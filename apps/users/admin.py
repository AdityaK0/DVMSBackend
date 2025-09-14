from django.contrib import admin
from .models import User, CustomerProfile

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "email", "phone_number", "role", "created_at")
    list_filter = ("role", "created_at")
    search_fields = ("name", "email", "phone")

@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "created_at")
    search_fields = ("user__name", "user__email")
