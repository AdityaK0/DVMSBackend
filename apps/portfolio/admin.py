from django.contrib import admin
from .models import PortfolioSyncPlan
# Register your models here.
@admin.register(PortfolioSyncPlan)
class SyncPlanAdmin(admin.ModelAdmin):
    list_display = ("vendor", "allowed_syncs_per_day", "used_syncs_today", "extra_syncs_available", "last_sync_at")
