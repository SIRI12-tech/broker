from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import UserProfile, Order, PriceAlert, Transaction, VerificationCode, KYCDocument, Portfolio
from .forms import SignUpForm, KYCDocumentForm
import random
import logging
import requests
import json
from decimal import Decimal

# Set up logging
logger = logging.getLogger(__name__)

def index(request):
    """Landing page view"""
    try:
        # Fetch initial crypto prices for landing page
        crypto_prices = get_multiple_crypto_prices()
        return render(request, 'index.html', {'crypto_prices': crypto_prices})
    except Exception as e:
        logger.error(f"Error in index view: {str(e)}")
        # Return empty prices if there's an error
        return render(request, 'index.html', {'crypto_prices': {}})

def login_view(request):
    """Handle user login with 2FA"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)
        
        if user is not None:
            # Check if user has 2FA enabled
            if user.userprofile.two_factor_enabled:
                # Generate and send verification code
                verification_method = 'email' if user.userprofile.is_email_verified else 'phone'
                if verification_method == 'email':
                    send_email_verification(user, 'login')
                else:
                    send_sms_verification(user, user.userprofile.phone_number)
                
                # Store user ID in session for verification
                request.session['auth_user_id'] = user.id
                request.session['verification_method'] = verification_method
                
                return redirect('trading:verify_login')
            else:
                # If 2FA is not enabled, log in directly
                login(request, user)
                messages.success(request, 'Login successful.')
                return redirect('trading:dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'registration/login.html')

def logout_view(request):
    """Handle user logout"""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('trading:index')

@login_required
def dashboard(request):
    """User dashboard view"""
    user_profile = UserProfile.objects.get_or_create(user=request.user)[0]
    
    # Get user's recent orders
    recent_orders = Order.objects.filter(user=request.user).order_by('-created_at')[:5]
    
    # Get user's active price alerts
    active_alerts = PriceAlert.objects.filter(user=request.user, status='active')
    
    # Get recent transactions
    recent_transactions = Transaction.objects.filter(user=request.user).order_by('-created_at')[:5]
    
    # Fetch current crypto prices
    crypto_prices = get_multiple_crypto_prices()
    
    context = {
        'user_profile': user_profile,
        'btc_balance': user_profile.btc_balance,
        'usd_balance': user_profile.usd_balance,
        'recent_orders': recent_orders,
        'active_alerts': active_alerts,
        'recent_transactions': recent_transactions,
        'crypto_prices': crypto_prices,
    }
    return render(request, 'trading/dashboard.html', context)

@login_required
def trading(request):
    """Trading dashboard view"""
    user_profile = UserProfile.objects.get_or_create(user=request.user)[0]
    crypto_prices = get_multiple_crypto_prices()
    context = {
        'btc_balance': user_profile.btc_balance,
        'usd_balance': user_profile.usd_balance,
        'crypto_prices': crypto_prices,
    }
    return render(request, 'trading/trading.html', context)

def signup(request):
    """User registration view"""
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  # User starts inactive until email verification
            user.save()
            
            # Create user profile
            profile = UserProfile.objects.create(
                user=user,
                phone_number=form.cleaned_data.get('phone_number')
            )
            
            # Send verification email
            send_email_verification(user, 'signup')
            
            messages.success(request, 'Please check your email to verify your account.')
            return redirect('trading:login')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = SignUpForm()
    
    return render(request, 'registration/signup.html', {'form': form})

def verify_email(request, user_id):
    """Email verification view"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        code = request.POST.get('verification_code')
        if verify_code(user, code, 'signup'):
            user.is_active = True
            user.save()
            user.userprofile.is_email_verified = True
            user.userprofile.save()
            
            # Create portfolio for the user
            Portfolio.objects.create(user=user.userprofile)
            
            messages.success(request, 'Email verified successfully. Please log in.')
            return redirect('trading:login')
        else:
            messages.error(request, 'Invalid or expired verification code.')
    
    return render(request, 'registration/verify_email.html', {'user': user})

def verify_login(request):
    """Verify 2FA code during login"""
    user_id = request.session.get('auth_user_id')
    verification_method = request.session.get('verification_method')
    
    if not user_id:
        return redirect('trading:login')
    
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        code = request.POST.get('verification_code')
        if verify_code(user, code, verification_method):
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            
            # Clean up session
            del request.session['auth_user_id']
            del request.session['verification_method']
            
            return redirect('trading:dashboard')
        else:
            messages.error(request, 'Invalid or expired verification code.')
    
    return render(request, 'registration/verify_login.html', {
        'user': user,
        'verification_method': verification_method
    })

