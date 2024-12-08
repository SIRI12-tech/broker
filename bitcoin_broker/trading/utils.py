import random
import string
import requests
import json
from django.core.mail import send_mail
from django.conf import settings
from .models import VerificationCode
from decimal import Decimal
from django.utils import timezone
import pandas as pd
import numpy as np
import ccxt
from django.db import transaction
from .models import Transaction, Position, Asset

def generate_verification_code():
    """Generate a 6-digit verification code"""
    return ''.join(random.choices(string.digits, k=6))

def send_email_verification(user, code_type='email'):
    """Send verification code via email"""
    code = generate_verification_code()
    
    # Save verification code
    VerificationCode.objects.create(
        user=user,
        code=code,
        code_type=code_type
    )
    
    # Send email
    subject = 'Your Nexus Broker Verification Code'
    message = f'Your verification code is: {code}\nThis code will expire in 10 minutes.'
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )
    
    return code

def send_sms_verification(user, phone_number, code_type='phone'):
    """Send verification code via SMS using Termii"""
    code = generate_verification_code()
    
    # Save verification code
    VerificationCode.objects.create(
        user=user,
        code=code,
        code_type=code_type
    )
    
    # Termii API endpoint
    url = "https://api.ng.termii.com/api/sms/send"
    
    # Prepare the message
    message = f'Your Nexus Broker verification code is: {code}. This code will expire in 10 minutes.'
    
    # Prepare the payload
    payload = {
        "to": phone_number,
        "from": settings.TERMII_SENDER_ID,
        "sms": message,
        "type": "plain",
        "channel": "generic",
        "api_key": settings.TERMII_API_KEY,
    }
    
    headers = {
        "Content-Type": "application/json",
    }
    
    try:
        # Send SMS
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response_data = response.json()
        
        if response.status_code == 200 and response_data.get('message') == 'Successfully Sent':
            return code
        else:
            error_msg = response_data.get('message', 'Unknown error')
            raise Exception(f"Failed to send SMS: {error_msg}")
            
    except Exception as e:
        # Log any errors and fall back to email
        print(f"SMS sending failed: {str(e)}")
        return send_email_verification(user, code_type='phone_fallback')

def verify_code(user, code, code_type):
    """Verify the provided code"""
    try:
        verification = VerificationCode.objects.filter(
            user=user,
            code=code,
            code_type=code_type,
            is_used=False
        ).latest('created_at')
        
        if verification.is_valid():
            verification.is_used = True
            verification.save()
            return True
    except VerificationCode.DoesNotExist:
        pass
    
    return False

# Portfolio and Trading Utility Functions

def get_current_price(asset):
    """Get current price for an asset using CCXT"""
    exchange = ccxt.binance()
    ticker = exchange.fetch_ticker(f'{asset.symbol}/USDT')
    return Decimal(str(ticker['last']))

def validate_order(portfolio, asset, order_type, side, quantity, price=None, is_modification=False, original_order=None):
    """Validate trading order parameters"""
    result = {'valid': True, 'message': ''}
    
    # Check minimum order size
    if quantity <= 0:
        return {'valid': False, 'message': 'Quantity must be greater than 0'}
    
    current_price = get_current_price(asset)
    
    # For sell orders, check if user has enough assets
    if side == 'sell':
        position = portfolio.positions.filter(asset=asset).first()
        available_quantity = position.quantity if position else 0
        
        if is_modification and original_order:
            available_quantity += original_order.quantity
            
        if quantity > available_quantity:
            return {'valid': False, 'message': 'Insufficient assets for sell order'}
    
    # For buy orders, check if user has enough balance
    elif side == 'buy':
        required_balance = quantity * (price or current_price)
        fee = calculate_order_fee(order_type, quantity, price or current_price)
        total_required = required_balance + fee
        
        if is_modification and original_order and original_order.side == 'buy':
            total_required -= (original_order.quantity * original_order.price + original_order.fee)
        
        if total_required > portfolio.available_balance:
            return {'valid': False, 'message': 'Insufficient balance for buy order'}
    
    # Validate limit price
    if order_type == 'limit' and price <= 0:
        return {'valid': False, 'message': 'Limit price must be greater than 0'}
    
    return result

def calculate_order_fee(order_type, quantity, price):
    """Calculate trading fee for an order"""
    # Example fee calculation (0.1% for market orders, 0.05% for limit orders)
    base_fee_rate = Decimal('0.001') if order_type == 'market' else Decimal('0.0005')
    order_value = quantity * price
    return order_value * base_fee_rate

