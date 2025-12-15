from django.contrib import admin
from .models import PortfolioSyncPlan,Portfolio
# Register your models here.
@admin.register(PortfolioSyncPlan)
class SyncPlanAdmin(admin.ModelAdmin):
    list_display = ("portfolio","allowed_syncs_per_day", "used_syncs_today", "extra_syncs_available", "last_sync_at")

@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ("id","vendor","is_featured")