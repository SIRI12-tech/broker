from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.urls import reverse
import logging

from .models import Order, Portfolio, Asset, Position

logger = logging.getLogger(__name__)

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.db import transaction
from django.contrib import messages
from decimal import Decimal
import uuid
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage

from .models import (
    Asset, Order, Transaction, Portfolio, Position,
    PriceAlert, MarketSentiment, MarketNews, AssetMetrics,
    RiskMetrics, EconomicCalendar, Wallet, WalletTransaction,
    TradingStrategy, BacktestResult  # Add BacktestResult model
)
from .forms import WithdrawalForm

@login_required
def dashboard(request):
    """Main trading dashboard with portfolio overview and market data."""
    user_profile = request.user.userprofile
    
    # Get or create portfolio
    portfolio, created = Portfolio.objects.get_or_create(user=user_profile)
    
    # Get user's wallet
    wallet = Wallet.objects.filter(user=request.user).first()
    
    positions = Position.objects.filter(portfolio=portfolio)
    
    # Get market metrics
    market_metrics = AssetMetrics.objects.select_related('asset').all()
    risk_metrics = RiskMetrics.objects.filter(portfolio=portfolio).first()
    
    context = {
        'portfolio': portfolio,
        'positions': positions,
        'market_metrics': market_metrics,
        'risk_metrics': risk_metrics,
        'wallet': wallet,
    }
    return render(request, 'trading/dashboard.html', context)

@login_required
def portfolio_analysis(request):
    """Portfolio analysis view with detailed metrics and charts."""
    user_profile = request.user.userprofile
    portfolio = get_object_or_404(Portfolio, user=user_profile)
    
    # Get portfolio metrics
    positions = Position.objects.filter(portfolio=portfolio)
    risk_metrics = RiskMetrics.objects.filter(portfolio=portfolio).first()
    
    # Calculate portfolio statistics
    total_value = sum(position.current_value for position in positions)
    asset_allocation = [
        {
            'asset': position.asset.name,
            'percentage': (position.current_value / total_value * 100) if total_value > 0 else 0
        }
        for position in positions
    ]
    
    context = {
        'portfolio': portfolio,
        'positions': positions,
        'risk_metrics': risk_metrics,
        'total_value': total_value,
        'asset_allocation': asset_allocation,
    }
    return render(request, 'trading/portfolio_analysis.html', context)

@login_required
def order_entry(request):
    """Handle order entry for trading."""
    if request.method == 'POST':
        try:
            asset_id = request.POST.get('asset')
            order_type = request.POST.get('order_type')
            quantity = Decimal(request.POST.get('quantity', '0'))
            price = Decimal(request.POST.get('price', '0'))
            
            asset = get_object_or_404(Asset, id=asset_id)
            portfolio = get_object_or_404(Portfolio, user=request.user.userprofile)
            
            # Create the order
            order = Order.objects.create(
                portfolio=portfolio,
                asset=asset,
                order_type=order_type,
                quantity=quantity,
                price=price,
                status='pending'
            )
            
            messages.success(request, 'Order submitted successfully.')
            return redirect('order_detail', order_id=order.id)
            
        except (ValueError, Asset.DoesNotExist, Portfolio.DoesNotExist) as e:
            messages.error(request, f'Error submitting order: {str(e)}')
            return redirect('order_entry')
    
    # GET request - show order form
    assets = Asset.objects.all()
    context = {
        'assets': assets,
        'order_types': [
            ('market', 'Market Order'),
            ('limit', 'Limit Order'),
            ('stop', 'Stop Order'),
        ]
    }
    return render(request, 'trading/order_entry.html', context)

@login_required
def order_detail(request, order_id):
    """View details of a specific order."""
    order = get_object_or_404(Order, id=order_id, portfolio__user=request.user.userprofile)
    return render(request, 'trading/order_detail.html', {'order': order})

@login_required
def market_data(request):
    """View market data and trends."""
    assets = Asset.objects.all()
    market_sentiment = MarketSentiment.objects.all()[:5]
    market_news = MarketNews.objects.all().order_by('-date')[:10]
    economic_calendar = EconomicCalendar.objects.filter(
        date__gte=timezone.now()
    ).order_by('date')[:5]
    
    context = {
        'assets': assets,
        'market_sentiment': market_sentiment,
        'market_news': market_news,
        'economic_calendar': economic_calendar,
    }
    return render(request, 'trading/market_data.html', context)

