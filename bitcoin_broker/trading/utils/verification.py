import random
import string
import requests
from django.core.mail import send_mail
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from ..models import UserProfile, KYCDocument

def generate_verification_code(length=6):
    """Generate a random verification code"""
    return ''.join(random.choices(string.digits, k=length))

def store_verification_code(user_id, code_type, code, expiry=300):
    """Store verification code in cache with expiry time (default 5 minutes)"""
    if not user_id or not code_type or not code:
        return False
        
    cache_key = f"{code_type}_{user_id}"
    
    # Delete any existing code first
    cache.delete(cache_key)
    
    # Store new code
    cache.set(cache_key, code, expiry)
    return True

def verify_code(user_id, code_type, submitted_code):
    """Verify the submitted code against stored code"""
    if not submitted_code:
        return False
        
    cache_key = f"{code_type}_{user_id}"
    stored_code = cache.get(cache_key)
    
    if not stored_code:
        return False
    
    # Case-insensitive comparison and strip whitespace
    submitted_code = submitted_code.strip()
    stored_code = stored_code.strip()
    
    if stored_code.lower() == submitted_code.lower():
        cache.delete(cache_key)  # Delete code after successful verification
        return True
    return False

def send_email_verification(user_email, code):
    """Send verification code via email"""
    subject = 'Nexus Broker - Email Verification Code'
    message = f'''Welcome to Nexus Broker!
    
Your verification code is: {code}

This code will expire in 5 minutes.
Please do not share this code with anyone.

Best regards,
The Nexus Broker Team'''
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user_email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False

def send_sms_verification(phone_number, code):
    """Send verification code via SMS using Termii"""
    url = "https://api.ng.termii.com/api/sms/send"
    
    payload = {
        "to": phone_number,
        "from": settings.TERMII_SENDER_ID,
        "sms": f"Your Nexus Broker verification code is: {code}",
        "type": "plain",
        "channel": "generic",
        "api_key": settings.TERMII_API_KEY,
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Error sending SMS: {str(e)}")
        return False

def verify_kyc_document(document_id, verified=True, rejection_reason=None):
    """
    Verify or reject a KYC document and update user profile status.
    
    Args:
        document_id (int): ID of the KYCDocument to verify
        verified (bool): Whether to verify or reject the document
        rejection_reason (str, optional): Reason for rejection if verified is False
    
    Returns:
        bool: True if verification was successful, False otherwise
    """
    try:
        document = KYCDocument.objects.select_related('user__userprofile').get(id=document_id)
        
        if verified:
            document.status = 'verified'
            document.verified_at = timezone.now()
            document.rejection_reason = None
            
            # Update user profile status
            profile = document.user.userprofile
            profile.kyc_status = 'verified'
            profile.save()
            
            # Send verification success email
            context = {
                'user': document.user,
                'document_type': document.get_document_type_display(),
                'verified_at': document.verified_at
            }
            html_message = render_to_string('emails/kyc_verified.html', context)
            plain_message = strip_tags(html_message)
            
            send_mail(
                'KYC Verification Successful',
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [document.user.email],
                html_message=html_message,
                fail_silently=True
            )
        else:
            document.status = 'rejected'
            document.rejection_reason = rejection_reason
            
            # Update user profile status if all documents are rejected
            profile = document.user.userprofile
            if not KYCDocument.objects.filter(user=document.user, status='verified').exists():
                profile.kyc_status = 'rejected'
                profile.save()
            
            # Send rejection email
            context = {
                'user': document.user,
                'document_type': document.get_document_type_display(),
                'rejection_reason': rejection_reason
            }
            html_message = render_to_string('emails/kyc_rejected.html', context)
            plain_message = strip_tags(html_message)
            
            send_mail(
                'KYC Verification Update',
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [document.user.email],
                html_message=html_message,
                fail_silently=True
            )
        
        document.save()
        return True
        
    except KYCDocument.DoesNotExist:
        return False
    except Exception as e:
        # Log the error
        print(f"Error verifying KYC document {document_id}: {str(e)}")
        return False

def get_user_verification_status(user_id):
    """
    Get detailed verification status for a user.
    
    Args:
        user_id (int): ID of the user to check
    
    Returns:
        dict: Dictionary containing verification status details
    """
    try:
        profile = UserProfile.objects.get(user_id=user_id)
        documents = KYCDocument.objects.filter(user_id=user_id)
        
        return {
            'kyc_status': profile.kyc_status,
            'total_documents': documents.count(),
            'verified_documents': documents.filter(status='verified').count(),
            'pending_documents': documents.filter(status='pending').count(),
            'rejected_documents': documents.filter(status='rejected').count(),
            'latest_submission': documents.order_by('-uploaded_at').first(),
            'latest_verification': documents.filter(status='verified').order_by('-verified_at').first()
        }
    except UserProfile.DoesNotExist:
        return None
    except Exception as e:
        # Log the error
        print(f"Error getting verification status for user {user_id}: {str(e)}")
        return None
