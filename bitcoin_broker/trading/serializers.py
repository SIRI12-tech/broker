from rest_framework import serializers
from .models import Trade, Asset

class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = ['id', 'symbol', 'name', 'current_price']

class TradeSerializer(serializers.ModelSerializer):
    asset = AssetSerializer(read_only=True)
    asset_id = serializers.IntegerField(write_only=True)
    profit_loss = serializers.DecimalField(max_digits=20, decimal_places=8, read_only=True)
    profit_loss_percentage = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)
    current_price = serializers.DecimalField(max_digits=20, decimal_places=8, read_only=True)

    class Meta:
        model = Trade
        fields = [
            'id', 'user', 'asset', 'asset_id', 'trade_type', 'side',
            'status', 'entry_price', 'exit_price', 'target_price',
            'stop_loss_price', 'quantity', 'filled_quantity',
            'remaining_quantity', 'leverage', 'profit_loss',
            'profit_loss_percentage', 'current_price', 'notes',
            'created_at', 'updated_at', 'closed_at'
        ]
        read_only_fields = [
            'id', 'user', 'status', 'filled_quantity', 'remaining_quantity',
            'profit_loss', 'profit_loss_percentage', 'current_price',
            'created_at', 'updated_at', 'closed_at'
        ]

    def validate(self, data):
        """
        Validate trade data
        """
        # Ensure required price fields are present based on trade type
        if data['trade_type'] == 'limit' and not data.get('target_price'):
            raise serializers.ValidationError({
                'target_price': 'Target price is required for limit orders'
            })
        
        if data['trade_type'] == 'stop_loss' and not data.get('stop_loss_price'):
            raise serializers.ValidationError({
                'stop_loss_price': 'Stop loss price is required for stop loss orders'
            })
        
        # Validate quantity
        if data.get('quantity', 0) <= 0:
            raise serializers.ValidationError({
                'quantity': 'Quantity must be greater than 0'
            })
        
        # Validate leverage
        if data.get('leverage', 1) < 1:
            raise serializers.ValidationError({
                'leverage': 'Leverage must be at least 1'
            })
        
        return data