@login_required
def order_book(request):
    """View the order book with current buy and sell orders."""
    asset_id = request.GET.get('asset')
    if asset_id:
        asset = get_object_or_404(Asset, id=asset_id)
        buy_orders = Order.objects.filter(
            asset=asset,
            order_type='buy',
            status='pending'
        ).order_by('-price')
        sell_orders = Order.objects.filter(
            asset=asset,
            order_type='sell',
            status='pending'
        ).order_by('price')
    else:
        asset = None
        buy_orders = []
        sell_orders = []
    
    assets = Asset.objects.all()
    context = {
        'asset': asset,
        'assets': assets,
        'buy_orders': buy_orders,
        'sell_orders': sell_orders,
    }
    return render(request, 'trading/order_book.html', context)

@login_required
def order_history(request):
    """View user's order history."""
    portfolio = get_object_or_404(Portfolio, user=request.user.userprofile)
    orders = Order.objects.filter(portfolio=portfolio).order_by('-created_at')
    
    context = {
        'orders': orders,
    }
    return render(request, 'trading/order_history.html', context)

@login_required
def price_alerts(request):
    """Manage price alerts."""
    if request.method == 'POST':
        asset_id = request.POST.get('asset')
        price = Decimal(request.POST.get('price', '0'))
        alert_type = request.POST.get('alert_type')  # 'above' or 'below'
        
        asset = get_object_or_404(Asset, id=asset_id)
        
        PriceAlert.objects.create(
            user=request.user,
            asset=asset,
            price=price,
            alert_type=alert_type
        )
        
        messages.success(request, 'Price alert created successfully.')
        return redirect('price_alerts')
    
    alerts = PriceAlert.objects.filter(user=request.user)
    assets = Asset.objects.all()
    
    context = {
        'alerts': alerts,
        'assets': assets,
    }
    return render(request, 'trading/price_alerts.html', context)

@login_required
def delete_price_alert(request, alert_id):
    """Delete a price alert."""
    alert = get_object_or_404(PriceAlert, id=alert_id, user=request.user)
    alert.delete()
    messages.success(request, 'Price alert deleted successfully.')
    return redirect('price_alerts')

# Wallet Management Views
@login_required
def wallet_generate(request):
    """Generate a new wallet for the user."""
    try:
        if Wallet.objects.filter(user=request.user).exists():
            messages.warning(request, 'You already have a wallet.')
            return redirect('wallet_detail')
        
        wallet_address = generate_wallet_address()
        wallet = Wallet.objects.create(
            user=request.user,
            address=wallet_address,
            balance=Decimal('0.0'),
            status='active'
        )
        messages.success(request, 'Wallet generated successfully.')
        return redirect('wallet_detail')
        
    except Exception as e:
        messages.error(request, f'Error generating wallet: {str(e)}')
        return redirect('dashboard')

@login_required
def wallet_detail(request):
    """View wallet details and transaction history."""
    wallet = get_object_or_404(Wallet, user=request.user)
    transactions = WalletTransaction.objects.filter(wallet=wallet).order_by('-timestamp')
    
    context = {
        'wallet': wallet,
        'transactions': transactions,
    }
    return render(request, 'trading/wallet/detail.html', context)

@login_required
def wallet_deposit(request):
    """Handle cryptocurrency deposits."""
    wallet = get_object_or_404(Wallet, user=request.user)
    
    if request.method == 'POST':
        try:
            amount = Decimal(request.POST.get('amount', '0'))
            currency = request.POST.get('currency')
            
            if amount <= 0:
                raise ValueError('Amount must be greater than 0')
            
            # Create deposit transaction
            transaction = WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type='deposit',
                amount=amount,
                currency=currency,
                status='pending'
            )
            
            messages.success(request, 'Deposit initiated successfully.')
            return redirect('wallet_detail')
            
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Error processing deposit: {str(e)}')
    
    context = {
        'wallet': wallet,
        'supported_currencies': get_supported_currencies()
    }
    return render(request, 'trading/wallet/deposit.html', context)

