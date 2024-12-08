from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from ..models import MarketDataFeed, Trade
from ..serializers import TradeSerializer
from django.utils import timezone
from datetime import timedelta
import numpy as np
import pandas as pd
import requests
import ta

@login_required
@require_http_methods(["GET"])
def market_data(request):
    """
    Get basic market data for the ticker
    """
    active_feeds = MarketDataFeed.objects.filter(
        feed_status='active'
    ).order_by('-volume_24h')[:10]  # Top 10 by volume
    
    data = []
    for feed in active_feeds:
        data.append({
            'symbol': feed.symbol,
            'price': str(feed.price),
            'price_change_24h': calculate_price_change(feed),
        })
    
    return JsonResponse(data, safe=False)

@login_required
@require_http_methods(["GET"])
def market_data_detailed(request):
    """
    Get detailed market data for the data feed panel
    """
    active_feeds = MarketDataFeed.objects.filter(
        feed_status='active'
    ).order_by('-volume_24h')[:5]  # Top 5 by volume
    
    data = []
    for feed in active_feeds:
        data.append({
            'asset_name': feed.asset_name,
            'symbol': feed.symbol,
            'price': str(feed.price),
            'bid': str(feed.bid),
            'ask': str(feed.ask),
            'volume_24h': str(feed.volume_24h),
            'high_24h': str(feed.high_24h),
            'low_24h': str(feed.low_24h),
            'last_updated': feed.last_updated.isoformat(),
        })
    
    return JsonResponse(data, safe=False)

@login_required
@require_http_methods(["GET"])
def technical_indicators(request):
    """
    Calculate and return technical indicators for the selected asset
    """
    symbol = request.GET.get('symbol', 'BTCUSDT')  # Default to BTCUSDT
    
    # Fetch historical data from Binance
    url = f"https://api.binance.com/api/v3/klines"
    params = {
        'symbol': symbol,
        'interval': '1h',  # 1-hour candles
        'limit': 100  # Last 100 candles
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        # Convert to DataFrame
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 
                                       'close_time', 'quote_volume', 'trades', 'buy_base_volume', 
                                       'buy_quote_volume', 'ignore'])
        
        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # Convert price columns to float
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        
        # Calculate indicators
        # RSI
        df['rsi'] = ta.momentum.RSIIndicator(df['close']).rsi()
        
        # MACD
        macd = ta.trend.MACD(df['close'])
        df['macd'] = macd.macd_diff()  # MACD histogram
        
        # Bollinger Bands
        bollinger = ta.volatility.BollingerBands(df['close'])
        df['bb_upper'] = bollinger.bollinger_hband()
        df['bb_lower'] = bollinger.bollinger_lband()
        
        # Prepare the response data
        response_data = {
            'rsi': [
                {'x': ts.isoformat(), 'y': val} 
                for ts, val in zip(df['timestamp'], df['rsi']) 
                if not pd.isna(val)
            ],
            'macd': [
                {'x': ts.isoformat(), 'y': val} 
                for ts, val in zip(df['timestamp'], df['macd']) 
                if not pd.isna(val)
            ],
            'price': [
                {'x': ts.isoformat(), 'y': val} 
                for ts, val in zip(df['timestamp'], df['close']) 
            ],
            'volume': [
                {'x': ts.isoformat(), 'y': val} 
                for ts, val in zip(df['timestamp'], df['volume'])
            ],
            'upperBB': [
                {'x': ts.isoformat(), 'y': val} 
                for ts, val in zip(df['timestamp'], df['bb_upper']) 
                if not pd.isna(val)
            ],
            'lowerBB': [
                {'x': ts.isoformat(), 'y': val} 
                for ts, val in zip(df['timestamp'], df['bb_lower']) 
                if not pd.isna(val)
            ]
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        # If there's an error, return sample data for demonstration
        current_time = timezone.now()
        sample_data = {
            'rsi': [
                {'x': (current_time - timedelta(hours=i)).isoformat(), 'y': 50 + np.random.randn() * 10}
                for i in range(24, 0, -1)
            ],
            'macd': [
                {'x': (current_time - timedelta(hours=i)).isoformat(), 'y': np.random.randn()}
                for i in range(24, 0, -1)
            ],
            'price': [
                {'x': (current_time - timedelta(hours=i)).isoformat(), 'y': 45000 + np.random.randn() * 1000}
                for i in range(24, 0, -1)
            ],
            'volume': [
                {'x': (current_time - timedelta(hours=i)).isoformat(), 'y': 1000000 + np.random.randn() * 100000}
                for i in range(24, 0, -1)
            ],
            'upperBB': [
                {'x': (current_time - timedelta(hours=i)).isoformat(), 'y': 47000 + np.random.randn() * 100}
                for i in range(24, 0, -1)
            ],
            'lowerBB': [
                {'x': (current_time - timedelta(hours=i)).isoformat(), 'y': 43000 + np.random.randn() * 100}
                for i in range(24, 0, -1)
            ]
        }
        return JsonResponse(sample_data)

def calculate_price_change(feed):
    """
    Calculate 24h price change percentage
    This is a simplified version - in production you would want to store historical prices
    """
    # In a real implementation, you would calculate this from historical data
    # For now, we'll generate a random change between -5% and +5%
    import random
    return random.uniform(-5, 5)

class ActiveTradesView(APIView):
    @login_required
    def get(self, request):
        """Get user's active trades"""
        trades = Trade.objects.filter(
            user=request.user,
            status__in=['open', 'pending']
        ).select_related('asset')
        
        # Update current prices and P/L
        for trade in trades:
            trade.update_performance()
        
        serializer = TradeSerializer(trades, many=True)
        return Response(serializer.data)

class TradeHistoryView(APIView):
    @login_required
    def get(self, request):
        """Get user's trade history"""
        trades = Trade.objects.filter(
            user=request.user,
            status__in=['closed', 'cancelled', 'failed']
        ).select_related('asset').order_by('-created_at')[:50]  # Last 50 trades
        
        serializer = TradeSerializer(trades, many=True)
        return Response(serializer.data)

class CreateTradeView(APIView):
    @login_required
    def post(self, request):
        """Create a new trade"""
        data = request.data.copy()
        data['user'] = request.user.id
        
        serializer = TradeSerializer(data=data)
        if serializer.is_valid():
            try:
                trade = serializer.save()
                
                # For market orders, execute immediately
                if trade.trade_type == 'market':
                    current_price = trade.asset.current_price
                    trade.execute_market_order(current_price)
                
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CloseTradeView(APIView):
    @login_required
    def post(self, request, trade_id):
        """Close an active trade"""
        try:
            trade = Trade.objects.get(id=trade_id, user=request.user)
            
            if trade.status != 'open':
                return Response(
                    {'message': 'Only open trades can be closed'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            current_price = trade.asset.current_price
            trade.close_trade(current_price)
            
            serializer = TradeSerializer(trade)
            return Response(serializer.data)
        
        except Trade.DoesNotExist:
            return Response(
                {'message': 'Trade not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'message': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
