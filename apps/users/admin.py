from django.contrib import admin
from .models import User,Address

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "email", "phone_number", "role", "created_at")
    list_filter = ("role", "created_at")
    search_fields = ("name", "email", "phone")


@admin.register(Address)
class UserAddress(admin.ModelAdmin):
   list_display = [field.name for field in Address._meta.get_fields() if not field.many_to_many and not field.one_to_many]