@login_required
def wallet_withdraw(request):
    """Handle cryptocurrency withdrawals."""
    wallet = get_object_or_404(Wallet, user=request.user)
    
    if request.method == 'POST':
        form = WithdrawalForm(request.POST)
        if form.is_valid():
            try:
                amount = form.cleaned_data['amount']
                address = form.cleaned_data['address']
                currency = form.cleaned_data['currency']
                
                if amount > wallet.balance:
                    raise ValueError('Insufficient balance')
                
                # Create withdrawal transaction
                transaction = WalletTransaction.objects.create(
                    wallet=wallet,
                    transaction_type='withdrawal',
                    amount=amount,
                    currency=currency,
                    destination_address=address,
                    status='pending'
                )
                
                messages.success(request, 'Withdrawal initiated successfully.')
                return redirect('wallet_detail')
                
            except ValueError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f'Error processing withdrawal: {str(e)}')
    else:
        form = WithdrawalForm()
    
    context = {
        'wallet': wallet,
        'form': form,
    }
    return render(request, 'trading/wallet/withdraw.html', context)

@login_required
def trading_strategies(request):
    """View and manage trading strategies."""
    if request.method == 'POST':
        strategy_type = request.POST.get('strategy_type')
        asset_id = request.POST.get('asset')
        parameters = {
            'time_frame': request.POST.get('time_frame'),
            'risk_level': request.POST.get('risk_level'),
            'take_profit': Decimal(request.POST.get('take_profit', '0')),
            'stop_loss': Decimal(request.POST.get('stop_loss', '0')),
        }
        
        try:
            asset = get_object_or_404(Asset, id=asset_id)
            
            # Create or update strategy
            strategy = TradingStrategy.objects.create(
                user=request.user,
                asset=asset,
                strategy_type=strategy_type,
                parameters=parameters,
                status='active'
            )
            
            messages.success(request, 'Trading strategy created successfully.')
            return redirect('trading_strategies')
            
        except Exception as e:
            messages.error(request, f'Error creating strategy: {str(e)}')
    
    strategies = TradingStrategy.objects.filter(user=request.user)
    assets = Asset.objects.all()
    
    context = {
        'strategies': strategies,
        'assets': assets,
        'strategy_types': [
            ('trend_following', 'Trend Following'),
            ('mean_reversion', 'Mean Reversion'),
            ('breakout', 'Breakout Trading'),
            ('scalping', 'Scalping'),
        ],
        'time_frames': [
            ('5m', '5 Minutes'),
            ('15m', '15 Minutes'),
            ('1h', '1 Hour'),
            ('4h', '4 Hours'),
            ('1d', '1 Day'),
        ],
        'risk_levels': [
            ('low', 'Low Risk'),
            ('medium', 'Medium Risk'),
            ('high', 'High Risk'),
        ],
    }
    return render(request, 'trading/strategies.html', context)

@login_required
def delete_strategy(request, strategy_id):
    """Delete a trading strategy."""
    strategy = get_object_or_404(TradingStrategy, id=strategy_id, user=request.user)
    strategy.delete()
    messages.success(request, 'Trading strategy deleted successfully.')
    return redirect('trading_strategies')

@login_required
def toggle_strategy(request, strategy_id):
    """Toggle a trading strategy's active status."""
    strategy = get_object_or_404(TradingStrategy, id=strategy_id, user=request.user)
    strategy.status = 'inactive' if strategy.status == 'active' else 'active'
    strategy.save()
    messages.success(request, f'Trading strategy {strategy.status}.')
    return redirect('trading_strategies')

@login_required
def strategy_performance(request, strategy_id):
    """View performance metrics for a specific trading strategy."""
    strategy = get_object_or_404(TradingStrategy, id=strategy_id, user=request.user)
    
    # Get strategy performance metrics
    performance = {
        'total_trades': 100,  # Replace with actual metrics
        'win_rate': 65.5,
        'profit_loss': 2500.00,
        'avg_trade_duration': '2h 15m',
        'largest_win': 500.00,
        'largest_loss': -200.00,
        'sharpe_ratio': 1.8,
    }
    
    # Get recent trades
    trades = Order.objects.filter(
        portfolio__user=request.user,
        strategy=strategy
    ).order_by('-created_at')[:20]
    
    context = {
        'strategy': strategy,
        'performance': performance,
        'trades': trades,
    }
    return render(request, 'trading/strategy_performance.html', context)

