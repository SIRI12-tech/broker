from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import Asset, MarketNews, MarketSentiment
import ccxt
import yfinance as yf
import logging

logger = logging.getLogger(__name__)

@shared_task
def update_all_asset_metrics():
    """Update performance metrics for all active assets."""
    assets = Asset.objects.filter(is_active=True)
    for asset in assets:
        update_asset_metrics.delay(asset.id)

@shared_task
def update_asset_metrics(asset_id):
    """Update performance metrics for a specific asset."""
    try:
        asset = Asset.objects.get(id=asset_id)
        asset.update_performance_metrics()
    except Asset.DoesNotExist:
        pass  # Asset may have been deleted

@shared_task
def update_market_data():
    """Update market data for all asset types."""
    try:
        update_crypto_prices()
        update_forex_prices()
        update_stock_prices()
        logger.info("Market data updated successfully")
    except Exception as e:
        logger.error(f"Error updating market data: {str(e)}")
        raise

@shared_task
def update_crypto_prices():
    """Update cryptocurrency prices using CCXT."""
    try:
        exchange = ccxt.binance()
        assets = Asset.objects.filter(asset_type='crypto')
        
        for asset in assets:
            try:
                ticker = exchange.fetch_ticker(f"{asset.symbol}/USDT")
                asset.current_price = ticker['last']
                asset.price_change_24h = ticker['last'] - ticker['open']
                asset.price_change_percentage_24h = ticker.get('percentage', 0)
                asset.volume_24h = ticker['quoteVolume']
                asset.high_24h = ticker['high']
                asset.low_24h = ticker['low']
                asset.save()
            except Exception as e:
                logger.error(f"Error updating {asset.symbol}: {str(e)}")
                continue
        
        logger.info(f"Updated prices for {assets.count()} cryptocurrencies")
    except Exception as e:
        logger.error(f"Error in update_crypto_prices: {str(e)}")
        raise

@shared_task
def update_forex_prices():
    """Update forex prices."""
    # TODO: Implement Alpha Vantage API integration
    try:
        assets = Asset.objects.filter(asset_type='forex')
        for asset in assets:
            try:
                # Placeholder for actual API call
                asset._update_forex_metrics()
            except Exception as e:
                logger.error(f"Error updating {asset.symbol}: {str(e)}")
                continue
        
        logger.info(f"Updated prices for {assets.count()} forex pairs")
    except Exception as e:
        logger.error(f"Error in update_forex_prices: {str(e)}")
        raise

@shared_task
def update_stock_prices():
    """Update stock prices using Yahoo Finance."""
    try:
        assets = Asset.objects.filter(asset_type='stock')
        for asset in assets:
            try:
                ticker = yf.Ticker(asset.symbol)
                info = ticker.info
                
                asset.current_price = info.get('regularMarketPrice', 0)
                asset.price_change_24h = info.get('regularMarketChange', 0)
                asset.price_change_percentage_24h = info.get('regularMarketChangePercent', 0)
                asset.volume_24h = info.get('regularMarketVolume', 0)
                asset.high_24h = info.get('regularMarketDayHigh', 0)
                asset.low_24h = info.get('regularMarketDayLow', 0)
                asset.market_cap = info.get('marketCap', 0)
                asset.save()
            except Exception as e:
                logger.error(f"Error updating {asset.symbol}: {str(e)}")
                continue
        
        logger.info(f"Updated prices for {assets.count()} stocks")
    except Exception as e:
        logger.error(f"Error in update_stock_prices: {str(e)}")
        raise

@shared_task
def cleanup_old_metrics():
    """Clean up old performance metrics data."""
    threshold = timezone.now() - timedelta(days=30)
    MarketNews.objects.filter(date__lt=threshold).delete()
    MarketSentiment.objects.filter(date__lt=threshold).delete()
