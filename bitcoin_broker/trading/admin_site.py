from django.contrib.admin import AdminSite
from django.urls import path
from .views.admin_views import admin_dashboard

class NexusBrokerAdminSite(AdminSite):
    site_header = 'Nexus Broker Administration'
    site_title = 'Nexus Broker Admin'
    index_title = 'Administration Dashboard'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('dashboard/', self.admin_view(admin_dashboard), name='admin_dashboard'),
        ]
        return custom_urls + urls

admin_site = NexusBrokerAdminSite(name='nexus_admin')
