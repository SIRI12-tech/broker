from django.contrib.auth import login, authenticate
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from .forms import SignUpForm, KYCDocumentForm, TwoFactorSetupForm
from .models import UserProfile, KYCDocument, VerificationCode
import pyotp
import qrcode
import base64
from io import BytesIO
import random
import string
import requests

def generate_verification_code():
    return ''.join(random.choices(string.digits, k=6))

def send_verification_email(user, code):
    subject = 'Verify your Nexus Broker account'
    html_message = render_to_string('registration/verification_email.html', {
        'user': user,
        'code': code
    })
    plain_message = strip_tags(html_message)
    
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=html_message
    )

def send_sms_verification(phone_number, code):
    # Implement your preferred SMS service here
    # Example using Twilio:
    try:
        response = requests.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Messages.json",
            auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
            data={
                'From': settings.TWILIO_PHONE_NUMBER,
                'To': phone_number,
                'Body': f'Your Nexus Broker verification code is: {code}'
            }
        )
        return response.status_code == 200
    except Exception as e:
        print(f"SMS sending failed: {str(e)}")
        return False

def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Create user profile
            profile = UserProfile.objects.create(
                user=user,
                phone_number=form.cleaned_data.get('phone_number')
            )
            
            # Generate and send email verification code
            email_code = generate_verification_code()
            VerificationCode.objects.create(
                user=user,
                code=email_code,
                code_type='email',
                expires_at=timezone.now() + timezone.timedelta(minutes=30)
            )
            send_verification_email(user, email_code)
            
            # Generate and send SMS verification code
            sms_code = generate_verification_code()
            VerificationCode.objects.create(
                user=user,
                code=sms_code,
                code_type='phone',
                expires_at=timezone.now() + timezone.timedelta(minutes=30)
            )
            send_sms_verification(profile.phone_number, sms_code)
            
            # Log the user in
            login(request, user)
            
            return redirect('trading:verify_email')
    else:
        form = SignUpForm()
    return render(request, 'registration/signup.html', {'form': form})

@login_required
def verify_email(request):
    if request.method == 'POST':
        code = request.POST.get('code')
        verification = VerificationCode.objects.filter(
            user=request.user,
            code=code,
            code_type='email',
            is_used=False
        ).first()
        
        if verification and verification.is_valid():
            profile = request.user.userprofile
            profile.is_email_verified = True
            profile.save()
            
            verification.is_used = True
            verification.save()
            
            return redirect('trading:verify_phone')
        
    return render(request, 'registration/verify_email.html')

@login_required
def verify_phone(request):
    if request.method == 'POST':
        code = request.POST.get('code')
        verification = VerificationCode.objects.filter(
            user=request.user,
            code=code,
            code_type='phone',
            is_used=False
        ).first()
        
        if verification and verification.is_valid():
            profile = request.user.userprofile
            profile.is_phone_verified = True
            profile.save()
            
            verification.is_used = True
            verification.save()
            
            return redirect('trading:setup_2fa')
        
    return render(request, 'registration/verify_phone.html')

@login_required
def setup_2fa(request):
    if request.method == 'POST':
        form = TwoFactorSetupForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data.get('code')
            totp = pyotp.TOTP(request.session['temp_secret'])
            
            if totp.verify(code):
                profile = request.user.userprofile
                profile.two_factor_enabled = True
                profile.two_factor_secret = request.session['temp_secret']
                if form.cleaned_data.get('backup_phone'):
                    profile.backup_phone = form.cleaned_data.get('backup_phone')
                profile.save()
                
                del request.session['temp_secret']
                return redirect('trading:dashboard')
    else:
        # Generate new TOTP secret
        secret = pyotp.random_base32()
        request.session['temp_secret'] = secret
        
        # Generate QR code
        totp = pyotp.TOTP(secret)
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp.provisioning_uri(
            request.user.email,
            issuer_name="Nexus Broker"
        ))
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        qr_code = base64.b64encode(buffer.getvalue()).decode()
        
        form = TwoFactorSetupForm()
        return render(request, 'registration/setup_2fa.html', {
            'form': form,
            'qr_code': qr_code,
            'secret': secret
        })

@login_required
def kyc_upload(request):
    if request.method == 'POST':
        form = KYCDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.user = request.user.userprofile
            document.save()
            
            # Update user profile verification status
            profile = request.user.userprofile
            profile.verification_status = 'pending'
            profile.save()
            
            return redirect('trading:dashboard')
    else:
        form = KYCDocumentForm()
    
    return render(request, 'registration/kyc_upload.html', {'form': form})

def verify_login(request):
    if request.method == 'POST':
        code = request.POST.get('code')
        user_id = request.session.get('temp_user_id')
        
        if user_id:
            user = User.objects.get(id=user_id)
            totp = pyotp.TOTP(user.userprofile.two_factor_secret)
            
            if totp.verify(code):
                login(request, user)
                del request.session['temp_user_id']
                return redirect('trading:dashboard')
    
    return render(request, 'registration/verify_login.html')
