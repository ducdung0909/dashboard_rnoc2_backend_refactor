from django.contrib import admin

from .models import Source, SourceRealtime, Threshold, ThresholdRealtime


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = [
        "_id", "active", "vendor", "system", "oss",
        "protocol", "ip", "port", "data_name"
    ]
    list_filter = ["active", "vendor", "system", "protocol"]
    search_fields = ["ip", "data_name", "oss"]
    ordering = ["-_id"]


@admin.register(SourceRealtime)
class SourceRealtimeAdmin(admin.ModelAdmin):
    list_display = [
        "_id", "vendor", "system", "protocol", "ip",
        "cycle_minutes", "active", "last_fetch_time"
    ]
    list_filter = ["active", "vendor", "system", "protocol", "cycle_minutes"]
    search_fields = ["ip", "data_name"]
    ordering = ["-_id"]


@admin.register(Threshold)
class ThresholdAdmin(admin.ModelAdmin):
    list_display = ["_id", "_system", "_level", "status", "created_time"]
    list_filter = ["_system", "_level", "status"]
    ordering = ["-_id"]


@admin.register(ThresholdRealtime)
class ThresholdRealtimeAdmin(admin.ModelAdmin):
    list_display = ["_id", "_system", "_level", "status", "created_time"]
    list_filter = ["_system", "_level", "status"]
    ordering = ["-_id"]
