from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid
from django.utils import timezone
import logging
import ccxt
import yfinance as yf

logger = logging.getLogger(__name__)

class UserProfile(models.Model):
    VERIFICATION_STATUS_CHOICES = [
        ('unverified', 'Unverified'),
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]
    
    KYC_STATUS_CHOICES = [
        ('not_submitted', 'Not Submitted'),
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True, null=True)
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS_CHOICES, default='unverified')
    is_phone_verified = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    kyc_status = models.CharField(max_length=20, choices=KYC_STATUS_CHOICES, default='not_submitted')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user.username}'s Profile"

    def save(self, *args, **kwargs):
        if not self.pk:  # If this is a new profile
            super().save(*args, **kwargs)
            # Create associated Account
            Account.objects.create(user=self.user)
        else:
            super().save(*args, **kwargs)

class KYCDocument(models.Model):
    DOCUMENT_TYPES = [
        ('passport', 'Passport'),
        ('id_card', 'ID Card'),
        ('drivers_license', 'Driver\'s License'),
        ('utility_bill', 'Utility Bill'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    document_number = models.CharField(max_length=50)
    document_file = models.FileField(upload_to='kyc_documents/')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    rejection_reason = models.TextField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.document_type}"

class Portfolio(models.Model):
    user = models.OneToOneField(UserProfile, on_delete=models.CASCADE)
    total_value = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    total_profit_loss = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    last_updated = models.DateTimeField(auto_now=True)

class Asset(models.Model):
    """Model for tradeable assets including cryptocurrencies, forex, and stocks."""
    ASSET_TYPES = [
        ('crypto', 'Cryptocurrency'),
        ('forex', 'Forex'),
        ('stock', 'Stock'),
    ]
    
    symbol = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    asset_type = models.CharField(max_length=10, choices=ASSET_TYPES)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    # For stocks
    exchange = models.CharField(max_length=50, blank=True)
    sector = models.CharField(max_length=100, blank=True)
    market_cap = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    
    # For forex
    base_currency = models.CharField(max_length=3, blank=True)
    quote_currency = models.CharField(max_length=3, blank=True)
    
    # Performance metrics
    current_price = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    price_change_24h = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price_change_percentage_24h = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    volume_24h = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    high_24h = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    low_24h = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['asset_type', '-price_change_percentage_24h']),
        ]
    
    def __str__(self):
        return f"{self.symbol} ({self.get_asset_type_display()})"
    
    @staticmethod
    def get_top_performers(asset_type=None, limit=10):
        """Get top performing assets by 24h price change percentage."""
        queryset = Asset.objects.filter(is_active=True)
        if asset_type:
            queryset = queryset.filter(asset_type=asset_type)
        return queryset.order_by('-price_change_percentage_24h')[:limit]
    
    def update_performance_metrics(self):
        """Update asset performance metrics from external API."""
        try:
            if self.asset_type == 'crypto':
                self._update_crypto_metrics()
            elif self.asset_type == 'forex':
                self._update_forex_metrics()
            elif self.asset_type == 'stock':
                self._update_stock_metrics()
        except Exception as e:
            logger.error(f"Error updating metrics for {self.symbol}: {str(e)}")
    
    def _update_crypto_metrics(self):
        """Update cryptocurrency metrics using CCXT."""
        try:
            exchange = ccxt.binance()
            ticker = exchange.fetch_ticker(f"{self.symbol}/USDT")
            
            self.current_price = ticker['last']
            self.price_change_24h = ticker['last'] - ticker['open']
            self.price_change_percentage_24h = ticker.get('percentage', 0)
            self.volume_24h = ticker['quoteVolume']
            self.high_24h = ticker['high']
            self.low_24h = ticker['low']
            self.save()
        except Exception as e:
            logger.error(f"Error updating crypto metrics for {self.symbol}: {str(e)}")
            raise

    def _update_forex_metrics(self):
        """Update forex metrics using Alpha Vantage API."""
        try:
            from alpha_vantage.foreignexchange import ForeignExchange
            from django.conf import settings
            
            fx = ForeignExchange(key=settings.ALPHA_VANTAGE_API_KEY)
            # Extract base and quote currencies from symbol (e.g., 'EURUSD')
            base_currency = self.symbol[:3]
            quote_currency = self.symbol[3:]
            
            # Get real-time exchange rate
            data, _ = fx.get_currency_exchange_rate(
                from_currency=base_currency,
                to_currency=quote_currency
            )
            
            # Get daily time series for percentage change calculation
            daily_data, _ = fx.get_currency_exchange_daily(
                from_symbol=base_currency,
                to_symbol=quote_currency,
                outputsize='compact'
            )
            
            # Extract current price
            self.current_price = float(data['5. Exchange Rate'])
            
            # Calculate 24h changes
            daily_prices = list(daily_data.values())[:2]  # Get last two days
            if len(daily_prices) >= 2:
                today_close = float(daily_prices[0]['4. close'])
                yesterday_close = float(daily_prices[1]['4. close'])
                
                self.price_change_24h = today_close - yesterday_close
                self.price_change_percentage_24h = (self.price_change_24h / yesterday_close) * 100
                self.high_24h = float(daily_prices[0]['2. high'])
                self.low_24h = float(daily_prices[0]['3. low'])
                self.volume_24h = float(daily_prices[0]['5. volume'])
            
            self.save()
            logger.info(f"Updated forex rates for {self.symbol}")
        except Exception as e:
            logger.error(f"Error updating forex metrics for {self.symbol}: {str(e)}")
            raise

    def _update_stock_metrics(self):
        """Update stock metrics using Yahoo Finance."""
        try:
            ticker = yf.Ticker(self.symbol)
            info = ticker.info
            
            self.current_price = info.get('regularMarketPrice', 0)
            self.price_change_24h = info.get('regularMarketChange', 0)
            self.price_change_percentage_24h = info.get('regularMarketChangePercent', 0)
            self.volume_24h = info.get('regularMarketVolume', 0)
            self.high_24h = info.get('regularMarketDayHigh', 0)
            self.low_24h = info.get('regularMarketDayLow', 0)
            self.market_cap = info.get('marketCap', 0)
            self.save()
        except Exception as e:
            logger.error(f"Error updating stock metrics for {self.symbol}: {str(e)}")
            raise

