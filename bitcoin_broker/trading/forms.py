from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth import get_user_model
from .models import UserProfile, KYCDocument, Order, PriceAlert, Asset
from django.core.validators import MinValueValidator
from decimal import Decimal
import os
import random

class SignUpForm(UserCreationForm):
    email = forms.EmailField(
        max_length=254,
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-black',
            'placeholder': 'Enter your email address'
        })
    )
    phone_number = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-black',
            'placeholder': '+1234567890'
        })
    )
    accept_terms = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
        })
    )

    class Meta:
        model = get_user_model()
        fields = ('username', 'email', 'phone_number', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-black',
                'placeholder': 'Choose a username'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-black'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-black'
        })

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if get_user_model().objects.filter(email=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email

class KYCDocumentForm(forms.ModelForm):
    class Meta:
        model = KYCDocument
        fields = ('document_type', 'document_number', 'document_file')
        widgets = {
            'document_type': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-black',
                'placeholder': 'Select document type'
            }),
            'document_number': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-black',
                'placeholder': 'Enter document number'
            }),
            'document_file': forms.FileInput(attrs={
                'class': 'mt-1 block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 focus:outline-none',
                'accept': 'image/jpeg,image/png,application/pdf'
            })
        }

    def clean_document_file(self):
        file = self.cleaned_data.get('document_file')
        if file:
            # Check file size (5MB limit)
            if file.size > 5 * 1024 * 1024:
                raise forms.ValidationError('File size must be under 5MB')
            
            # Check file type
            allowed_types = ['image/jpeg', 'image/png', 'application/pdf']
            if file.content_type not in allowed_types:
                raise forms.ValidationError('Only JPEG, PNG, and PDF files are allowed')
            
            # Check file extension
            allowed_extensions = ['.jpg', '.jpeg', '.png', '.pdf']
            ext = os.path.splitext(file.name)[1].lower()
            if ext not in allowed_extensions:
                raise forms.ValidationError('Invalid file extension')
        return file

    def clean_document_number(self):
        document_number = self.cleaned_data.get('document_number')
        if len(document_number) < 5:
            raise forms.ValidationError('Document number must be at least 5 characters long')
        return document_number

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['crypto_asset', 'amount', 'order_type']
        widgets = {
            'crypto_asset': forms.Select(choices=[
                ('BTC', 'Bitcoin (BTC)'),
                ('ETH', 'Ethereum (ETH)'),
                ('USDT', 'Tether (USDT)')
            ]),
            'amount': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'order_type': forms.Select(choices=Order.ORDER_TYPES)
        }

class PriceAlertForm(forms.ModelForm):
    class Meta:
        model = PriceAlert
        fields = ('asset', 'alert_type', 'price_target')
        widgets = {
            'price_target': forms.NumberInput(attrs={'step': '0.00000001'}),
        }

class TwoFactorSetupForm(forms.Form):
    code = forms.CharField(max_length=6, min_length=6, required=True)
    backup_phone = forms.CharField(max_length=20, required=False)

class UserSettingsForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['phone_number', 'date_of_birth', 'address']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }
    notification_email = forms.BooleanField(required=False)
    notification_sms = forms.BooleanField(required=False)
    notification_browser = forms.BooleanField(required=False)
    trading_default_size = forms.DecimalField(max_digits=10, decimal_places=2, required=False)
    ui_theme = forms.ChoiceField(choices=[('light', 'Light'), ('dark', 'Dark')], required=False)
    chart_interval = forms.ChoiceField(
        choices=[
            ('1m', '1 Minute'),
            ('5m', '5 Minutes'),
            ('15m', '15 Minutes'),
            ('1h', '1 Hour'),
            ('4h', '4 Hours'),
            ('1d', '1 Day')
        ],
        required=False
    )

class APIKeyForm(forms.Form):
    name = forms.CharField(max_length=100)
    permissions = forms.MultipleChoiceField(
        choices=[
            ('read', 'Read Data'),
            ('trade', 'Execute Trades'),
            ('withdraw', 'Withdraw Funds')
        ],
        widget=forms.CheckboxSelectMultiple
    )

class WithdrawalForm(forms.Form):
    """Form for cryptocurrency withdrawals."""
    amount = forms.DecimalField(
        max_digits=18,
        decimal_places=8,
        min_value=0.00000001,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    address = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter destination wallet address'
        })
    )
    currency = forms.ChoiceField(
        choices=[
            ('BTC', 'Bitcoin'),
            ('ETH', 'Ethereum'),
            ('USDT', 'Tether'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    def clean_address(self):
        """Validate the wallet address format."""
        address = self.cleaned_data['address']
        # Add your address validation logic here
        # Example: check if it's a valid Bitcoin or Ethereum address
        return address

class TradingBotForm(forms.Form):
    name = forms.CharField(max_length=100)
    strategy = forms.ChoiceField(choices=[
        ('trend_following', 'Trend Following'),
        ('mean_reversion', 'Mean Reversion'),
        ('arbitrage', 'Arbitrage')
    ])
    assets = forms.MultipleChoiceField(choices=[])  # Will be populated dynamically
    max_position_size = forms.DecimalField(max_digits=10, decimal_places=2)
    stop_loss_percentage = forms.DecimalField(max_digits=5, decimal_places=2)
    take_profit_percentage = forms.DecimalField(max_digits=5, decimal_places=2)
    is_active = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate assets choices from database
        self.fields['assets'].choices = [
            (asset.id, f"{asset.name} ({asset.symbol})")
            for asset in Asset.objects.all()
        ]

class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'mt-1 block w-full bg-gray-800/70 border border-gray-700 text-white rounded-lg focus:ring-bitcoin focus:border-bitcoin p-3 placeholder-gray-400',
        'placeholder': 'Enter your username or email'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'mt-1 block w-full bg-gray-800/70 border border-gray-700 text-white rounded-lg focus:ring-bitcoin focus:border-bitcoin p-3 placeholder-gray-400',
        'placeholder': 'Enter your password'
    }))
