"""
Trading app views package.
"""

import json
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm, SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail, BadHeaderError
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.db.models.query_utils import Q
from django.conf import settings
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ..models import UserProfile, Order, PriceAlert, Transaction, VerificationCode, KYCDocument, Portfolio, Account, RiskMetrics, PortfolioSnapshot, Trade, Asset
from ..forms import SignUpForm, LoginForm, KYCDocumentForm
from ..utils.verification import (
    generate_verification_code,
    store_verification_code,
    verify_code,
    send_email_verification,
    send_sms_verification
)
import random
import logging
import requests
from decimal import Decimal
from django.core.cache import cache

# Set up logging
logger = logging.getLogger(__name__)

def index(request):
    """Landing page view"""
    try:
        # Return the landing page
        return render(request, 'index.html', {})
    except Exception as e:
        logger.error(f"Error in index view: {str(e)}")
        # Return empty prices if there's an error
        return render(request, 'index.html', {})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('trading:dashboard')
    
    if request.method == 'POST':
        form = LoginForm(request=request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.username}!')
                return redirect('trading:dashboard')
            else:
                messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()
    
    return render(request, 'trading/login.html', {'form': form})

def logout_view(request):
    """Handle user logout"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('trading:login')

@login_required
def dashboard(request):
    # Get or create user profile
    user_profile, created = UserProfile.objects.get_or_create(
        user=request.user,
        defaults={
            'verification_status': 'unverified',
            'kyc_status': 'not_submitted',
        }
    )
    
    # Get or create portfolio
    portfolio, created = Portfolio.objects.get_or_create(
        user=user_profile,
        defaults={
            'total_value': 0,
            'total_profit_loss': 0,
        }
    )
    
    # Get or create account
    account, created = Account.objects.get_or_create(
        user=request.user,
        defaults={
            'balance': 0,
            'margin_used': 0,
            'available_margin': 0,
            'portfolio_value': 0,
            'account_status': 'active'
        }
    )
    
    # Get risk metrics
    risk_metrics = RiskMetrics.objects.filter(portfolio=portfolio).first()
    if not risk_metrics:
        risk_metrics = {'volatility': None, 'sharpe_ratio': None}
    
    # Get recent transactions
    recent_transactions = Transaction.objects.filter(user=user_profile).order_by('-created_at')[:5]
    
    # Update account values
    account.update_portfolio_value()
    account.calculate_available_margin()
    
    context = {
        'portfolio': portfolio,
        'account': account,
        'risk_metrics': risk_metrics,
        'recent_transactions': recent_transactions,
        'portfolio_history': json.dumps(get_portfolio_history(portfolio))
    }
    
    return render(request, 'trading/dashboard.html', context)

@login_required
def trading(request):
    """Trading dashboard view"""
    # Get user's active trades
    active_trades = Trade.objects.filter(
        user=request.user,
        status__in=['open', 'pending']
    ).select_related('asset').order_by('-created_at')
    
    # Get user's trade history
    trade_history = Trade.objects.filter(
        user=request.user,
        status__in=['closed', 'cancelled']
    ).select_related('asset').order_by('-closed_at')[:50]  # Last 50 trades
    
    # Get available assets
    assets = Asset.objects.filter(is_active=True).order_by('symbol')
    
    # Calculate total P/L
    total_pl = sum(trade.profit_loss for trade in active_trades)
    total_pl_percentage = sum(trade.profit_loss_percentage for trade in active_trades) / len(active_trades) if active_trades else 0
    
    context = {
        'active_trades': active_trades,
        'trade_history': trade_history,
        'assets': assets,
        'total_pl': total_pl,
        'total_pl_percentage': total_pl_percentage
    }
    
    return render(request, 'trading/trading.html', context)

def signup(request):
    """Handle user signup with verification"""
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Generate and send verification code
            code = generate_verification_code()
            store_verification_code(user.id, 'email', code)
            if send_email_verification(user.email, code):
                messages.success(request, 'Verification code sent to your email.')
                return redirect('trading:verify_email', user_id=user.id)
            else:
                messages.error(request, 'Failed to send verification code. Please try again.')
    else:
        form = SignUpForm()
    
    return render(request, 'registration/signup.html', {'form': form})

def verify_email(request, user_id):
    """Handle email verification"""
    if request.method == 'POST':
        submitted_code = request.POST.get('code')
        if verify_code(user_id, 'email', submitted_code):
            user = User.objects.get(id=user_id)
            user.is_email_verified = True
            user.save()
            messages.success(request, 'Email verified successfully!')
            return redirect('trading:login')
        else:
            messages.error(request, 'Invalid or expired verification code.')
    
    return render(request, 'trading/verify_email.html', {'user_id': user_id})

def verify_phone(request):
    """Handle phone verification"""
    if not request.user.is_authenticated:
        return redirect('trading:login')
    
    if request.method == 'POST':
        submitted_code = request.POST.get('code')
        if verify_code(request.user.id, 'phone', submitted_code):
            request.user.is_phone_verified = True
            request.user.save()
            messages.success(request, 'Phone number verified successfully!')
            return redirect('trading:dashboard')
        else:
            messages.error(request, 'Invalid or expired verification code.')
    
    return render(request, 'trading/verify_phone.html')

def setup_2fa(request):
    """Handle 2FA setup"""
    if not request.user.is_authenticated:
        return redirect('trading:login')
    
    if request.method == 'POST':
        phone_number = request.POST.get('phone_number')
        if phone_number:
            # Save phone number
            request.user.phone_number = phone_number
            request.user.save()
            
            # Send verification code
            code = generate_verification_code()
            store_verification_code(request.user.id, 'phone', code)
            if send_sms_verification(phone_number, code):
                messages.success(request, 'Verification code sent to your phone.')
                return redirect('trading:verify_phone')
            else:
                messages.error(request, 'Failed to send verification code. Please try again.')
    
    return render(request, 'trading/setup_2fa.html')

def about(request):
    """About page view"""
    return render(request, 'pages/about.html')

def contact(request):
    """Contact page view"""
    return render(request, 'pages/contact.html')

def terms(request):
    """Terms of service view"""
    return render(request, 'pages/terms.html')

def privacy(request):
    """Privacy policy view"""
    return render(request, 'pages/privacy.html')

def faq(request):
    """FAQ page view"""
    return render(request, 'pages/faq.html')

@login_required
def place_order(request):
    """Handle order placement"""
    if request.method == 'POST':
        # Get order details from request
        order_type = request.POST.get('type')
        amount = request.POST.get('amount')
        symbol = request.POST.get('symbol')
        
        try:
            # Create and execute order
            order = Order.objects.create(
                user=request.user,
                type=order_type,
                amount=amount,
                symbol=symbol,
                status='pending'
            )
            execute_order(order)
            return JsonResponse({'status': 'success'})
        except Exception as e:
            logger.error(f"Error placing order: {str(e)}")
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@login_required
def set_price_alert(request):
    """Handle price alert creation"""
    if request.method == 'POST':
        symbol = request.POST.get('symbol')
        price = request.POST.get('price')
        condition = request.POST.get('condition')
        
        try:
            alert = PriceAlert.objects.create(
                user=request.user,
                symbol=symbol,
                price=price,
                condition=condition
            )
            return JsonResponse({'status': 'success'})
        except Exception as e:
            logger.error(f"Error setting price alert: {str(e)}")
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@require_http_methods(["GET"])
def get_crypto_prices(request):
    """
    Fetch current cryptocurrency prices from CoinGecko API
    Returns prices for BTC, ETH, and other major cryptocurrencies
    """
    # Try to get cached data first
    cached_prices = cache.get('crypto_prices')
    if cached_prices:
        return JsonResponse(cached_prices)

    # List of cryptocurrencies to fetch
    crypto_ids = [
        'bitcoin',
        'ethereum',
        'binancecoin',
        'ripple',
        'cardano',
        'solana',
        'polkadot',
        'dogecoin'
    ]
    
    try:
        # CoinGecko API endpoint
        url = 'https://api.coingecko.com/api/v3/simple/price'
        params = {
            'ids': ','.join(crypto_ids),
            'vs_currencies': 'usd',
            'include_24hr_change': 'true',
            'include_market_cap': 'true',
            'include_last_updated_at': 'true'
        }
        
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        
        # Format the response data
        formatted_data = {}
        for crypto_id, details in data.items():
            formatted_data[crypto_id] = {
                'price': details['usd'],
                'change_24h': details.get('usd_24h_change', 0),
                'market_cap': details.get('usd_market_cap', 0),
                'last_updated': details.get('last_updated_at', None)
            }
        
        # Cache the results for 5 minutes
        cache.set('crypto_prices', formatted_data, 300)
        
        return JsonResponse(formatted_data)
        
    except requests.RequestException as e:
        return JsonResponse({
            'error': 'Failed to fetch cryptocurrency prices',
            'details': str(e)
        }, status=503)
    except Exception as e:
        return JsonResponse({
            'error': 'An unexpected error occurred',
            'details': str(e)
        }, status=500)

@login_required
def kyc_status(request):
    """View for checking KYC verification status."""
    try:
        user_profile = request.user.userprofile
        documents = KYCDocument.objects.filter(user=request.user).order_by('-uploaded_at')
        
        context = {
            'verification_status': user_profile.kyc_status,
            'documents': documents,
            'can_upload': user_profile.kyc_status != 'verified',
            'profile': user_profile,
            'total_documents': documents.count(),
            'pending_documents': documents.filter(status='pending').count(),
            'verified_documents': documents.filter(status='verified').count(),
            'rejected_documents': documents.filter(status='rejected').count(),
        }
        
        return render(request, 'trading/kyc_status.html', context)
    except Exception as e:
        logger.error(f"Error in kyc_status view: {str(e)}")
        messages.error(request, 'An error occurred while checking KYC status.')
        return redirect('trading:dashboard')

@login_required
def kyc_upload(request):
    """Handle KYC document upload."""
    if request.method == 'POST':
        form = KYCDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Create KYC document but don't save to DB yet
                kyc_doc = form.save(commit=False)
                kyc_doc.user = request.user
                kyc_doc.status = 'pending'
                kyc_doc.save()
                
                # Update user profile KYC status
                user_profile = request.user.userprofile
                if user_profile.kyc_status == 'not_submitted':
                    user_profile.kyc_status = 'pending'
                    user_profile.save()
                
                messages.success(request, 'KYC document uploaded successfully. Our team will review it shortly.')
                return redirect('trading:kyc_status')
            except Exception as e:
                logger.error(f"Error in kyc_upload view: {str(e)}")
                messages.error(request, 'An error occurred while uploading your document.')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = KYCDocumentForm()
        return render(request, 'trading/kyc_upload.html', {'form': form})
    
    return redirect('trading:kyc_status')

def resend_verification(request, user_id):
    """Resend verification email to user."""
    try:
        user = User.objects.get(id=user_id)
        send_email_verification(user, 'signup')
        messages.success(request, 'Verification email has been resent.')
    except User.DoesNotExist:
        messages.error(request, 'User not found.')
    except Exception as e:
        logger.error(f"Error in resend_verification: {str(e)}")
        messages.error(request, 'Failed to resend verification email.')
    
    return redirect('trading:login')

def password_reset_request(request):
    """Handle password reset request"""
    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data['email']
            user = User.objects.filter(Q(email=data)).first()
            if user:
                subject = "Password Reset Requested"
                email_template_name = "trading/password_reset_email.html"
                c = {
                    "email": user.email,
                    'domain': request.META['HTTP_HOST'],
                    'site_name': 'Nexus Broker',
                    "uid": urlsafe_base64_encode(force_bytes(user.pk)),
                    "user": user,
                    'token': default_token_generator.make_token(user),
                    'protocol': 'https' if request.is_secure() else 'http',
                }
                email = render_to_string(email_template_name, c)
                try:
                    send_mail(subject, email, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
                except BadHeaderError:
                    messages.error(request, "Invalid header found.")
                    return redirect('trading:password_reset')
                messages.success(request, "Password reset instructions have been sent to your email.")
                return redirect('trading:password_reset_done')
            else:
                messages.error(request, "No user found with that email address.")
    else:
        form = PasswordResetForm()
    return render(request, 'trading/password_reset_form.html', {'form': form})

def password_reset_done(request):
    """Password reset done view"""
    return render(request, 'trading/password_reset_done.html')

def password_reset_confirm(request, uidb64, token):
    """Password reset confirmation view"""
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            form = SetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Your password has been set. You may go ahead and log in now.")
                return redirect('trading:login')
        else:
            form = SetPasswordForm(user)
        return render(request, 'trading/password_reset_confirm.html', {'form': form})
    else:
        messages.error(request, "The password reset link was invalid, possibly because it has already been used. Please request a new password reset.")
        return redirect('trading:password_reset')

def password_reset_complete(request):
    """Password reset complete view"""
    return render(request, 'trading/password_reset_complete.html')

def get_portfolio_history(portfolio):
    """
    Get historical portfolio value data for charting.
    Returns a list of portfolio snapshots with timestamp and value.
    """
    snapshots = PortfolioSnapshot.objects.filter(
        portfolio=portfolio
    ).order_by('timestamp')[:30]  # Last 30 snapshots
    
    history_data = []
    for snapshot in snapshots:
        history_data.append({
            'timestamp': snapshot.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'total_value': float(snapshot.total_value),
            'cash_balance': float(snapshot.cash_balance),
            'asset_value': float(snapshot.asset_value),
            'pnl_24h': float(snapshot.pnl_24h),
            'pnl_percentage_24h': float(snapshot.pnl_percentage_24h)
        })
    
    # If no snapshots exist, create initial data point
    if not history_data:
        current_time = timezone.now()
        history_data.append({
            'timestamp': current_time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_value': float(portfolio.total_value),
            'cash_balance': 0.0,
            'asset_value': float(portfolio.total_value),
            'pnl_24h': 0.0,
            'pnl_percentage_24h': 0.0
        })
        
        # Create initial snapshot
        PortfolioSnapshot.objects.create(
            portfolio=portfolio,
            timestamp=current_time,
            total_value=portfolio.total_value,
            cash_balance=0,
            asset_value=portfolio.total_value,
            pnl_24h=0,
            pnl_percentage_24h=0
        )
    
    return history_data
