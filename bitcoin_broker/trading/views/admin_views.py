from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render
from django.contrib.auth.models import User
from django.db.models import Count
from ..models import UserProfile, KYCDocument

def is_staff(user):
    return user.is_staff

@user_passes_test(is_staff)
def admin_dashboard(request):
    """Admin dashboard view with KYC verification statistics."""
    # Get user statistics
    total_users = User.objects.count()
    verified_users = UserProfile.objects.filter(kyc_status='verified').count()
    pending_verifications = UserProfile.objects.filter(kyc_status='pending').count()
    
    # Get document statistics
    document_stats = KYCDocument.objects.values('status').annotate(count=Count('id'))
    rejected_documents = next((stat['count'] for stat in document_stats if stat['status'] == 'rejected'), 0)
    
    # Get recent documents
    recent_documents = KYCDocument.objects.select_related('user').order_by('-uploaded_at')[:5]
    
    context = {
        'total_users': total_users,
        'verified_users': verified_users,
        'pending_verifications': pending_verifications,
        'rejected_documents': rejected_documents,
        'recent_documents': recent_documents,
        'document_stats': {
            stat['status']: stat['count'] for stat in document_stats
        }
    }
    
    return render(request, 'admin/dashboard.html', context)
