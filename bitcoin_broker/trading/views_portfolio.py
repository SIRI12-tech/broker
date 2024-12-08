from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Sum, F, Q
from django.utils import timezone
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from .models import (
    Portfolio, Position, Asset, Transaction, PortfolioSnapshot,
    AssetMetrics, RiskMetrics, WatchList
)
from .utils import (
    calculate_portfolio_metrics, fetch_asset_prices,
    calculate_risk_metrics, generate_portfolio_chart_data
)

@login_required
def portfolio_dashboard(request):
    """Main portfolio dashboard view"""
    portfolio = Portfolio.objects.get(user=request.user.userprofile)
    positions = Position.objects.filter(portfolio=portfolio).select_related('asset')
    
    # Get portfolio snapshots for historical performance
    snapshots = PortfolioSnapshot.objects.filter(
        portfolio=portfolio,
        snapshot_date__gte=timezone.now() - timedelta(days=30)
    ).order_by('snapshot_date')
    
    # Calculate portfolio metrics
    metrics = calculate_portfolio_metrics(portfolio)
    risk_metrics = calculate_risk_metrics(portfolio)
    
    # Generate chart data
    chart_data = generate_portfolio_chart_data(snapshots)
    
    # Get asset allocation data
    allocation_data = positions.annotate(
        allocation=F('current_value') / portfolio.total_value * 100
    ).values('asset__name', 'allocation')
    
    context = {
        'portfolio': portfolio,
        'positions': positions,
        'metrics': metrics,
        'risk_metrics': risk_metrics,
        'chart_data': chart_data,
        'allocation_data': list(allocation_data),
    }
    return render(request, 'trading/portfolio/dashboard.html', context)

@login_required
def position_detail(request, position_id):
    """Detailed view of a portfolio position"""
    position = get_object_or_404(Position, id=position_id, portfolio__user=request.user.userprofile)
    
    # Get historical transactions for this position
    transactions = Transaction.objects.filter(
        user=request.user.userprofile,
        order__asset=position.asset
    ).order_by('-created_at')
    
    # Get asset metrics
    metrics = AssetMetrics.objects.get(asset=position.asset)
    
    # Calculate position performance metrics
    performance = {
        'total_return': (position.current_value - (position.average_buy_price * position.quantity)),
        'return_percentage': ((position.current_value / (position.average_buy_price * position.quantity)) - 1) * 100,
        'daily_change': metrics.price_change_24h,
        'weekly_change': metrics.price_change_7d,
        'monthly_change': metrics.price_change_30d,
    }
    
    context = {
        'position': position,
        'transactions': transactions,
        'metrics': metrics,
        'performance': performance,
    }
    return render(request, 'trading/portfolio/position_detail.html', context)

@login_required
def watchlist(request):
    """User's watchlist management"""
    watchlists = WatchList.objects.filter(user=request.user.userprofile)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create':
            name = request.POST.get('name')
            WatchList.objects.create(user=request.user.userprofile, name=name)
        elif action == 'add_asset':
            watchlist_id = request.POST.get('watchlist_id')
            asset_id = request.POST.get('asset_id')
            watchlist = get_object_or_404(WatchList, id=watchlist_id, user=request.user.userprofile)
            asset = get_object_or_404(Asset, id=asset_id)
            watchlist.assets.add(asset)
        elif action == 'remove_asset':
            watchlist_id = request.POST.get('watchlist_id')
            asset_id = request.POST.get('asset_id')
            watchlist = get_object_or_404(WatchList, id=watchlist_id, user=request.user.userprofile)
            asset = get_object_or_404(Asset, id=asset_id)
            watchlist.assets.remove(asset)
        
        return redirect('trading:watchlist')
    
    # Get latest metrics for watchlist assets
    for watchlist in watchlists:
        assets = watchlist.assets.all()
        for asset in assets:
            asset.metrics = AssetMetrics.objects.get(asset=asset)
    
    context = {
        'watchlists': watchlists,
        'available_assets': Asset.objects.all(),
    }
    return render(request, 'trading/portfolio/watchlist.html', context)

