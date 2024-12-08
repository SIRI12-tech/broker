from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils import timezone
from .models import (
    UserProfile, Portfolio, Asset, Position,
    Order, Transaction, PriceAlert, AIRecommendation,
    KYCDocument, Account, MarketDataFeed, Trade
)
from .utils.verification import verify_kyc_document
from django.db import models

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'verification_status', 'is_phone_verified', 'is_email_verified', 'kyc_status_display', 'created_at')
    list_filter = ('verification_status', 'is_phone_verified', 'is_email_verified')
    search_fields = ('user__username', 'user__email', 'phone_number')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'phone_number', 'date_of_birth', 'address')
        }),
        ('Verification Status', {
            'fields': ('verification_status', 'is_phone_verified', 'is_email_verified')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def kyc_status_display(self, obj):
        status_colors = {
            'not_submitted': 'gray',
            'pending': 'orange',
            'verified': 'green',
            'rejected': 'red'
        }
        color = status_colors.get(obj.kyc_status, 'black')
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            obj.get_kyc_status_display()
        )
    kyc_status_display.short_description = 'KYC Status'

@admin.register(KYCDocument)
class KYCDocumentAdmin(admin.ModelAdmin):
    list_display = ('user', 'document_type', 'status_colored', 'document_number', 'uploaded_at', 'verified_at', 'view_document')
    list_filter = ('status', 'document_type', 'uploaded_at')
    search_fields = ('user__username', 'user__email', 'document_number')
    readonly_fields = ('uploaded_at', 'verified_at')
    actions = ['verify_selected_documents', 'reject_selected_documents']

    fieldsets = (
        ('Document Information', {
            'fields': ('user', 'document_type', 'document_number', 'document_file')
        }),
        ('Verification Status', {
            'fields': ('status', 'rejection_reason', 'verified_at')
        }),
        ('Timestamps', {
            'fields': ('uploaded_at',),
            'classes': ('collapse',)
        }),
    )

    def status_colored(self, obj):
        colors = {
            'pending': 'orange',
            'verified': 'green',
            'rejected': 'red'
        }
        return format_html(
            '<span style="color: {};">{}</span>',
            colors.get(obj.status, 'black'),
            obj.get_status_display()
        )
    status_colored.short_description = 'Status'

    def view_document(self, obj):
        if obj.document_file:
            return format_html(
                '<a href="{}" target="_blank" class="button">View Document</a>',
                obj.document_file.url
            )
        return "No document"
    view_document.short_description = 'Document'

    def verify_selected_documents(self, request, queryset):
        success_count = 0
        for doc in queryset:
            if verify_kyc_document(doc.id, verified=True):
                success_count += 1

        self.message_user(
            request,
            f"{success_count} document(s) were successfully verified."
        )
    verify_selected_documents.short_description = "Verify selected documents"

    def reject_selected_documents(self, request, queryset):
        success_count = 0
        for doc in queryset:
            if verify_kyc_document(doc.id, verified=False, rejection_reason="Document does not meet requirements"):
                success_count += 1

        self.message_user(
            request,
            f"{success_count} document(s) were rejected."
        )
    reject_selected_documents.short_description = "Reject selected documents"

    class Media:
        css = {
            'all': ('admin/css/custom_admin.css',)
        }

    def save_model(self, request, obj, form, change):
        if 'status' in form.changed_data:
            if obj.status == 'verified':
                obj.verified_at = timezone.now()
                # Update user's KYC status
                user_profile = obj.user.userprofile
                user_profile.kyc_status = 'verified'
                user_profile.save()
        super().save_model(request, obj, form, change)

@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_value', 'total_profit_loss', 'last_updated')
    search_fields = ('user__username',)

@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'name', 'asset_type', 'is_active')
    list_filter = ('asset_type', 'is_active')
    search_fields = ('symbol', 'name')

@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ('portfolio', 'asset', 'quantity', 'average_buy_price', 'current_value')
    list_filter = ('asset',)
    search_fields = ('portfolio__user__username', 'asset__symbol')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('user', 'crypto_asset', 'order_type', 'amount', 'status', 'created_at')
    list_filter = ('order_type', 'status')
    search_fields = ('user__username', 'crypto_asset')

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'transaction_type', 'amount', 'status', 'created_at')
    list_filter = ('transaction_type', 'status')
    search_fields = ('user__username',)

@admin.register(PriceAlert)
class PriceAlertAdmin(admin.ModelAdmin):
    list_display = ('user', 'asset', 'alert_type', 'status', 'created_at')
    list_filter = ('alert_type', 'status')
    search_fields = ('user__username', 'asset__symbol')

