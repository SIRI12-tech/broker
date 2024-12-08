import uuid
import braintree
from decimal import Decimal
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone

from ..models import Order, Payment, UserProfile
from ..utils.crypto import generate_crypto_address

# Initialize Braintree
gateway = braintree.BraintreeGateway(
    braintree.Configuration(
        environment=getattr(braintree.Environment, settings.BRAINTREE_ENVIRONMENT.capitalize()),
        merchant_id=settings.BRAINTREE_MERCHANT_ID,
        public_key=settings.BRAINTREE_PUBLIC_KEY,
        private_key=settings.BRAINTREE_PRIVATE_KEY
    )
)

@login_required
def order_confirmation(request):
    """Handle order confirmation and payment method selection."""
    if request.method == 'POST':
        order_id = request.session.get('current_order_id')
        order = get_object_or_404(Order, id=order_id, user=request.user.userprofile)
        
        # Calculate total amount including fees
        total_amount = order.calculate_total_amount()
        order.save()
        
        # Generate client token for Braintree
        client_token = gateway.client_token.generate()
        
        context = {
            'order': order,
            'trading_fee': order.trading_fee,
            'network_fee': order.network_fee,
            'total_amount': total_amount,
            'client_token': client_token,
        }
        return render(request, 'trading/order_confirmation.html', context)
    
    return redirect('trading:order_entry')

@login_required
def process_payment(request):
    """Process payment based on selected payment method."""
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        order_id = request.session.get('current_order_id')
        order = get_object_or_404(Order, id=order_id, user=request.user.userprofile)
        
        if payment_method == 'card':
            return process_card_payment(request, order)
        elif payment_method == 'crypto':
            return process_crypto_payment(request, order)
        else:
            messages.error(request, 'Invalid payment method selected.')
            return redirect('trading:order_confirmation')
    
    return redirect('trading:order_entry')

@login_required
def process_card_payment(request, order):
    """Process credit/debit card payment using Braintree."""
    try:
        nonce = request.POST.get('payment_method_nonce')
        if not nonce:
            return JsonResponse({'error': 'Payment method nonce is required'}, status=400)
        
        # Create transaction
        result = gateway.transaction.sale({
            'amount': str(order.calculate_total_amount()),
            'payment_method_nonce': nonce,
            'options': {
                'submit_for_settlement': True
            },
            'custom_fields': {
                'order_id': str(order.id)
            }
        })
        
        if result.is_success:
            # Create payment record
            payment = Payment.objects.create(
                order=order,
                payment_method='card',
                amount=order.calculate_total_amount(),
                status='completed',
                transaction_id=result.transaction.id,
                completed_at=timezone.now()
            )
            
            # Update order status
            order.status = 'paid'
            order.save()
            
            return JsonResponse({
                'status': 'success',
                'payment_id': payment.id,
                'transaction_id': result.transaction.id
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': result.message
            }, status=400)
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def process_crypto_payment(request, order):
    """Process cryptocurrency payment."""
    try:
        # Generate crypto payment address
        payment_address = generate_crypto_address(order.cryptocurrency)
        
        # Create payment record
        payment = Payment.objects.create(
            order=order,
            payment_method='crypto',
            amount=order.calculate_total_amount(),
            status='pending',
            crypto_address=payment_address
        )
        
        return JsonResponse({
            'payment_address': payment_address,
            'payment_id': payment.id,
            'amount': str(order.calculate_total_amount()),
            'currency': order.cryptocurrency
        })
        
    except Exception as e:
        return JsonResponse({'error': 'Failed to generate payment address'}, status=500)

@csrf_exempt
@require_http_methods(['POST'])
def braintree_webhook(request):
    """Handle Braintree webhook notifications."""
    try:
        bt_signature = request.META.get('HTTP_BT_SIGNATURE')
        bt_payload = request.META.get('HTTP_BT_PAYLOAD')
        
        notification = gateway.webhook_notification.parse(bt_signature, bt_payload)
        
        if notification.kind == 'transaction_settled':
            # Find the payment by transaction ID
            transaction = notification.transaction
            try:
                payment = Payment.objects.get(transaction_id=transaction.id)
                payment.status = 'completed'
                payment.completed_at = timezone.now()
                payment.save()
                
                # Update order status
                order = payment.order
                order.status = 'paid'
                order.save()
                
            except Payment.DoesNotExist:
                return JsonResponse({'error': 'Payment not found'}, status=404)
                
        return JsonResponse({'status': 'success'})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def payment_success(request, payment_id):
    """Handle successful payment completion."""
    payment = get_object_or_404(Payment, id=payment_id, order__user=request.user.userprofile)
    
    if payment.status == 'completed':
        messages.success(request, 'Payment processed successfully!')
        return redirect('trading:order_detail', order_id=payment.order.id)
    
    messages.warning(request, 'Payment is still being processed.')
    return redirect('trading:order_confirmation')

@login_required
def payment_failed(request):
    """Handle failed payment."""
    messages.error(request, 'Payment failed. Please try again or choose a different payment method.')
    return redirect('trading:order_confirmation')
