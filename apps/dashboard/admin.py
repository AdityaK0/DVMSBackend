from django.contrib import admin
from .models import Event, CustomerMessage, Customer, ActivityLog


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['name', 'vendor', 'event_type', 'start_date', 'status', 'created_at']
    list_filter = ['status', 'event_type', 'created_at']
    search_fields = ['name', 'vendor__business_name']
    date_hierarchy = 'created_at'


@admin.register(CustomerMessage)
class CustomerMessageAdmin(admin.ModelAdmin):
    list_display = ['subject', 'vendor', 'message_type', 'recipient_count', 'sent_at']
    list_filter = ['message_type', 'sent_at']
    search_fields = ['subject', 'vendor__business_name']
    date_hierarchy = 'sent_at'


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'vendor', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'email', 'vendor__business_name']
    date_hierarchy = 'created_at'


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ['activity_type', 'vendor', 'description', 'created_at']
    list_filter = ['activity_type', 'created_at']
    search_fields = ['description', 'vendor__business_name']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at']