@login_required
def strategy_backtest(request, strategy_id):
    """Run backtesting for a specific trading strategy."""
    strategy = get_object_or_404(TradingStrategy, id=strategy_id, user=request.user)
    
    if request.method == 'POST':
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        initial_capital = Decimal(request.POST.get('initial_capital', '10000'))
        
        try:
            # Run backtest simulation
            results = run_strategy_backtest(
                strategy=strategy,
                start_date=start_date,
                end_date=end_date,
                initial_capital=initial_capital
            )
            
            # Store backtest results
            BacktestResult.objects.create(
                strategy=strategy,
                start_date=start_date,
                end_date=end_date,
                initial_capital=initial_capital,
                final_capital=results['final_capital'],
                total_trades=results['total_trades'],
                win_rate=results['win_rate'],
                profit_loss=results['profit_loss'],
                max_drawdown=results['max_drawdown'],
                sharpe_ratio=results['sharpe_ratio']
            )
            
            messages.success(request, 'Backtest completed successfully.')
            return redirect('strategy_backtest', strategy_id=strategy.id)
            
        except Exception as e:
            messages.error(request, f'Error running backtest: {str(e)}')
    
    # Get previous backtest results
    backtest_results = BacktestResult.objects.filter(
        strategy=strategy
    ).order_by('-created_at')
    
    context = {
        'strategy': strategy,
        'backtest_results': backtest_results,
    }
    return render(request, 'trading/strategy_backtest.html', context)

@login_required
def trading_view(request, symbol):
    """View for trading a specific cryptocurrency."""
    try:
        asset = get_object_or_404(Asset, symbol=symbol.upper())
        
        # Get user's portfolio and positions
        portfolio = get_object_or_404(Portfolio, user=request.user.userprofile)
        position = Position.objects.filter(portfolio=portfolio, asset=asset).first()
        
        # Get market data
        market_data = {
            'current_price': get_current_price(symbol),
            '24h_volume': get_24h_volume(symbol),
            '24h_high': get_24h_high(symbol),
            '24h_low': get_24h_low(symbol),
            'market_cap': get_market_cap(symbol),
        }
        
        # Get order book
        buy_orders = Order.objects.filter(
            asset=asset,
            order_type='buy',
            status='pending'
        ).order_by('-price')[:10]
        
        sell_orders = Order.objects.filter(
            asset=asset,
            order_type='sell',
            status='pending'
        ).order_by('price')[:10]
        
        # Get recent trades
        recent_trades = Order.objects.filter(
            asset=asset,
            status='completed'
        ).order_by('-updated_at')[:20]
        
        # Get price alerts
        alerts = PriceAlert.objects.filter(
            user=request.user,
            asset=asset,
            is_active=True
        )
        
        context = {
            'asset': asset,
            'position': position,
            'market_data': market_data,
            'buy_orders': buy_orders,
            'sell_orders': sell_orders,
            'recent_trades': recent_trades,
            'alerts': alerts,
        }
        return render(request, 'trading/trading_view.html', context)
        
    except Exception as e:
        messages.error(request, f'Error loading trading view: {str(e)}')
        return redirect('dashboard')

@login_required
def market_overview(request):
    """View for market overview with key metrics and trends."""
    # Get all tradeable assets
    assets = Asset.objects.all()
    
    # Get market metrics for each asset
    market_metrics = []
    for asset in assets:
        metrics = {
            'asset': asset,
            'current_price': get_current_price(asset.symbol),
            '24h_volume': get_24h_volume(asset.symbol),
            '24h_high': get_24h_high(asset.symbol),
            '24h_low': get_24h_low(asset.symbol),
            'market_cap': get_market_cap(asset.symbol),
            'price_change_24h': calculate_price_change(asset.symbol),
        }
        market_metrics.append(metrics)
    
    # Get market sentiment
    sentiment = MarketSentiment.objects.all().order_by('-date')[:5]
    
    # Get market news
    news = MarketNews.objects.all().order_by('-date')[:10]
    
    # Get upcoming economic events
    economic_events = EconomicCalendar.objects.filter(
        date__gte=timezone.now()
    ).order_by('date')[:5]
    
    # Calculate market dominance
    total_market_cap = sum(m['market_cap'] for m in market_metrics)
    for metrics in market_metrics:
        metrics['market_dominance'] = (
            metrics['market_cap'] / total_market_cap * 100
            if total_market_cap > 0 else 0
        )
    
    # Sort by market cap
    market_metrics.sort(key=lambda x: x['market_cap'], reverse=True)
    
    context = {
        'market_metrics': market_metrics,
        'sentiment': sentiment,
        'news': news,
        'economic_events': economic_events,
        'total_market_cap': total_market_cap,
    }
    return render(request, 'trading/market_overview.html', context)

