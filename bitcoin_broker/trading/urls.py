from django.urls import path, include
from . import views
from . import views_portfolio
from . import views_trading
from .views.payment import (
    order_confirmation,
    process_payment,
    process_card_payment,
    process_crypto_payment,
    payment_success,
    payment_failed,
    braintree_webhook,
)
from .views.admin_views import admin_dashboard
from .views import api

app_name = 'trading'

urlpatterns = [
    # Authentication URLs
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('signup/', views.signup, name='signup'),
    path('verify-email/<int:user_id>/', views.verify_email, name='verify_email'),
    path('verify-phone/', views.verify_phone, name='verify_phone'),
    path('setup-2fa/', views.setup_2fa, name='setup_2fa'),
    
    # Password Reset URLs
    path('password-reset/', views.password_reset_request, name='password_reset'),
    path('password-reset/done/', views.password_reset_done, name='password_reset_done'),
    path('password-reset/confirm/<uidb64>/<token>/', views.password_reset_confirm, name='password_reset_confirm'),
    path('password-reset/complete/', views.password_reset_complete, name='password_reset_complete'),
    
    # Static Pages
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('terms/', views.terms, name='terms'),
    path('privacy/', views.privacy, name='privacy'),
    path('faq/', views.faq, name='faq'),
    
    # Dashboard URLs
    path('dashboard/', views.dashboard, name='dashboard'),
    path('trading/', views.trading, name='trading'),
    
    # Portfolio URLs
    path('portfolio/', views_portfolio.portfolio_dashboard, name='portfolio'),
    path('portfolio/analysis/', views_portfolio.portfolio_analysis, name='portfolio_analysis'),
    path('portfolio/position/<int:position_id>/', views_portfolio.position_detail, name='position_detail'),
    path('portfolio/watchlist/', views_portfolio.watchlist, name='watchlist'),
    path('portfolio/transactions/', views_portfolio.transaction_history, name='transaction_history'),
    
    # Trading URLs
    path('order/place/', views.place_order, name='place_order'),
    path('alert/set/', views.set_price_alert, name='set_price_alert'),
    path('api/prices/', views.get_crypto_prices, name='get_crypto_prices'),
    path('api/portfolio/chart-data/', views_trading.get_portfolio_chart_data, name='get_portfolio_chart_data'),
    
    # API Endpoints
    path('get_crypto_prices/', views.get_crypto_prices, name='get_crypto_prices'),
    path('api/market-data/', api.market_data, name='api_market_data'),
    path('api/market-data/detailed/', api.market_data_detailed, name='api_market_data_detailed'),
    path('api/technical-indicators/', api.technical_indicators, name='api_technical_indicators'),
    
    # Trade Management URLs
    path('api/trades/active/', views.api.ActiveTradesView.as_view(), name='api_active_trades'),
    path('api/trades/history/', views.api.TradeHistoryView.as_view(), name='api_trade_history'),
    path('api/trades/create/', views.api.CreateTradeView.as_view(), name='api_create_trade'),
    path('api/trades/<int:trade_id>/close/', views.api.CloseTradeView.as_view(), name='api_close_trade'),
    
    # Payment URLs
    path('order/confirm/', order_confirmation, name='order_confirmation'),
    path('payment/process/', process_payment, name='process_payment'),
    path('payment/card/', process_card_payment, name='process_card_payment'),
    path('payment/crypto/', process_crypto_payment, name='process_crypto_payment'),
    path('payment/success/<uuid:payment_id>/', payment_success, name='payment_success'),
    path('payment/failed/', payment_failed, name='payment_failed'),
    path('webhook/braintree/', braintree_webhook, name='braintree_webhook'),
    
    # Wallet URLs
    path('wallet/generate/', views_trading.wallet_generate, name='wallet_generate'),
    path('wallet/balance/', views_trading.wallet_balance, name='wallet_balance'),
    path('wallet/withdraw/', views_trading.wallet_withdraw, name='wallet_withdraw'),
    path('wallet/deposit/', views_trading.wallet_deposit, name='wallet_deposit'),
    
    # KYC URLs
    path('kyc/status/', views.kyc_status, name='kyc_status'),
    path('kyc/upload/', views.kyc_upload, name='kyc_upload'),
    
    # Verification URLs
    path('resend-verification/<int:user_id>/', views.resend_verification, name='resend_verification'),
    path('resend-verification/', views.resend_verification, name='resend_verification'),
    
    # Admin URLs
    path('admin/dashboard/', admin_dashboard, name='admin_dashboard'),
    
    # Additional URL patterns
    path('verify-email/', views.verify_email, name='verify_email'),
    path('place-order/', views_trading.place_order, name='place_order'),
    path('order-confirmation/<int:order_id>/', views_trading.order_confirmation, name='order_confirmation'),
    path('order-entry/', views_trading.order_entry, name='order_entry'),
    path('portfolio-analysis/', views_trading.portfolio_analysis, name='portfolio_analysis'),
    path('api/portfolio-history/', views_trading.get_portfolio_chart_data, name='get_portfolio_history'),
]
