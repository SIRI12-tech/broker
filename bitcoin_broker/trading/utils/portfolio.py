"""Portfolio utility functions for calculating metrics and fetching data."""

import pandas as pd
import numpy as np
import ccxt
from django.utils import timezone
from decimal import Decimal
from ..models import Transaction, Position, Asset

def calculate_portfolio_metrics(portfolio):
    """Calculate portfolio performance metrics"""
    positions = portfolio.positions.all()
    total_value = Decimal('0.0')
    total_cost = Decimal('0.0')
    
    for position in positions:
        current_price = get_current_price(position.asset)
        position_value = position.quantity * Decimal(str(current_price))
        total_value += position_value
        total_cost += position.cost_basis
    
    return {
        'total_value': total_value,
        'total_cost': total_cost,
        'total_return': total_value - total_cost,
        'return_percentage': ((total_value - total_cost) / total_cost * 100) if total_cost else Decimal('0')
    }

def fetch_asset_prices(asset_id, days=30):
    """Fetch historical prices for an asset"""
    asset = Asset.objects.get(id=asset_id)
    exchange = ccxt.binance()
    
    end_time = timezone.now()
    start_time = end_time - timezone.timedelta(days=days)
    
    ohlcv = exchange.fetch_ohlcv(
        f"{asset.symbol}/USDT",
        '1d',
        int(start_time.timestamp() * 1000),
        limit=days
    )
    
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

def calculate_risk_metrics(portfolio):
    """Calculate portfolio risk metrics"""
    positions = portfolio.positions.all()
    returns_data = []
    weights = []
    total_value = Decimal('0')
    
    # Calculate total portfolio value
    for position in positions:
        current_price = get_current_price(position.asset)
        position_value = position.quantity * Decimal(str(current_price))
        total_value += position_value
    
    # Get historical data and calculate weights
    for position in positions:
        if position.quantity > 0:
            prices_df = fetch_asset_prices(position.asset.id)
            returns = prices_df['close'].pct_change().dropna()
            returns_data.append(returns)
            
            position_value = position.quantity * Decimal(str(get_current_price(position.asset)))
            weight = float(position_value / total_value)
            weights.append(weight)
    
    if not returns_data:
        return {
            'volatility': 0,
            'sharpe_ratio': 0,
            'beta': 0
        }
    
    # Calculate portfolio returns
    portfolio_returns = sum(returns * weight for returns, weight in zip(returns_data, weights))
    
    # Calculate metrics
    volatility = float(portfolio_returns.std() * np.sqrt(252))  # Annualized volatility
    avg_return = float(portfolio_returns.mean() * 252)  # Annualized return
    risk_free_rate = 0.02  # Assuming 2% risk-free rate
    sharpe_ratio = (avg_return - risk_free_rate) / volatility if volatility else 0
    
    # Calculate beta using BTC as market proxy
    market_prices = fetch_market_prices()
    market_returns = market_prices['close'].pct_change().dropna()
    beta = calculate_portfolio_beta(portfolio_returns, market_returns)
    
    return {
        'volatility': volatility,
        'sharpe_ratio': sharpe_ratio,
        'beta': beta
    }

def generate_portfolio_chart_data(snapshots):
    """Generate chart data from portfolio snapshots"""
    data = []
    for snapshot in snapshots:
        data.append({
            'date': snapshot.timestamp.strftime('%Y-%m-%d'),
            'value': float(snapshot.total_value),
            'pnl': float(snapshot.unrealized_pnl),
            'return_pct': float(snapshot.return_percentage)
        })
    return data

def get_current_price(asset):
    """Get current price for an asset using CCXT"""
    exchange = ccxt.binance()
    ticker = exchange.fetch_ticker(f"{asset.symbol}/USDT")
    return ticker['last']

def fetch_market_prices(days=30):
    """Fetch Bitcoin prices as market proxy"""
    exchange = ccxt.binance()
    ohlcv = exchange.fetch_ohlcv('BTC/USDT', '1d', limit=days)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

def calculate_portfolio_beta(returns, market_returns):
    """Calculate portfolio beta relative to market"""
    if len(returns) != len(market_returns):
        min_len = min(len(returns), len(market_returns))
        returns = returns[-min_len:]
        market_returns = market_returns[-min_len:]
    
    covariance = np.cov(returns, market_returns)[0][1]
    market_variance = np.var(market_returns)
    return covariance / market_variance if market_variance else 0
