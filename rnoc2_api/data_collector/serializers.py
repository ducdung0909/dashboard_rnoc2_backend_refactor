from rest_framework import serializers

from .models import CollectionLog, DataSource, ThresholdConfig


class DataSourceSerializer(serializers.ModelSerializer):
    """Serializer cho DataSource model."""

    cycle_display = serializers.SerializerMethodField()

    class Meta:
        model = DataSource
        fields = [
            "_id", "name", "active", "vendor", "system", "oss", "protocol",
            "ip", "port", "level", "data_user", "data_pass",
            "data_path", "data_name", "data_sheet", "data_format",
            "data_file_delay", "data_kpi_delay", "data_header_name",
            "data_header_row", "data_table", "datetime_file", "datetime_kpi",
            "data_skiprows", "cycle_minutes", "cycle_display",
            "last_fetch_time", "last_file_name",
            "created_time", "updated_time"
        ]
        read_only_fields = ["_id", "last_fetch_time", "last_file_name", "created_time", "updated_time"]

    def get_cycle_display(self, obj):
        """Trả về chuỗi hiển thị cycle."""
        if obj.cycle_minutes is None:
            return "Batch (60min)"
        return f"{obj.cycle_minutes} minutes"

    def validate_port(self, value):
        """Validate port number."""
        if value and (value < 1 or value > 65535):
            raise serializers.ValidationError("Port phải từ 1 đến 65535")
        return value

    def validate_cycle_minutes(self, value):
        """Validate cycle_minutes."""
        if value is not None and value not in [15, 30, 60]:
            raise serializers.ValidationError("cycle_minutes phải là None (batch), 15, 30, hoặc 60")
        return value


class ThresholdConfigSerializer(serializers.ModelSerializer):
    """Serializer cho ThresholdConfig model."""

    cycle_display = serializers.SerializerMethodField()

    class Meta:
        model = ThresholdConfig
        fields = [
            "_id", "name", "_system", "_level", "cycle_minutes", "cycle_display",
            "threshold", "status",
            "created_time", "updated_time"
        ]
        read_only_fields = ["_id", "created_time", "updated_time"]

    def get_cycle_display(self, obj):
        """Trả về chuỗi hiển thị cycle."""
        if obj.cycle_minutes is None:
            return "Batch (60min)"
        return f"{obj.cycle_minutes} minutes"

    def validate_threshold(self, value):
        """Validate threshold là valid JSON."""
        if value and not isinstance(value, dict):
            raise serializers.ValidationError("threshold phải là JSON object")
        return value


class CollectionLogSerializer(serializers.ModelSerializer):
    """Serializer cho CollectionLog model."""

    class Meta:
        model = CollectionLog
        fields = [
            "_id", "source_id", "source_name",
            "test_datetime", "status", "steps", "data_preview",
            "rows_fetched", "rows_written", "error_message",
            "execution_time", "test_hour", "test_date", "created_time"
        ]
        read_only_fields = [
            "_id", "steps", "data_preview", "rows_fetched",
            "rows_written", "error_message", "execution_time", "created_time"
        ]


class CollectionLogCreateSerializer(serializers.Serializer):
    """Serializer cho việc tạo mới CollectionLog (test collect)."""

    source_id = serializers.IntegerField(required=True)
    test_date = serializers.DateField(required=False, allow_null=True)
    test_hour = serializers.IntegerField(
        required=False, allow_null=True,
        min_value=0, max_value=23
    )

    def validate(self, data):
        """Validate source tồn tại."""
        source_id = data.get("source_id")

        if not DataSource.objects.filter(_id=source_id).exists():
            raise serializers.ValidationError(
                {"source_id": f"DataSource với id={source_id} không tồn tại"}
            )
        return data


class ExportRequestSerializer(serializers.Serializer):
    """Serializer cho export request."""

    model_name = serializers.ChoiceField(
        choices=[
            "datasource", "thresholdconfig",
            # KPI 60min (batch/hourly)
            "kpi2g_60min", "kpi3g_60min", "kpi4g_60min", "kpi5g_60min", "kpivolte_60min",
            # KPI 15min (realtime)
            "kpi2g_15min", "kpi3g_15min", "kpi4g_15min", "kpi5g_15min", "kpivolte_15min",
            "collection_log"
        ],
        required=True
    )
    filters = serializers.JSONField(required=False, allow_null=True)
    format = serializers.ChoiceField(
        choices=["json", "csv"],
        default="json"
    )


class ImportRequestSerializer(serializers.Serializer):
    """Serializer cho import request."""

    model_name = serializers.ChoiceField(
        choices=[
            "datasource", "thresholdconfig",
            "collection_log"
        ],
        required=True
    )
    data = serializers.ListField(
        child=serializers.JSONField(),
        required=True
    )
    mode = serializers.ChoiceField(
        choices=["upsert", "insert", "update"],
        default="upsert"
    )


class TestConnectionSerializer(serializers.Serializer):
    """Serializer cho test connection request."""

    source_id = serializers.IntegerField(required=True)

    def validate(self, data):
        """Validate source tồn tại."""
        source_id = data.get("source_id")

        if not DataSource.objects.filter(_id=source_id).exists():
            raise serializers.ValidationError(
                {"source_id": f"DataSource với id={source_id} không tồn tại"}
            )
        return data


# Backward compatibility serializers
SourceSerializer = DataSourceSerializer
SourceRealtimeSerializer = DataSourceSerializer
ThresholdSerializer = ThresholdConfigSerializer
ThresholdRealtimeSerializer = ThresholdConfigSerializer