@admin.register(AIRecommendation)
class AIRecommendationAdmin(admin.ModelAdmin):
    list_display = ('user', 'asset', 'recommendation_type', 'confidence_score', 'created_at')
    list_filter = ('recommendation_type',)
    search_fields = ('user__username', 'asset__symbol')

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'margin_used', 'available_margin', 'portfolio_value', 'account_status', 'created_at')
    list_filter = ('account_status', 'created_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at', 'available_margin')
    actions = ['activate_accounts', 'deactivate_accounts', 'suspend_accounts', 'reset_accounts']
    
    fieldsets = (
        ('Account Information', {
            'fields': ('user', 'balance', 'margin_used', 'available_margin', 'portfolio_value')
        }),
        ('Status', {
            'fields': ('account_status',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def activate_accounts(self, request, queryset):
        updated = queryset.update(account_status='active')
        self.message_user(request, f'{updated} accounts have been activated.')
    activate_accounts.short_description = "Activate selected accounts"

    def deactivate_accounts(self, request, queryset):
        updated = queryset.update(account_status='inactive')
        self.message_user(request, f'{updated} accounts have been deactivated.')
    deactivate_accounts.short_description = "Deactivate selected accounts"

    def suspend_accounts(self, request, queryset):
        updated = queryset.update(account_status='suspended')
        self.message_user(request, f'{updated} accounts have been suspended.')
    suspend_accounts.short_description = "Suspend selected accounts"

    def reset_accounts(self, request, queryset):
        updated = queryset.update(
            margin_used=0,
            available_margin=models.F('balance'),
            account_status='active'
        )
        self.message_user(request, f'{updated} accounts have been reset.')
    reset_accounts.short_description = "Reset selected accounts"

    def save_model(self, request, obj, form, change):
        if not change:  # New account
            obj.available_margin = obj.balance - obj.margin_used
        super().save_model(request, obj, form, change)

@admin.register(MarketDataFeed)
class MarketDataFeedAdmin(admin.ModelAdmin):
    list_display = ('asset_name', 'symbol', 'price', 'bid', 'ask', 'feed_status', 'data_source', 'last_updated')
    list_filter = ('feed_status', 'data_source', 'created_at')
    search_fields = ('asset_name', 'symbol')
    readonly_fields = ('created_at', 'last_updated')
    actions = ['activate_feeds', 'deactivate_feeds', 'approve_feeds', 'reject_feeds']
    
    fieldsets = (
        ('Asset Information', {
            'fields': ('asset_name', 'symbol')
        }),
        ('Price Data', {
            'fields': ('price', 'bid', 'ask', 'volume_24h', 'high_24h', 'low_24h')
        }),
        ('Feed Configuration', {
            'fields': ('data_source', 'feed_status', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'last_updated'),
            'classes': ('collapse',)
        }),
    )

    def activate_feeds(self, request, queryset):
        updated = queryset.update(feed_status='active')
        self.message_user(request, f'{updated} feeds have been activated.')
    activate_feeds.short_description = "Activate selected feeds"

    def deactivate_feeds(self, request, queryset):
        updated = queryset.update(feed_status='inactive')
        self.message_user(request, f'{updated} feeds have been deactivated.')
    deactivate_feeds.short_description = "Deactivate selected feeds"

    def approve_feeds(self, request, queryset):
        updated = queryset.update(feed_status='active')
        self.message_user(request, f'{updated} feeds have been approved.')
    approve_feeds.short_description = "Approve selected feeds"

    def reject_feeds(self, request, queryset):
        updated = queryset.update(feed_status='rejected')
        self.message_user(request, f'{updated} feeds have been rejected.')
    reject_feeds.short_description = "Reject selected feeds"

@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    list_display = ('user', 'asset', 'trade_type', 'side', 'status', 'quantity', 'entry_price', 'current_price', 'profit_loss', 'created_at')
    list_filter = ('status', 'trade_type', 'side', 'asset', ('user', admin.RelatedOnlyFieldListFilter))
    search_fields = ('user__username', 'asset__symbol')
    readonly_fields = ('profit_loss', 'profit_loss_percentage', 'created_at', 'opened_at', 'closed_at')
    
    fieldsets = (
        ('Trade Information', {
            'fields': ('user', 'asset', 'trade_type', 'side', 'status')
        }),
        ('Price Details', {
            'fields': ('entry_price', 'current_price', 'take_profit', 'stop_loss', 'trailing_stop')
        }),
        ('Performance', {
            'fields': ('quantity', 'profit_loss', 'profit_loss_percentage', 'fee')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'opened_at', 'closed_at')
        }),
    )
    
    actions = ['close_selected_trades', 'cancel_selected_trades', 'close_all_user_trades']
    
    def close_selected_trades(self, request, queryset):
        """Close selected trades at current market price"""
        closed_count = 0
        for trade in queryset.filter(status='open'):
            trade.close_trade()
            closed_count += 1
        
        self.message_user(request, f'{closed_count} trades have been closed.')
    close_selected_trades.short_description = 'Close selected trades at market price'
    
    def cancel_selected_trades(self, request, queryset):
        """Cancel selected pending trades"""
        updated = queryset.filter(status='pending').update(status='cancelled')
        self.message_user(request, f'{updated} trades have been cancelled.')
    cancel_selected_trades.short_description = 'Cancel selected pending trades'
    
    def close_all_user_trades(self, request, queryset):
        """Close all open trades for selected users"""
        users = set(trade.user for trade in queryset)
        closed_count = 0
        for user in users:
            user_trades = Trade.objects.filter(user=user, status='open')
            for trade in user_trades:
                trade.close_trade()
                closed_count += 1
        
        self.message_user(request, f'Closed {closed_count} trades for {len(users)} users.')
    close_all_user_trades.short_description = 'Close all trades for selected users'