@login_required
@require_http_methods(["POST"])
def place_order(request):
    """Handle order placement"""
    try:
        # Get form data
        crypto = request.POST.get('crypto')
        amount = Decimal(request.POST.get('amount'))
        order_type = request.POST.get('type')

        # Validate amount
        if amount <= 0:
            messages.error(request, 'Amount must be greater than 0')
            return redirect('trading:dashboard')

        # Create order
        order = Order.objects.create(
            user=request.user,
            crypto_asset=crypto,
            amount=amount,
            order_type=order_type,
            status='pending'
        )

        # Redirect to order confirmation
        return redirect('trading:order_confirmation', order_id=order.id)

    except (ValueError, TypeError):
        messages.error(request, 'Invalid amount provided')
    except Exception as e:
        logger.error(f"Error in place_order: {str(e)}")
        messages.error(request, 'An error occurred while placing your order')
    
    return redirect('trading:dashboard')

@login_required
def transaction_history(request):
    """View for displaying user's transaction history."""
    try:
        # Get user's portfolio
        portfolio = get_object_or_404(Portfolio, user=request.user.userprofile)
        
        # Get all completed orders
        orders = Order.objects.filter(
            user=request.user.userprofile,
            status='completed'
        ).order_by('-filled_at')
        
        # Get all wallet transactions
        wallet_transactions = WalletTransaction.objects.filter(
            wallet__user=request.user.userprofile
        ).order_by('-timestamp')
        
        # Combine and sort all transactions
        transactions = []
        
        # Add orders to transactions list
        for order in orders:
            transactions.append({
                'type': f"{order.order_type} order",
                'asset': order.asset.symbol,
                'amount': order.quantity,
                'price': order.filled_price,
                'total': order.quantity * order.filled_price,
                'timestamp': order.filled_at,
                'status': order.status,
            })
        
        # Add wallet transactions to list
        for tx in wallet_transactions:
            transactions.append({
                'type': tx.transaction_type,
                'asset': tx.wallet.asset.symbol,
                'amount': tx.amount,
                'price': None,  # Wallet transactions don't have a price
                'total': None,
                'timestamp': tx.timestamp,
                'status': tx.status,
            })
        
        # Sort combined transactions by timestamp
        transactions.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Pagination
        paginator = Paginator(transactions, 20)  # 20 transactions per page
        page = request.GET.get('page')
        
        try:
            transactions = paginator.page(page)
        except PageNotAnInteger:
            transactions = paginator.page(1)
        except EmptyPage:
            transactions = paginator.page(paginator.num_pages)
        
        context = {
            'transactions': transactions,
            'portfolio': portfolio,
        }
        return render(request, 'trading/transaction_history.html', context)
        
    except Exception as e:
        messages.error(request, f'Error loading transaction history: {str(e)}')
        return redirect('dashboard')

@login_required
def get_asset_price(request, symbol):
    """API endpoint for getting current asset price."""
    try:
        # Validate asset exists
        asset = get_object_or_404(Asset, symbol=symbol.upper())
        
        # Get current price and related metrics
        price_data = {
            'symbol': asset.symbol,
            'current_price': get_current_price(symbol),
            'price_change_24h': calculate_price_change(symbol),
            'volume_24h': get_24h_volume(symbol),
            'high_24h': get_24h_high(symbol),
            'low_24h': get_24h_low(symbol),
            'market_cap': get_market_cap(symbol),
            'timestamp': timezone.now().isoformat(),
        }
        
        return JsonResponse(price_data)
        
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=400)

