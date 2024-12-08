from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import datetime, timedelta

from .models import UserProfile, Transaction, Order, PriceAlert

def is_admin(user):
    """Check if user is an admin"""
    return user.is_authenticated and user.is_staff

# Decorator for admin-only views
admin_required = user_passes_test(is_admin)

@login_required
@admin_required
def admin_dashboard(request):
    """Admin dashboard with overview of all metrics"""
    # Get key metrics
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    total_transactions = Transaction.objects.count()
    total_volume = Transaction.objects.aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Recent activity
    recent_users = User.objects.order_by('-date_joined')[:5]
    recent_transactions = Transaction.objects.order_by('-timestamp')[:5]
    
    context = {
        'total_users': total_users,
        'active_users': active_users,
        'total_transactions': total_transactions,
        'total_volume': total_volume,
        'recent_users': recent_users,
        'recent_transactions': recent_transactions,
    }
    return render(request, 'admin/dashboard.html', context)

@login_required
@admin_required
def user_management(request):
    """User management view"""
    users = User.objects.all().order_by('-date_joined')
    return render(request, 'admin/users.html', {'users': users})

@login_required
@admin_required
def create_user(request):
    """Create new user"""
    if request.method == 'POST':
        # Add user creation logic
        pass
    return render(request, 'admin/create_user.html')

@login_required
@admin_required
def edit_user(request, user_id):
    """Edit user details"""
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        # Add user edit logic
        pass
    return render(request, 'admin/edit_user.html', {'edit_user': user})

@login_required
@admin_required
def delete_user(request, user_id):
    """Delete user"""
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        user.delete()
        messages.success(request, 'User deleted successfully.')
        return redirect('admin:users')
    return render(request, 'admin/delete_user.html', {'delete_user': user})

@login_required
@admin_required
def verify_users(request):
    """Verify new user registrations"""
    unverified_users = UserProfile.objects.filter(is_verified=False)
    return render(request, 'admin/verify_users.html', {'unverified_users': unverified_users})

@login_required
@admin_required
def financial_operations(request):
    """Financial operations dashboard"""
    recent_transactions = Transaction.objects.order_by('-timestamp')[:10]
    total_volume = Transaction.objects.aggregate(Sum('amount'))['amount__sum'] or 0
    
    context = {
        'recent_transactions': recent_transactions,
        'total_volume': total_volume,
    }
    return render(request, 'admin/finances.html', context)

@login_required
@admin_required
def transactions(request):
    """View all transactions"""
    transactions = Transaction.objects.all().order_by('-timestamp')
    return render(request, 'admin/transactions.html', {'transactions': transactions})

@login_required
@admin_required
def deposits(request):
    """Manage deposits"""
    deposits = Transaction.objects.filter(transaction_type='deposit').order_by('-timestamp')
    return render(request, 'admin/deposits.html', {'deposits': deposits})

@login_required
@admin_required
def withdrawals(request):
    """Manage withdrawals"""
    withdrawals = Transaction.objects.filter(transaction_type='withdrawal').order_by('-timestamp')
    return render(request, 'admin/withdrawals.html', {'withdrawals': withdrawals})

@login_required
@admin_required
def trading_control(request):
    """Trading platform control panel"""
    return render(request, 'admin/trading_control.html')

@login_required
@admin_required
def trading_instruments(request):
    """Manage trading instruments"""
    return render(request, 'admin/trading_instruments.html')

@login_required
@admin_required
def trading_settings(request):
    """Configure trading settings"""
    return render(request, 'admin/trading_settings.html')

@login_required
@admin_required
def security_management(request):
    """Security management dashboard"""
    return render(request, 'admin/security.html')

@login_required
@admin_required
def kyc_verification(request):
    """KYC verification management"""
    return render(request, 'admin/kyc.html')

@login_required
@admin_required
def two_factor_auth(request):
    """2FA management"""
    return render(request, 'admin/2fa.html')

@login_required
@admin_required
def compliance(request):
    """Compliance dashboard"""
    return render(request, 'admin/compliance.html')

@login_required
@admin_required
def compliance_reports(request):
    """Generate compliance reports"""
    return render(request, 'admin/compliance_reports.html')

@login_required
@admin_required
def support_dashboard(request):
    """Support dashboard"""
    return render(request, 'admin/support_dashboard.html')

@login_required
@admin_required
def support_tickets(request):
    """Manage support tickets"""
    return render(request, 'admin/support_tickets.html')

@login_required
@admin_required
def marketing(request):
    """Marketing dashboard"""
    return render(request, 'admin/marketing.html')

@login_required
@admin_required
def campaigns(request):
    """Manage marketing campaigns"""
    return render(request, 'admin/campaigns.html')

@login_required
@admin_required
def referrals(request):
    """Manage referral program"""
    return render(request, 'admin/referrals.html')

@login_required
@admin_required
def system_settings(request):
    """System settings"""
    return render(request, 'admin/system_settings.html')

@login_required
@admin_required
def notification_settings(request):
    """Configure notifications"""
    return render(request, 'admin/notification_settings.html')

@login_required
@admin_required
def api_settings(request):
    """Manage API settings"""
    return render(request, 'admin/api_settings.html')

@login_required
@admin_required
def reports(request):
    """Reports dashboard"""
    return render(request, 'admin/reports.html')

@login_required
@admin_required
def trading_reports(request):
    """Trading reports"""
    return render(request, 'admin/trading_reports.html')

@login_required
@admin_required
def financial_reports(request):
    """Financial reports"""
    return render(request, 'admin/financial_reports.html')

@login_required
@admin_required
def content_management(request):
    """Content management dashboard"""
    return render(request, 'admin/content.html')

@login_required
@admin_required
def page_management(request):
    """Manage website pages"""
    return render(request, 'admin/pages.html')

@login_required
@admin_required
def resource_management(request):
    """Manage trading resources"""
    return render(request, 'admin/resources.html')