@login_required
def portfolio_analysis(request):
    """Advanced portfolio analysis and risk metrics"""
    portfolio = Portfolio.objects.get(user=request.user.userprofile)
    positions = Position.objects.filter(portfolio=portfolio).select_related('asset')
    
    # Calculate advanced risk metrics
    risk_metrics = RiskMetrics.objects.filter(
        portfolio=portfolio,
        calculated_at__gte=timezone.now() - timedelta(hours=24)
    ).first()
    
    if not risk_metrics:
        # Calculate new risk metrics if none exist or too old
        risk_metrics = calculate_risk_metrics(portfolio)
    
    # Get historical correlation matrix
    correlation_matrix = calculate_correlation_matrix(positions)
    
    # Calculate diversification score
    diversification_score = calculate_diversification_score(positions)
    
    context = {
        'portfolio': portfolio,
        'risk_metrics': risk_metrics,
        'correlation_matrix': correlation_matrix,
        'diversification_score': diversification_score,
    }
    return render(request, 'trading/portfolio/analysis.html', context)

@login_required
def transaction_history(request):
    """Transaction history view"""
    transactions = Transaction.objects.filter(
        user=request.user.userprofile
    ).select_related('order', 'order__asset').order_by('-created_at')
    
    # Filter transactions
    transaction_type = request.GET.get('type')
    if transaction_type:
        transactions = transactions.filter(transaction_type=transaction_type)
    
    # Date range filter
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    if start_date and end_date:
        transactions = transactions.filter(
            created_at__range=[start_date, end_date]
        )
    
    # Calculate summary statistics
    summary = {
        'total_trades': transactions.filter(transaction_type='trade').count(),
        'total_deposits': transactions.filter(transaction_type='deposit').aggregate(
            total=Sum('amount')
        )['total'] or 0,
        'total_withdrawals': transactions.filter(transaction_type='withdrawal').aggregate(
            total=Sum('amount')
        )['total'] or 0,
        'total_fees': transactions.aggregate(total=Sum('fee'))['total'] or 0,
    }
    
    context = {
        'transactions': transactions,
        'summary': summary,
    }
    return render(request, 'trading/portfolio/transactions.html', context)

@login_required
def portfolio_performance_api(request):
    """API endpoint for portfolio performance data"""
    portfolio = Portfolio.objects.get(user=request.user.userprofile)
    timeframe = request.GET.get('timeframe', '1M')  # 1D, 1W, 1M, 3M, 1Y, ALL
    
    # Get snapshots based on timeframe
    if timeframe == '1D':
        start_date = timezone.now() - timedelta(days=1)
    elif timeframe == '1W':
        start_date = timezone.now() - timedelta(weeks=1)
    elif timeframe == '1M':
        start_date = timezone.now() - timedelta(days=30)
    elif timeframe == '3M':
        start_date = timezone.now() - timedelta(days=90)
    elif timeframe == '1Y':
        start_date = timezone.now() - timedelta(days=365)
    else:  # ALL
        start_date = portfolio.created_at
    
    snapshots = PortfolioSnapshot.objects.filter(
        portfolio=portfolio,
        snapshot_date__gte=start_date
    ).order_by('snapshot_date')
    
    data = [{
        'date': snapshot.snapshot_date.isoformat(),
        'total_value': float(snapshot.total_value),
        'profit_loss': float(snapshot.daily_profit_loss),
        'profit_loss_pct': float(snapshot.daily_profit_loss_percentage),
    } for snapshot in snapshots]
    
    return JsonResponse({'data': data})

def calculate_correlation_matrix(positions):
    """Calculate correlation matrix for portfolio assets"""
    # Get historical prices for all assets
    asset_ids = positions.values_list('asset_id', flat=True)
    prices = fetch_asset_prices(asset_ids, days=30)
    
    # Create price DataFrame
    df = pd.DataFrame(prices)
    
    # Calculate correlation matrix
    correlation = df.corr()
    
    return correlation.to_dict()

def calculate_diversification_score(positions):
    """Calculate portfolio diversification score"""
    # Get asset allocations and categories
    allocations = positions.values_list('asset__asset_type', 'current_value')
    total_value = sum(value for _, value in allocations)
    
    # Calculate Herfindahl-Hirschman Index (HHI)
    type_allocations = {}
    for asset_type, value in allocations:
        if asset_type not in type_allocations:
            type_allocations[asset_type] = 0
        type_allocations[asset_type] += float(value) / total_value
    
    hhi = sum(alloc ** 2 for alloc in type_allocations.values())
    
    # Convert HHI to diversification score (0-100)
    # Lower HHI means better diversification
    diversification_score = (1 - hhi) * 100
    
    return round(diversification_score, 2)