@login_required
def get_market_data(request, symbol):
    """API endpoint for getting comprehensive market data for an asset."""
    try:
        # Validate asset exists
        asset = get_object_or_404(Asset, symbol=symbol.upper())
        
        # Get market data
        market_data = {
            'symbol': asset.symbol,
            'name': asset.name,
            'current_price': get_current_price(symbol),
            'price_change_24h': calculate_price_change(symbol),
            'volume_24h': get_24h_volume(symbol),
            'high_24h': get_24h_high(symbol),
            'low_24h': get_24h_low(symbol),
            'market_cap': get_market_cap(symbol),
            'timestamp': timezone.now().isoformat(),
        }
        
        # Get order book data
        buy_orders = Order.objects.filter(
            asset=asset,
            order_type='buy',
            status='pending'
        ).order_by('-price')[:10]
        
        sell_orders = Order.objects.filter(
            asset=asset,
            order_type='sell',
            status='pending'
        ).order_by('price')[:10]
        
        # Format order book data
        order_book = {
            'buy_orders': [
                {
                    'price': str(order.price),
                    'quantity': str(order.quantity),
                    'total': str(order.price * order.quantity)
                } for order in buy_orders
            ],
            'sell_orders': [
                {
                    'price': str(order.price),
                    'quantity': str(order.quantity),
                    'total': str(order.price * order.quantity)
                } for order in sell_orders
            ]
        }
        
        # Get recent trades
        recent_trades = Order.objects.filter(
            asset=asset,
            status='completed'
        ).order_by('-filled_at')[:20]
        
        # Format trade data
        trades = [
            {
                'price': str(trade.filled_price),
                'quantity': str(trade.quantity),
                'total': str(trade.filled_price * trade.quantity),
                'type': trade.order_type,
                'timestamp': trade.filled_at.isoformat()
            } for trade in recent_trades
        ]
        
        # Combine all data
        response_data = {
            'market_data': market_data,
            'order_book': order_book,
            'recent_trades': trades
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=400)

@login_required
def get_portfolio_chart_data(request):
    """API endpoint for getting portfolio performance chart data."""
    try:
        # Get user's portfolio
        portfolio = get_object_or_404(Portfolio, user=request.user.userprofile)
        
        # Get date range from request parameters
        days = int(request.GET.get('days', 30))  # Default to 30 days
        end_date = timezone.now()
        start_date = end_date - timezone.timedelta(days=days)
        
        # Get portfolio snapshots for the date range
        snapshots = PortfolioSnapshot.objects.filter(
            portfolio=portfolio,
            timestamp__range=(start_date, end_date)
        ).order_by('timestamp')
        
        # Format data for chart
        chart_data = []
        for snapshot in snapshots:
            chart_data.append({
                'timestamp': snapshot.timestamp.isoformat(),
                'total_value': str(snapshot.total_value),
                'cash_balance': str(snapshot.cash_balance),
                'asset_value': str(snapshot.asset_value),
                'pnl_24h': str(snapshot.pnl_24h),
                'pnl_percentage_24h': str(snapshot.pnl_percentage_24h),
            })
        
        # Get current portfolio composition
        positions = Position.objects.filter(portfolio=portfolio)
        composition = []
        
        total_asset_value = sum(
            position.quantity * get_current_price(position.asset.symbol)
            for position in positions
        )
        
        for position in positions:
            current_price = get_current_price(position.asset.symbol)
            position_value = position.quantity * current_price
            
            composition.append({
                'symbol': position.asset.symbol,
                'quantity': str(position.quantity),
                'current_price': str(current_price),
                'total_value': str(position_value),
                'percentage': str(position_value / total_asset_value * 100 if total_asset_value > 0 else 0),
                'avg_price': str(position.average_price),
                'pnl': str((current_price - position.average_price) * position.quantity),
                'pnl_percentage': str((current_price - position.average_price) / position.average_price * 100 if position.average_price > 0 else 0),
            })
        
        response_data = {
            'chart_data': chart_data,
            'composition': composition,
            'total_value': str(portfolio.total_value),
            'cash_balance': str(portfolio.cash_balance),
            'asset_value': str(total_asset_value),
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=400)

@login_required
def market_overview(request):
    """View for market overview and top performers."""
    context = {
        'top_crypto': Asset.get_top_performers(asset_type='crypto', limit=5),
        'top_forex': Asset.get_top_performers(asset_type='forex', limit=5),
        'top_stocks': Asset.get_top_performers(asset_type='stock', limit=5),
        'market_news': MarketNews.objects.order_by('-date')[:5],
        'market_sentiment': MarketSentiment.objects.latest('date'),
    }
    return render(request, 'trading/market_overview.html', context)

@login_required
def get_top_performers(request):
    """API endpoint for getting top performers."""
    asset_type = request.GET.get('asset_type')
    limit = int(request.GET.get('limit', 10))
    
    top_performers = Asset.get_top_performers(asset_type=asset_type, limit=limit)
    data = [{
        'symbol': asset.symbol,
        'name': asset.name,
        'current_price': float(asset.current_price),
        'price_change_24h': float(asset.price_change_24h),
        'price_change_percentage_24h': float(asset.price_change_percentage_24h),
        'volume_24h': float(asset.volume_24h),
        'last_updated': asset.last_updated.isoformat(),
    } for asset in top_performers]
    
    return JsonResponse({'data': data})