class Position(models.Model):
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=20, decimal_places=8)
    average_buy_price = models.DecimalField(max_digits=20, decimal_places=8)
    current_value = models.DecimalField(max_digits=20, decimal_places=2)
    profit_loss = models.DecimalField(max_digits=20, decimal_places=2)
    last_updated = models.DateTimeField(auto_now=True)

class Order(models.Model):
    ORDER_TYPES = [
        ('buy', 'Buy'),
        ('sell', 'Sell'),
    ]
    
    ORDER_STATUS = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    crypto_asset = models.CharField(max_length=10, default='BTC')  # e.g., BTC, ETH
    amount = models.DecimalField(max_digits=18, decimal_places=8, default=0)
    order_type = models.CharField(max_length=4, choices=ORDER_TYPES)
    status = models.CharField(max_length=10, choices=ORDER_STATUS, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.order_type.upper()} {self.amount} {self.crypto_asset}"

class Payment(models.Model):
    PAYMENT_METHODS = [
        ('card', 'Credit/Debit Card'),
        ('paypal', 'PayPal'),
        ('crypto', 'Cryptocurrency'),
        ('bank', 'Bank Transfer'),
    ]
    
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    
    # Payment provider specific fields
    provider_reference = models.CharField(max_length=255, null=True, blank=True)
    provider_status = models.CharField(max_length=100, null=True, blank=True)
    provider_response = models.JSONField(null=True, blank=True)
    
    # Cryptocurrency specific fields
    crypto_address = models.CharField(max_length=255, null=True, blank=True)
    crypto_amount = models.DecimalField(max_digits=18, decimal_places=8, null=True, blank=True)
    crypto_currency = models.CharField(max_length=10, null=True, blank=True)
    tx_hash = models.CharField(max_length=255, null=True, blank=True)
    
    # Card payment specific fields
    card_last4 = models.CharField(max_length=4, null=True, blank=True)
    card_brand = models.CharField(max_length=20, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Payment for Order {self.order.payment_reference}"

    class Meta:
        ordering = ['-created_at']

class Transaction(models.Model):
    TRANSACTION_TYPE = (
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('trade', 'Trade')
    )
    
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPE)
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    fee = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    status = models.CharField(max_length=20, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True)