@login_required
def verify_phone(request):
    """Phone number verification view"""
    if request.method == 'POST':
        code = request.POST.get('code')
        if verify_code(request.user, code, 'phone'):
            # Update user profile
            request.user.userprofile.phone_verified = True
            request.user.userprofile.save()
            
            messages.success(request, 'Phone number verified successfully!')
            return redirect('trading:dashboard')
        else:
            messages.error(request, 'Invalid or expired verification code.')
    
    return render(request, 'trading/verify_phone.html')

@login_required
def setup_2fa(request):
    """Setup two-factor authentication view"""
    if request.method == 'POST':
        method = request.POST.get('method')
        if method == 'phone':
            phone_number = request.POST.get('phone_number')
            if phone_number:
                request.user.userprofile.phone_number = phone_number
                request.user.userprofile.save()
                
                # Send verification code
                send_sms_verification(request.user, phone_number)
                return redirect('trading:verify_phone')
        elif method == 'email':
            email = request.POST.get('email')
            if email:
                request.user.email = email
                request.user.save()
                
                # Send verification code
                send_email_verification(request.user)
                return redirect('trading:verify_email', user_id=request.user.id)
        
        messages.error(request, 'Please provide a valid phone number or email.')
    
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
@require_http_methods(['POST'])
def place_order(request):
    """Handle order placement"""
    try:
        order_type = request.POST.get('order_type')
        side = request.POST.get('side')
        amount = Decimal(request.POST.get('amount'))
        price = Decimal(request.POST.get('price')) if request.POST.get('price') else None

        # Validate order parameters
        if amount <= 0:
            raise ValidationError('Amount must be greater than 0')
        if order_type == 'limit' and (not price or price <= 0):
            raise ValidationError('Invalid limit price')

        # Get current BTC price
        btc_price = get_current_btc_price()
        
        # Create order
        order = Order.objects.create(
            user=request.user,
            order_type=order_type,
            side=side,
            amount=amount,
            price=price if order_type == 'limit' else btc_price
        )

        # If market order, execute immediately
        if order_type == 'market':
            execute_order(order)

        return JsonResponse({'status': 'success', 'message': 'Order placed successfully'})
    except (ValueError, ValidationError) as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': 'An error occurred'}, status=500)

@login_required
@require_http_methods(['POST'])
def set_price_alert(request):
    """Handle price alert creation"""
    try:
        price = Decimal(request.POST.get('price'))
        condition = request.POST.get('condition')

        if price <= 0:
            raise ValidationError('Price must be greater than 0')

        PriceAlert.objects.create(
            user=request.user,
            price=price,
            condition=condition
        )

        return JsonResponse({'status': 'success', 'message': 'Price alert set successfully'})
    except (ValueError, ValidationError) as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': 'An error occurred'}, status=500)

def get_current_btc_price():
    """Fetch current BTC price from Binance API"""
    try:
        response = requests.get('https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT')
        data = response.json()
        return Decimal(data['price'])
    except Exception as e:
        raise Exception('Unable to fetch BTC price')

