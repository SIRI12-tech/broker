from django.urls import path
from . import views_admin

app_name = 'admin'

urlpatterns = [
    # User Management
    path('dashboard/', views_admin.admin_dashboard, name='dashboard'),
    path('users/', views_admin.user_management, name='users'),
    path('users/create/', views_admin.create_user, name='create_user'),
    path('users/<int:user_id>/edit/', views_admin.edit_user, name='edit_user'),
    path('users/<int:user_id>/delete/', views_admin.delete_user, name='delete_user'),
    path('users/verify/', views_admin.verify_users, name='verify_users'),
    
    # Financial Operations
    path('finances/', views_admin.financial_operations, name='finances'),
    path('finances/transactions/', views_admin.transactions, name='transactions'),
    path('finances/deposits/', views_admin.deposits, name='deposits'),
    path('finances/withdrawals/', views_admin.withdrawals, name='withdrawals'),
    
    # Trading Platform Control
    path('trading/', views_admin.trading_control, name='trading_control'),
    path('trading/instruments/', views_admin.trading_instruments, name='instruments'),
    path('trading/settings/', views_admin.trading_settings, name='trading_settings'),
    
    # Security Management
    path('security/', views_admin.security_management, name='security'),
    path('security/kyc/', views_admin.kyc_verification, name='kyc'),
    path('security/2fa/', views_admin.two_factor_auth, name='2fa'),
    
    # Compliance and Regulatory
    path('compliance/', views_admin.compliance, name='compliance'),
    path('compliance/reports/', views_admin.compliance_reports, name='compliance_reports'),
    
    # Customer Support
    path('support/', views_admin.support_dashboard, name='support'),
    path('support/tickets/', views_admin.support_tickets, name='tickets'),
    
    # Marketing and Promotions
    path('marketing/', views_admin.marketing, name='marketing'),
    path('marketing/campaigns/', views_admin.campaigns, name='campaigns'),
    path('marketing/referrals/', views_admin.referrals, name='referrals'),
    
    # Technical Configuration
    path('settings/', views_admin.system_settings, name='settings'),
    path('settings/notifications/', views_admin.notification_settings, name='notifications'),
    path('settings/api/', views_admin.api_settings, name='api_settings'),
    
    # Reporting and Analytics
    path('reports/', views_admin.reports, name='reports'),
    path('reports/trading/', views_admin.trading_reports, name='trading_reports'),
    path('reports/financial/', views_admin.financial_reports, name='financial_reports'),
    
    # Content Management
    path('content/', views_admin.content_management, name='content'),
    path('content/pages/', views_admin.page_management, name='pages'),
    path('content/resources/', views_admin.resource_management, name='resources'),
]