class PriceAlert(models.Model):
    ALERT_TYPES = [
        ('price_above', 'Price Above'),
        ('price_below', 'Price Below'),
        ('price_change_pct', 'Price Change %'),
        ('volume_above', 'Volume Above'),
        ('rsi_above', 'RSI Above'),
        ('rsi_below', 'RSI Below'),
    ]
    
    ALERT_STATUS = [
        ('active', 'Active'),
        ('triggered', 'Triggered'),
        ('expired', 'Expired'),
    ]
    
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    price_target = models.DecimalField(max_digits=18, decimal_places=8, null=True, blank=True)
    percentage_target = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    volume_target = models.DecimalField(max_digits=18, decimal_places=8, null=True, blank=True)
    rsi_target = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=10, choices=ALERT_STATUS, default='active')
    notification_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.asset.symbol} {self.alert_type} Alert"

class AIRecommendation(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    recommendation_type = models.CharField(max_length=10)  # buy, sell, hold
    confidence_score = models.DecimalField(max_digits=5, decimal_places=2)
    reasoning = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

class MarketSentiment(models.Model):
    """Model for market sentiment analysis."""
    date = models.DateTimeField(default=timezone.now)
    sentiment_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    source = models.CharField(max_length=100, default='')
    description = models.TextField(default='')
    
    def __str__(self):
        return f"Sentiment {self.sentiment_score} on {self.date}"

class MarketNews(models.Model):
    """Model for market news and updates."""
    date = models.DateTimeField(default=timezone.now)
    title = models.CharField(max_length=200, default='')
    content = models.TextField(default='')
    source = models.CharField(max_length=100, default='')
    url = models.URLField(default='')
    related_assets = models.ManyToManyField(Asset)
    impact = models.CharField(max_length=20, choices=[
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ], default='medium')
    
    def __str__(self):
        return self.title

class EconomicCalendar(models.Model):
    """Model for economic events and announcements."""
    date = models.DateTimeField(default=timezone.now)
    event = models.CharField(max_length=200, default='')
    country = models.CharField(max_length=100, default='')
    impact = models.CharField(max_length=20, choices=[
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ], default='medium')
    forecast = models.CharField(max_length=100, null=True, blank=True)
    previous = models.CharField(max_length=100, null=True, blank=True)
    actual = models.CharField(max_length=100, null=True, blank=True)
    
    def __str__(self):
        return f"{self.event} on {self.date}"

class UserSettings(models.Model):
    user = models.OneToOneField(UserProfile, on_delete=models.CASCADE)
    notification_preferences = models.JSONField(default=dict)
    trading_preferences = models.JSONField(default=dict)
    ui_preferences = models.JSONField(default=dict)
    api_key = models.UUIDField(default=uuid.uuid4, editable=False)
    webhook_url = models.URLField(blank=True, null=True)

class PortfolioSnapshot(models.Model):
    """Model for tracking portfolio value over time."""
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(default=timezone.now)
    total_value = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    cash_balance = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    asset_value = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    pnl_24h = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    pnl_percentage_24h = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    class Meta:
        ordering = ['-timestamp']
        get_latest_by = 'timestamp'
    
    def __str__(self):
        return f"{self.portfolio.user.username}'s portfolio snapshot at {self.timestamp}"

class AssetMetrics(models.Model):
    """Technical and fundamental metrics for assets"""
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    market_cap = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    volume_24h = models.DecimalField(max_digits=20, decimal_places=2)
    high_24h = models.DecimalField(max_digits=20, decimal_places=8)
    low_24h = models.DecimalField(max_digits=20, decimal_places=8)
    price_change_24h = models.DecimalField(max_digits=10, decimal_places=2)
    price_change_7d = models.DecimalField(max_digits=10, decimal_places=2)
    price_change_30d = models.DecimalField(max_digits=10, decimal_places=2)
    rsi_14 = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    ma_50 = models.DecimalField(max_digits=20, decimal_places=8, null=True)
    ma_200 = models.DecimalField(max_digits=20, decimal_places=8, null=True)
    updated_at = models.DateTimeField(auto_now=True)

class RiskMetrics(models.Model):
    """Portfolio risk analysis metrics"""
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE)
    volatility = models.DecimalField(max_digits=10, decimal_places=2)
    sharpe_ratio = models.DecimalField(max_digits=10, decimal_places=2)
    beta = models.DecimalField(max_digits=10, decimal_places=2)
    alpha = models.DecimalField(max_digits=10, decimal_places=2)
    max_drawdown = models.DecimalField(max_digits=10, decimal_places=2)
    var_95 = models.DecimalField(max_digits=10, decimal_places=2)  # Value at Risk (95% confidence)
    calculated_at = models.DateTimeField(auto_now=True)

