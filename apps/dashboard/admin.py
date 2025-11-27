from django.contrib import admin
from .models import Customer,Invoice



@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'vendor', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'email', 'vendor__business_name']
    date_hierarchy = 'created_at'

    
    
@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('id',)