def get_multiple_crypto_prices():
    """Fetch prices for multiple cryptocurrencies"""
    try:
        # Using Binance API for real-time prices
        base_url = "https://api.binance.com/api/v3"
        symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT", "DOTUSDT"]
        prices = {}

        for symbol in symbols:
            # Get ticker data
            ticker_response = requests.get(f"{base_url}/ticker/24hr", params={"symbol": symbol})
            ticker_data = ticker_response.json()

            # Get recent trades
            trades_response = requests.get(f"{base_url}/trades", params={"symbol": symbol, "limit": 1})
            trade_data = trades_response.json()[0]

            if ticker_response.status_code == 200 and trades_response.status_code == 200:
                symbol_name = symbol.replace("USDT", "")
                prices[symbol_name] = {
                    "price": float(trade_data["price"]),
                    "change_24h": float(ticker_data["priceChangePercent"]),
                    "volume": float(ticker_data["volume"]) * float(ticker_data["weightedAvgPrice"]),
                    "high_24h": float(ticker_data["highPrice"]),
                    "low_24h": float(ticker_data["lowPrice"])
                }

        return prices
    except Exception as e:
        # Fallback to simulated data if API fails
        return {
            "BTC": {
                "price": 45000.00,
                "change_24h": 2.5,
                "volume": 1500000000,
                "high_24h": 46000.00,
                "low_24h": 44000.00
            },
            "ETH": {
                "price": 3200.00,
                "change_24h": 1.8,
                "volume": 800000000,
                "high_24h": 3300.00,
                "low_24h": 3100.00
            },
            "BNB": {
                "price": 420.00,
                "change_24h": 0.5,
                "volume": 200000000,
                "high_24h": 425.00,
                "low_24h": 415.00
            },
            "SOL": {
                "price": 98.50,
                "change_24h": 3.2,
                "volume": 150000000,
                "high_24h": 100.00,
                "low_24h": 95.00
            },
            "ADA": {
                "price": 0.55,
                "change_24h": 1.2,
                "volume": 100000000,
                "high_24h": 0.57,
                "low_24h": 0.53
            },
            "DOT": {
                "price": 7.80,
                "change_24h": -0.8,
                "volume": 80000000,
                "high_24h": 8.00,
                "low_24h": 7.60
            }
        }

def get_crypto_prices(request):
    # List of cryptocurrencies to fetch
    cryptos = ['bitcoin', 'ethereum', 'ripple', 'solana', 'cardano', 'polkadot', 'matic-network', 'chainlink', 'avalanche-2']
    
    try:
        # Fetch data from CoinGecko API
        response = requests.get(
            'https://api.coingecko.com/api/v3/simple/price',
            params={
                'ids': ','.join(cryptos),
                'vs_currencies': 'usd',
                'include_24hr_change': 'true',
                'include_24hr_vol': 'true'
            }
        )
        data = response.json()

        # Map CoinGecko IDs to ticker symbols
        id_to_symbol = {
            'bitcoin': 'BTC',
            'ethereum': 'ETH',
            'ripple': 'XRP',
            'solana': 'SOL',
            'cardano': 'ADA',
            'polkadot': 'DOT',
            'matic-network': 'MATIC',
            'chainlink': 'LINK',
            'avalanche-2': 'AVAX'
        }

        # Format response data
        formatted_data = {}
        for crypto_id, symbol in id_to_symbol.items():
            if crypto_id in data:
                crypto_data = data[crypto_id]
                formatted_data[symbol] = {
                    'price': crypto_data['usd'],
                    'price_change_24h': crypto_data.get('usd_24h_change', 0),
                    'volume_24h': crypto_data.get('usd_24h_vol', 0)
                }

        return JsonResponse(formatted_data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def execute_order(order):
    """Execute a market order"""
    try:
        user_profile = UserProfile.objects.get(user=order.user)
        btc_price = get_current_btc_price()
        
        if order.side == 'buy':
            usd_required = order.amount * btc_price
            if user_profile.usd_balance < usd_required:
                raise ValidationError('Insufficient USD balance')
            
            user_profile.usd_balance -= usd_required
            user_profile.btc_balance += order.amount
        else:  # sell
            if user_profile.btc_balance < order.amount:
                raise ValidationError('Insufficient BTC balance')
            
            user_profile.btc_balance -= order.amount
            user_profile.usd_balance += order.amount * btc_price

        user_profile.save()
        order.status = 'filled'
        order.save()

        # Create transaction record
        Transaction.objects.create(
            user=order.user,
            order=order,
            transaction_type='trade',
            amount_btc=order.amount,
            amount_usd=order.amount * btc_price
        )

    except Exception as e:
        order.status = 'cancelled'
        order.save()
        raise e

def send_email_verification(user, code_type='login'):
    """Generate a 6-digit verification code and send it via email"""
    code = generate_verification_code(user, code_type)
    
    # Send email
    subject = 'Verify Your Email - Nexus Broker'
    message = f'''
    Hello {user.username},
    
    Thank you for signing up with Nexus Broker. To verify your email address, please use the following code:
    
    {code}
    
    This code will expire in 10 minutes.
    
    If you did not request this verification code, please ignore this email.
    
    Best regards,
    Nexus Broker Team
    '''
    
    try:
        send_mail(
            subject,
            message,
            settings.EMAIL_HOST_USER,
            [user.email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False

def send_sms_verification(user, phone_number):
    """Generate a 6-digit verification code and send it via SMS"""
    code = generate_verification_code(user, 'login')
    
    # Send SMS
    # Implement SMS sending logic here

def generate_verification_code(user, code_type):
    """Generate a 6-digit verification code and save it to VerificationCode model"""
    code = ''.join(random.choices('0123456789', k=6))
    expiry = timezone.now() + timezone.timedelta(minutes=10)
    
    VerificationCode.objects.filter(user=user.userprofile, code_type=code_type, is_used=False).update(is_used=True)
    
    verification = VerificationCode.objects.create(
        user=user.userprofile,
        code=code,
        code_type=code_type,
        expires_at=expiry
    )
    return code

def verify_code(user, code, code_type):
    """Verify the provided code"""
    try:
        verification = VerificationCode.objects.get(
            user=user.userprofile,
            code=code,
            code_type=code_type,
            is_used=False,
            expires_at__gt=timezone.now()
        )
        verification.is_used = True
        verification.save()
        return True
    except VerificationCode.DoesNotExist:
        return False

def resend_verification(request, user_id):
    """Resend verification code for signup"""
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        send_email_verification(user, code_type='signup')
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=400)

def resend_login_verification(request):
    """Resend verification code for login"""
    if request.method == 'POST':
        user_id = request.session.get('auth_user_id')
        verification_method = request.session.get('verification_method')
        
        if not user_id:
            return JsonResponse({'success': False, 'error': 'No pending verification'}, status=400)
        
        user = get_object_or_404(User, id=user_id)
        
        if verification_method == 'phone':
            send_sms_verification(user, user.userprofile.phone_number)
        else:
            send_email_verification(user)
            
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=400)

def resend_email_code(request):
    if request.method == 'POST':
        if request.user.is_authenticated:
            # Generate new verification code
            code = generate_verification_code(request.user, 'email')
            VerificationCode.objects.create(
                user=request.user.userprofile,
                code=code,
                code_type='email',
                expires_at=timezone.now() + timezone.timedelta(minutes=30)
            )
            send_email_verification(request.user, code)
            return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=400)