class WatchList(models.Model):
    """User's watchlist for tracking assets"""
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    assets = models.ManyToManyField(Asset)
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class TradingStrategy(models.Model):
    """Custom trading strategies"""
    TIMEFRAMES = (
        ('1m', '1 Minute'),
        ('5m', '5 Minutes'),
        ('15m', '15 Minutes'),
        ('1h', '1 Hour'),
        ('4h', '4 Hours'),
        ('1d', '1 Day'),
    )
    
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField()
    timeframe = models.CharField(max_length=3, choices=TIMEFRAMES)
    indicators = models.JSONField()  # Store indicator settings
    entry_conditions = models.JSONField()  # Store entry conditions
    exit_conditions = models.JSONField()  # Store exit conditions
    risk_per_trade = models.DecimalField(max_digits=5, decimal_places=2)  # Percentage
    take_profit = models.DecimalField(max_digits=5, decimal_places=2)  # Percentage
    stop_loss = models.DecimalField(max_digits=5, decimal_places=2)  # Percentage
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class BacktestResult(models.Model):
    """Model for storing strategy backtest results."""
    strategy = models.ForeignKey(TradingStrategy, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    start_date = models.DateField()
    end_date = models.DateField()
    initial_capital = models.DecimalField(max_digits=18, decimal_places=8)
    final_capital = models.DecimalField(max_digits=18, decimal_places=8)
    total_trades = models.IntegerField()
    win_rate = models.DecimalField(max_digits=5, decimal_places=2)
    profit_loss = models.DecimalField(max_digits=18, decimal_places=8)
    max_drawdown = models.DecimalField(max_digits=5, decimal_places=2)
    sharpe_ratio = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Backtest for {self.strategy} ({self.start_date} to {self.end_date})"

class StrategyBacktest(models.Model):
    """Backtest results for trading strategies"""
    strategy = models.ForeignKey(TradingStrategy, on_delete=models.CASCADE)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    initial_balance = models.DecimalField(max_digits=20, decimal_places=2)
    final_balance = models.DecimalField(max_digits=20, decimal_places=2)
    total_trades = models.IntegerField()
    winning_trades = models.IntegerField()
    losing_trades = models.IntegerField()
    profit_factor = models.DecimalField(max_digits=10, decimal_places=2)
    max_drawdown = models.DecimalField(max_digits=10, decimal_places=2)
    sharpe_ratio = models.DecimalField(max_digits=10, decimal_places=2)
    detailed_results = models.JSONField()  # Store detailed backtest results
    created_at = models.DateTimeField(auto_now_add=True)

class NotificationLog(models.Model):
    """Log of notifications sent to users"""
    NOTIFICATION_TYPES = (
        ('price_alert', 'Price Alert'),
        ('trade_execution', 'Trade Execution'),
        ('news', 'News Alert'),
        ('system', 'System Notification'),
    )
    
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

class VerificationCode(models.Model):
    """Model for storing verification codes"""
    CODE_TYPES = (
        ('email', 'Email Verification'),
        ('phone', 'Phone Verification'),
        ('phone_fallback', 'Phone Fallback'),
        ('2fa', 'Two-Factor Authentication'),
    )
    
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    code_type = models.CharField(max_length=20, choices=CODE_TYPES)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(minutes=10)
        super().save(*args, **kwargs)
    
    def is_valid(self):
        """Check if the code is still valid"""
        return (
            not self.is_used and
            timezone.now() <= self.expires_at
        )

    class Meta:
        ordering = ['-created_at']

class Wallet(models.Model):
    """Cryptocurrency wallet model."""
    WALLET_STATUS = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    address = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=20, choices=WALLET_STATUS, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wallet ({self.address[:10]}...{self.address[-8:]})"

class WalletTransaction(models.Model):
    """Model for tracking wallet transactions."""
    TRANSACTION_TYPES = (
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
    )
    
    TRANSACTION_STATUS = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    )

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=18, decimal_places=8)
    currency = models.CharField(max_length=10)  # e.g., BTC, ETH
    status = models.CharField(max_length=20, choices=TRANSACTION_STATUS, default='pending')
    tx_hash = models.CharField(max_length=255, null=True, blank=True)  # blockchain transaction hash
    destination_address = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.transaction_type} - {self.amount} {self.currency}"

