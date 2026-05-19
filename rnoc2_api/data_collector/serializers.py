from rest_framework import serializers

from .models import Source, SourceRealtime, Threshold, ThresholdRealtime, CollectionLog


class SourceSerializer(serializers.ModelSerializer):
    """Serializer cho Source model."""

    class Meta:
        model = Source
        fields = [
            "_id", "active", "vendor", "system", "oss", "protocol",
            "ip", "port", "level", "data_user", "data_pass",
            "data_path", "data_name", "data_sheet", "data_format",
            "data_file_delay", "data_kpi_delay", "data_header_name",
            "data_header_row", "data_table", "datetime_file", "datetime_kpi",
            "created_time", "updated_time"
        ]
        read_only_fields = ["_id", "created_time", "updated_time"]

    def validate_port(self, value):
        """Validate port number."""
        if value and (value < 1 or value > 65535):
            raise serializers.ValidationError("Port phải từ 1 đến 65535")
        return value

    def validate_data_header_name(self, value):
        """Validate data_header_name là valid JSON dict."""
        if value and not isinstance(value, dict):
            raise serializers.ValidationError("data_header_name phải là JSON object")
        return value


class SourceRealtimeSerializer(serializers.ModelSerializer):
    """Serializer cho SourceRealtime model."""

    class Meta:
        model = SourceRealtime
        fields = [
            "_id", "vendor", "system", "protocol", "ip", "port",
            "data_user", "data_pass", "data_path", "data_name",
            "datetime_file", "data_format", "data_sheet", "data_header_row",
            "data_header_name", "data_skiprows", "cycle_minutes", "level",
            "active", "last_fetch_time", "last_file_name",
            "created_time", "updated_time"
        ]
        read_only_fields = ["_id", "last_fetch_time", "last_file_name", "created_time", "updated_time"]

    def validate_port(self, value):
        """Validate port number."""
        if value and (value < 1 or value > 65535):
            raise serializers.ValidationError("Port phải từ 1 đến 65535")
        return value

    def validate_cycle_minutes(self, value):
        """Validate cycle_minutes."""
        if value and value not in [15, 30, 60]:
            raise serializers.ValidationError("cycle_minutes phải là 15, 30, hoặc 60")
        return value


class ThresholdSerializer(serializers.ModelSerializer):
    """Serializer cho Threshold model."""

    class Meta:
        model = Threshold
        fields = [
            "_id", "_system", "_level", "threshold", "status",
            "created_time", "updated_time"
        ]
        read_only_fields = ["_id", "created_time", "updated_time"]

    def validate_threshold(self, value):
        """Validate threshold là valid JSON."""
        if value and not isinstance(value, dict):
            raise serializers.ValidationError("threshold phải là JSON object")
        return value


class ThresholdRealtimeSerializer(serializers.ModelSerializer):
    """Serializer cho ThresholdRealtime model."""

    class Meta:
        model = ThresholdRealtime
        fields = [
            "_id", "_system", "_level", "threshold", "status",
            "created_time", "updated_time"
        ]
        read_only_fields = ["_id", "created_time", "updated_time"]

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
            "_id", "source_type", "source_id", "source_name",
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

    source_type = serializers.ChoiceField(
        choices=["source", "source_realtime"],
        required=True
    )
    source_id = serializers.IntegerField(required=True)
    test_date = serializers.DateField(required=False, allow_null=True)
    test_hour = serializers.IntegerField(
        required=False, allow_null=True,
        min_value=0, max_value=23
    )

    def validate(self, data):
        """Validate source tồn tại."""
        source_type = data.get("source_type")
        source_id = data.get("source_id")

        if source_type == "source":
            if not Source.objects.filter(_id=source_id).exists():
                raise serializers.ValidationError(
                    {"source_id": f"Source với id={source_id} không tồn tại"}
                )
        elif source_type == "source_realtime":
            if not SourceRealtime.objects.filter(_id=source_id).exists():
                raise serializers.ValidationError(
                    {"source_id": f"SourceRealtime với id={source_id} không tồn tại"}
                )
        return data


class ExportRequestSerializer(serializers.Serializer):
    """Serializer cho export request."""

    model_name = serializers.ChoiceField(
        choices=[
            "source", "sourcerealtime", "threshold", "threshold_realtime",
            "kpi2g", "kpi3g", "kpi4g", "kpi5g", "kpivolte",
            "kpi2g_realtime", "kpi3g_realtime", "kpi4g_realtime",
            "kpi5g_realtime", "kpivolte_realtime",
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
            "source", "sourcerealtime", "threshold", "threshold_realtime",
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

    source_type = serializers.ChoiceField(
        choices=["source", "source_realtime"],
        required=True
    )
    source_id = serializers.IntegerField(required=True)

    def validate(self, data):
        """Validate source tồn tại."""
        source_type = data.get("source_type")
        source_id = data.get("source_id")

        if source_type == "source":
            if not Source.objects.filter(_id=source_id).exists():
                raise serializers.ValidationError(
                    {"source_id": f"Source với id={source_id} không tồn tại"}
                )
        elif source_type == "source_realtime":
            if not SourceRealtime.objects.filter(_id=source_id).exists():
                raise serializers.ValidationError(
                    {"source_id": f"SourceRealtime với id={source_id} không tồn tại"}
                )
        return data
