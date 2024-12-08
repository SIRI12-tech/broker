"""
Payment settings for the trading platform.
These settings should be moved to environment variables in production.
"""
import os
from django.conf import settings

# Square Settings
SQUARE_APPLICATION_ID = os.getenv('SQUARE_APPLICATION_ID', 'sandbox-sq0idb-jjdXDu008SwJvZBDdQ9eEw')
SQUARE_ACCESS_TOKEN = os.getenv('SQUARE_ACCESS_TOKEN', 'EAAAl6btUUYwx7E9xHpi_xss6-X4CnXYCSbxuBOtuPPS3Q0KsdOEmzM2DDI0ZGla')
SQUARE_LOCATION_ID = os.getenv('SQUARE_LOCATION_ID', 'LNXT4PWCRPJ9B')
SQUARE_ENVIRONMENT = os.getenv('SQUARE_ENVIRONMENT', 'sandbox')  # Change to 'production' in production

# Cryptocurrency Settings
SUPPORTED_CRYPTOCURRENCIES = {
    'BTC': {
        'name': 'Bitcoin',
        'symbol': 'BTC',
        'network': 'bitcoin',
        'min_confirmations': 3,
    },
    'ETH': {
        'name': 'Ethereum',
        'symbol': 'ETH',
        'network': 'ethereum',
        'min_confirmations': 12,
    }
}

# Payment Method Settings
PAYMENT_METHODS = {
    'card': {
        'enabled': True,
        'min_amount': 10.00,
        'max_amount': 10000.00,
        'fee_percentage': 2.9,
        'fee_fixed': 0.30,
        'provider': 'square',
        'supported_cards': ['visa', 'mastercard', 'amex', 'discover'],
    },
    'crypto': {
        'enabled': True,
        'min_amount': 50.00,
        'max_amount': 100000.00,
        'fee_percentage': 1.0,
        'fee_fixed': 0.00,
        'supported_currencies': list(SUPPORTED_CRYPTOCURRENCIES.keys()),
    },
    'bank': {
        'enabled': True,
        'min_amount': 100.00,
        'max_amount': 1000000.00,
        'fee_percentage': 0.0,
        'fee_fixed': 15.00,
    },
}

# General Payment Settings
PAYMENT_SETTINGS = {
    'default_currency': 'USD',
    'order_expiry_minutes': 30,
    'max_payment_attempts': 3,
    'require_kyc_above': 1000.00,
    'max_daily_limit': 10000.00,
    'max_monthly_limit': 100000.00,
}

# Payment Status Messages
PAYMENT_MESSAGES = {
    'success': 'Your payment has been processed successfully.',
    'pending': 'Your payment is being processed. Please wait...',
    'failed': 'Payment failed. Please try again or choose a different payment method.',
    'expired': 'The payment session has expired. Please start over.',
    'cancelled': 'Payment was cancelled. No charges were made.',
}