class Account(models.Model):
    ACCOUNT_STATUS = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    margin_used = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    available_margin = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    portfolio_value = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    account_status = models.CharField(max_length=20, choices=ACCOUNT_STATUS, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Account"

    def calculate_available_margin(self):
        self.available_margin = self.balance - self.margin_used
        self.save()
        return self.available_margin

    def update_portfolio_value(self):
        # Calculate total value of all positions plus available balance
        positions_value = Position.objects.filter(portfolio__user=self.user.userprofile).aggregate(
            total=models.Sum(models.F('current_value'), default=0)
        )['total']
        self.portfolio_value = positions_value + self.balance
        self.save()
        return self.portfolio_value

class MarketDataFeed(models.Model):
    FEED_STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('pending', 'Pending Approval'),
        ('rejected', 'Rejected'),
    ]

    DATA_SOURCE_CHOICES = [
        ('binance', 'Binance'),
        ('coinbase', 'Coinbase'),
        ('kraken', 'Kraken'),
        ('manual', 'Manual Entry'),
        ('other', 'Other'),
    ]

    asset_name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=20)
    price = models.DecimalField(max_digits=20, decimal_places=8)
    bid = models.DecimalField(max_digits=20, decimal_places=8)
    ask = models.DecimalField(max_digits=20, decimal_places=8)
    volume_24h = models.DecimalField(max_digits=24, decimal_places=8)
    high_24h = models.DecimalField(max_digits=20, decimal_places=8)
    low_24h = models.DecimalField(max_digits=20, decimal_places=8)
    data_source = models.CharField(max_length=20, choices=DATA_SOURCE_CHOICES)
    feed_status = models.CharField(max_length=20, choices=FEED_STATUS_CHOICES, default='pending')
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = 'Market Data Feed'
        verbose_name_plural = 'Market Data Feeds'
        ordering = ['-last_updated']

    def __str__(self):
        return f"{self.asset_name} ({self.symbol}) - {self.get_feed_status_display()}"

    def clean(self):
        if self.ask < self.bid:
            raise ValidationError({'ask': 'Ask price cannot be lower than bid price'})

class Trade(models.Model):
    """Model for managing individual trades"""
    
    TRADE_TYPES = [
        ('market', 'Market Order'),
        ('limit', 'Limit Order'),
        ('stop_loss', 'Stop Loss'),
        ('stop_limit', 'Stop Limit'),
        ('trailing_stop', 'Trailing Stop'),
    ]
    
    TRADE_STATUS = [
        ('pending', 'Pending'),
        ('open', 'Open'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled'),
    ]
    
    SIDE_CHOICES = [
        ('buy', 'Buy'),
        ('sell', 'Sell'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    trade_type = models.CharField(max_length=20, choices=TRADE_TYPES)
    side = models.CharField(max_length=4, choices=SIDE_CHOICES)
    status = models.CharField(max_length=10, choices=TRADE_STATUS, default='pending')
    quantity = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    entry_price = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    current_price = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    take_profit = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    stop_loss = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    trailing_stop = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    profit_loss = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    profit_loss_percentage = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fee = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    opened_at = models.DateTimeField(default=timezone.now)
    closed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['asset', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.asset.symbol} {self.side} {self.status}"
    
    def update_profit_loss(self):
        """Update profit/loss based on current price"""
        if self.status == 'open':
            if self.side == 'buy':
                self.profit_loss = (self.current_price - self.entry_price) * self.quantity
            else:  # sell
                self.profit_loss = (self.entry_price - self.current_price) * self.quantity
            
            if self.entry_price != 0:
                self.profit_loss_percentage = (self.profit_loss / (self.entry_price * self.quantity)) * 100
            self.save()

    def close_trade(self, exit_price=None):
        """Close the trade at specified price or current market price"""
        if self.status != 'open':
            return
        
        if exit_price:
            self.current_price = exit_price
        
        self.update_profit_loss()
        self.status = 'closed'
        self.closed_at = timezone.now()
        self.save()
        
        # Create transaction record
        Transaction.objects.create(
            user=self.user.userprofile,
            transaction_type='trade',
            amount=self.profit_loss,
            fee=self.fee,
            status='completed',
            completed_at=timezone.now()
        )