def resend_phone_code(request):
    if request.method == 'POST':
        if request.user.is_authenticated:
            # Generate new verification code
            code = generate_verification_code(request.user, 'phone')
            VerificationCode.objects.create(
                user=request.user.userprofile,
                code=code,
                code_type='phone',
                expires_at=timezone.now() + timezone.timedelta(minutes=30)
            )
            send_sms_verification(request.user.userprofile.phone_number, code)
            return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=400)

def resend_login_code(request):
    if request.method == 'POST':
        user_id = request.session.get('temp_user_id')
        if user_id:
            user = User.objects.get(id=user_id)
            # Generate new verification code
            code = generate_verification_code(user, 'login')
            VerificationCode.objects.create(
                user=user.userprofile,
                code=code,
                code_type='login',
                expires_at=timezone.now() + timezone.timedelta(minutes=5)
            )
            # Send code via SMS or email based on user preference
            if user.userprofile.preferred_2fa_method == 'sms':
                send_sms_verification(user.userprofile.phone_number, code)
            else:
                send_email_verification(user, code)
            return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=400)

def kyc_status(request):
    if not request.user.is_authenticated:
        return redirect('trading:login')
    
    profile = request.user.userprofile
    documents = KYCDocument.objects.filter(user=profile)
    
    context = {
        'verification_status': profile.verification_status,
        'documents': documents,
    }
    return render(request, 'trading/kyc_status.html', context)

@login_required
def kyc_upload(request):
    """Handle KYC document upload"""
    if request.method == 'POST':
        document_type = request.POST.get('document_type')
        document = request.FILES.get('document')
        
        if document_type and document:
            # Create new KYC document
            kyc_doc = KYCDocument.objects.create(
                user=request.user,
                document_type=document_type,
                document=document,
                status='pending'
            )
            
            messages.success(request, 'Document uploaded successfully. Our team will review it shortly.')
            return redirect('trading:kyc_status')
        else:
            messages.error(request, 'Please provide both document type and file.')
    
    return render(request, 'trading/kyc_upload.html')
