from django.contrib import admin

from .models import (
    CollectionLog,
    DataSource,
    Kpi2g15min,
    Kpi2g60min,
    Kpi3g15min,
    Kpi3g60min,
    Kpi4g15min,
    Kpi4g60min,
    Kpi5g15min,
    Kpi5g60min,
    KpiVolte15min,
    KpiVolte60min,
    ThresholdConfig,
)


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    """Admin cho DataSource (hợp nhất Source + SourceRealtime)."""
    list_display = [
        "_id", "name", "active", "vendor", "system", "oss",
        "protocol", "ip", "port", "cycle_minutes", "last_fetch_time"
    ]
    list_filter = ["active", "vendor", "system", "protocol", "cycle_minutes"]
    search_fields = ["ip", "data_name", "oss", "name"]
    ordering = ["-_id"]


@admin.register(ThresholdConfig)
class ThresholdConfigAdmin(admin.ModelAdmin):
    """Admin cho ThresholdConfig (hợp nhất Threshold + ThresholdRealtime)."""
    list_display = ["_id", "name", "_system", "_level", "cycle_minutes", "status", "created_time"]
    list_filter = ["_system", "_level", "cycle_minutes", "status"]
    search_fields = ["name", "_system", "_level"]
    ordering = ["-_id"]


@admin.register(CollectionLog)
class CollectionLogAdmin(admin.ModelAdmin):
    """Admin cho CollectionLog."""
    list_display = ["_id", "source_id", "source_name", "status", "rows_fetched", "execution_time", "created_time"]
    list_filter = ["status"]
    search_fields = ["source_name"]
    ordering = ["-_id"]
    readonly_fields = ["steps", "data_preview"]


# =============================================================================
# KPI 60min Admins (Batch/Hourly)
# =============================================================================

@admin.register(Kpi2g60min)
class Kpi2g60minAdmin(admin.ModelAdmin):
    list_display = ["_id", "_node_name", "_level", "_vendor", "_sta_datetime"]
    list_filter = ["_level", "_vendor"]
    search_fields = ["_node_name"]
    ordering = ["-_sta_datetime"]


@admin.register(Kpi3g60min)
class Kpi3g60minAdmin(admin.ModelAdmin):
    list_display = ["_id", "_node_name", "_level", "_vendor", "_sta_datetime"]
    list_filter = ["_level", "_vendor"]
    search_fields = ["_node_name"]
    ordering = ["-_sta_datetime"]


@admin.register(Kpi4g60min)
class Kpi4g60minAdmin(admin.ModelAdmin):
    list_display = ["_id", "_node_name", "_level", "_vendor", "_sta_datetime"]
    list_filter = ["_level", "_vendor"]
    search_fields = ["_node_name"]
    ordering = ["-_sta_datetime"]


@admin.register(Kpi5g60min)
class Kpi5g60minAdmin(admin.ModelAdmin):
    list_display = ["_id", "_node_name", "_level", "_vendor", "_sta_datetime"]
    list_filter = ["_level", "_vendor"]
    search_fields = ["_node_name"]
    ordering = ["-_sta_datetime"]


@admin.register(KpiVolte60min)
class KpiVolte60minAdmin(admin.ModelAdmin):
    list_display = ["_id", "_node_name", "_level", "_vendor", "_sta_datetime"]
    list_filter = ["_level", "_vendor"]
    search_fields = ["_node_name"]
    ordering = ["-_sta_datetime"]


# =============================================================================
# KPI 15min Admins (Realtime)
# =============================================================================

@admin.register(Kpi2g15min)
class Kpi2g15minAdmin(admin.ModelAdmin):
    list_display = ["_id", "_node_name", "_level", "_vendor", "_sta_datetime"]
    list_filter = ["_level", "_vendor"]
    search_fields = ["_node_name"]
    ordering = ["-_sta_datetime"]


@admin.register(Kpi3g15min)
class Kpi3g15minAdmin(admin.ModelAdmin):
    list_display = ["_id", "_node_name", "_level", "_vendor", "_sta_datetime"]
    list_filter = ["_level", "_vendor"]
    search_fields = ["_node_name"]
    ordering = ["-_sta_datetime"]


@admin.register(Kpi4g15min)
class Kpi4g15minAdmin(admin.ModelAdmin):
    list_display = ["_id", "_node_name", "_level", "_vendor", "_sta_datetime"]
    list_filter = ["_level", "_vendor"]
    search_fields = ["_node_name"]
    ordering = ["-_sta_datetime"]


@admin.register(Kpi5g15min)
class Kpi5g15minAdmin(admin.ModelAdmin):
    list_display = ["_id", "_node_name", "_level", "_vendor", "_sta_datetime"]
    list_filter = ["_level", "_vendor"]
    search_fields = ["_node_name"]
    ordering = ["-_sta_datetime"]


@admin.register(KpiVolte15min)
class KpiVolte15minAdmin(admin.ModelAdmin):
    list_display = ["_id", "_node_name", "_level", "_vendor", "_sta_datetime"]
    list_filter = ["_level", "_vendor"]
    search_fields = ["_node_name"]
    ordering = ["-_sta_datetime"]