@login_required
def wallet_balance(request):
    """Get user's wallet balance."""
    try:
        wallet = Wallet.objects.filter(user=request.user).first()
        if wallet:
            return JsonResponse({
                'status': 'success',
                'balance': {
                    'btc': str(wallet.btc_balance),
                    'eth': str(wallet.eth_balance),
                    'usdt': str(wallet.usdt_balance)
                }
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Wallet not found'
            }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
def order_confirmation(request, order_id):
    """Show order confirmation page"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    context = {
        'order': order,
        'page_title': 'Order Confirmation'
    }
    return render(request, 'trading/order_confirmation.html', context)

def process_order(order):
    """Process a trading order.
    
    In a real system, this would:
    1. Connect to exchange API
    2. Place the order
    3. Monitor order status
    4. Update user's portfolio when filled
    """
    # Placeholder implementation - auto-fill order
    order.status = 'completed'
    order.filled_price = order.price
    order.filled_at = timezone.now()
    order.save()
    
    # Update portfolio
    portfolio = order.user.portfolio
    
    if order.order_type == 'buy':
        # Deduct cash balance
        portfolio.cash_balance -= order.quantity * order.filled_price
        
        # Add to position
        position, created = Position.objects.get_or_create(
            portfolio=portfolio,
            asset=order.asset,
            defaults={'quantity': 0, 'average_price': 0}
        )
        
        # Update position
        total_value = (position.quantity * position.average_price) + (order.quantity * order.filled_price)
        position.quantity += order.quantity
        position.average_price = total_value / position.quantity
        position.save()
        
    elif order.order_type == 'sell':
        # Add to cash balance
        portfolio.cash_balance += order.quantity * order.filled_price
        
        # Reduce position
        position = Position.objects.get(
            portfolio=portfolio,
            asset=order.asset
        )
        position.quantity -= order.quantity
        if position.quantity == 0:
            position.delete()
        else:
            position.save()
    
    portfolio.save()

def calculate_price_change(symbol):
    """Calculate 24-hour price change percentage."""
    # Placeholder - implement actual calculation
    return Decimal('2.5')  # 2.5% increase

# Market Data Helper Functions
def get_current_price(symbol):
    """Get current price for a cryptocurrency."""
    # Placeholder - implement actual API call
    return Decimal('50000.00')

def get_24h_volume(symbol):
    """Get 24-hour trading volume for a cryptocurrency."""
    # Placeholder - implement actual API call
    return Decimal('1000000.00')

def get_24h_high(symbol):
    """Get 24-hour high price for a cryptocurrency."""
    # Placeholder - implement actual API call
    return Decimal('52000.00')

def get_24h_low(symbol):
    """Get 24-hour low price for a cryptocurrency."""
    # Placeholder - implement actual API call
    return Decimal('48000.00')

def get_market_cap(symbol):
    """Get market capitalization for a cryptocurrency."""
    # Placeholder - implement actual API call
    return Decimal('1000000000.00')

def run_strategy_backtest(strategy, start_date, end_date, initial_capital):
    """Run a backtest simulation for a trading strategy.
    
    This is a placeholder implementation. In a real system, you would:
    1. Fetch historical price data for the strategy's asset
    2. Implement the strategy's logic
    3. Simulate trades based on the strategy's signals
    4. Calculate performance metrics
    """
    # Placeholder results
    return {
        'final_capital': initial_capital * Decimal('1.25'),  # 25% return
        'total_trades': 50,
        'win_rate': 60.0,
        'profit_loss': initial_capital * Decimal('0.25'),
        'max_drawdown': Decimal('15.5'),
        'sharpe_ratio': Decimal('1.8'),
    }

def generate_wallet_address():
    """Generate a unique wallet address."""
    # This is a placeholder. Implement your actual wallet address generation logic
    # You might want to use a crypto library like bitcoinlib or web3.py depending on your needs
    return str(uuid.uuid4())

def get_supported_currencies():
    """Return list of supported cryptocurrencies."""
    return [
        {'code': 'BTC', 'name': 'Bitcoin'},
        {'code': 'ETH', 'name': 'Ethereum'},
        {'code': 'USDT', 'name': 'Tether'},
    ]