def execute_order(order):
    """Execute a trading order"""
    current_price = get_current_price(order.asset)
    
    # For market orders, use current price
    execution_price = order.price or current_price
    
    with transaction.atomic():
        # Update order status
        order.status = 'executed'
        order.executed_price = execution_price
        order.executed_at = timezone.now()
        order.save()
        
        # Create transaction record
        transaction = Transaction.objects.create(
            user=order.user,
            order=order,
            price=execution_price,
            quantity=order.quantity,
            fee=order.fee
        )
        
        # Update position
        position, created = Position.objects.get_or_create(
            portfolio=order.user.portfolio,
            asset=order.asset,
            defaults={'quantity': 0, 'average_buy_price': 0}
        )
        
        if order.side == 'buy':
            # Update position for buy order
            new_quantity = position.quantity + order.quantity
            new_cost = (position.quantity * position.average_buy_price) + (order.quantity * execution_price)
            position.quantity = new_quantity
            position.average_buy_price = new_cost / new_quantity
        else:
            # Update position for sell order
            position.quantity -= order.quantity
        
        position.current_value = position.quantity * current_price
        position.save()
        
        # Update portfolio balance
        portfolio = order.user.portfolio
        if order.side == 'buy':
            portfolio.available_balance -= (order.quantity * execution_price + order.fee)
        else:
            portfolio.available_balance += (order.quantity * execution_price - order.fee)
        portfolio.save()

def calculate_portfolio_metrics(portfolio):
    """Calculate portfolio performance metrics"""
    positions = portfolio.positions.all()
    total_value = sum(position.current_value for position in positions)
    total_cost = sum(position.quantity * position.average_buy_price for position in positions)
    
    return {
        'total_value': total_value,
        'total_cost': total_cost,
        'total_profit_loss': total_value - total_cost,
        'profit_loss_percentage': ((total_value / total_cost) - 1) * 100 if total_cost > 0 else 0,
        'position_count': positions.count(),
    }

def calculate_risk_metrics(portfolio):
    """Calculate portfolio risk metrics"""
    positions = portfolio.positions.all()
    
    # Get historical prices for all assets
    prices_data = {}
    for position in positions:
        historical_prices = fetch_asset_prices(position.asset.id, days=30)
        prices_data[position.asset.symbol] = historical_prices
    
    # Calculate portfolio returns
    df = pd.DataFrame(prices_data)
    returns = df.pct_change().dropna()
    
    # Calculate weights
    total_value = sum(position.current_value for position in positions)
    weights = np.array([position.current_value / total_value for position in positions])
    
    # Calculate metrics
    portfolio_return = np.sum(weights * returns.mean()) * 252  # Annualized return
    portfolio_volatility = np.sqrt(np.dot(weights.T, np.dot(returns.cov() * 252, weights)))  # Annualized volatility
    sharpe_ratio = portfolio_return / portfolio_volatility if portfolio_volatility != 0 else 0
    
    # Calculate Value at Risk (VaR)
    portfolio_returns = np.dot(returns, weights)
    var_95 = np.percentile(portfolio_returns, 5)
    cvar_95 = portfolio_returns[portfolio_returns <= var_95].mean()
    
    return {
        'volatility': portfolio_volatility,
        'sharpe_ratio': sharpe_ratio,
        'var_95': var_95,
        'cvar_95': cvar_95,
        'beta': calculate_portfolio_beta(returns, weights),
    }

def calculate_portfolio_beta(returns, weights):
    """Calculate portfolio beta relative to market"""
    # Using Bitcoin as market proxy
    market_prices = fetch_market_prices(days=30)
    market_returns = pd.Series(market_prices).pct_change().dropna()
    
    portfolio_returns = np.dot(returns, weights)
    covariance = np.cov(portfolio_returns, market_returns)[0][1]
    market_variance = np.var(market_returns)
    
    return covariance / market_variance if market_variance != 0 else 1

def fetch_asset_prices(asset_id, days=30):
    """Fetch historical prices for an asset"""
    exchange = ccxt.binance()
    asset = Asset.objects.get(id=asset_id)
    
    # Fetch OHLCV data
    since = exchange.parse8601(timezone.now() - timezone.timedelta(days=days))
    ohlcv = exchange.fetch_ohlcv(f'{asset.symbol}/USDT', '1d', since=since)
    
    # Extract closing prices
    prices = [float(entry[4]) for entry in ohlcv]
    return prices

def fetch_market_prices(days=30):
    """Fetch Bitcoin prices as market proxy"""
    exchange = ccxt.binance()
    since = exchange.parse8601(timezone.now() - timezone.timedelta(days=days))
    ohlcv = exchange.fetch_ohlcv('BTC/USDT', '1d', since=since)
    return [float(entry[4]) for entry in ohlcv]

def calculate_strategy_performance(strategy, backtest):
    """Calculate performance metrics for a trading strategy backtest"""
    # Implement strategy-specific logic here
    # This is a placeholder implementation
    return {
        'total_trades': 0,
        'win_rate': 0,
        'profit_loss': 0,
        'sharpe_ratio': 0,
        'max_drawdown': 0,
    }

def generate_portfolio_chart_data(snapshots):
    """Generate chart data from portfolio snapshots"""
    data = []
    for snapshot in snapshots:
        data.append({
            'date': snapshot.snapshot_date.isoformat(),
            'total_value': float(snapshot.total_value),
            'invested_value': float(snapshot.invested_value),
            'cash_balance': float(snapshot.cash_balance),
            'daily_profit_loss': float(snapshot.daily_profit_loss),
            'daily_profit_loss_percentage': float(snapshot.daily_profit_loss_percentage)
        })
    return data
