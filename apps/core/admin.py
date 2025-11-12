from .models import BackgroundTask
from django.contrib import admin

@admin.register(BackgroundTask)
class BackgroundTaskAdmin(admin.ModelAdmin):
    list_display = ("id", "task_type", "status", "created_at")
    readonly_fields = ("result_data", "error_message")
