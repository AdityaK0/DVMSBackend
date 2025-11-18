"""
Admin configuration for events app.
"""
from django.contrib import admin
from apps.events.models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'vendor', 'status', 'start_date', 'end_date', 'is_deleted', 'created_at']
    list_filter = ['status', 'is_deleted', 'created_at', 'start_date']
    search_fields = ['name', 'description', 'vendor__business_name']
    readonly_fields = ['created_at', 'updated_at', 'deleted_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('vendor', 'name', 'description', 'status')
        }),
        ('Dates', {
            'fields': ('start_date', 'end_date')
        }),
        ('Festival & Media', {
            'fields': ('festival_template_id', 'poster_url', 'custom_message', 'selected_products')
        }),
        ('Soft Delete', {
            'fields': ('is_deleted', 'deleted_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

