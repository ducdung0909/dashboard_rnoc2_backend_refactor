from datetime import datetime

from django.db import models


class Source(models.Model):
    """
    Bảng cấu hình data source cho thu thập dữ liệu batch.
    Mỗi Source đại diện cho một kết nối SFTP/FTP đến một OSS.
    """
    PROTOCOL_CHOICES = [
        ("SFTP", "SFTP"),
        ("FTP", "FTP"),
    ]

    SYSTEM_CHOICES = [
        ("2G", "2G"),
        ("3G", "3G"),
        ("4G", "4G"),
        ("5G", "5G"),
        ("VoLTE", "VoLTE"),
    ]

    LEVEL_CHOICES = [
        ("BSC", "BSC"),
        ("RNC", "RNC"),
        ("eNB", "eNB"),
        ("gNB", "gNB"),
    ]

    _id = models.AutoField(primary_key=True)
    active = models.CharField(
        max_length=10, default="1", null=True, blank=True
    )
    vendor = models.CharField(max_length=255, null=True, blank=True)
    system = models.CharField(
        max_length=10, choices=SYSTEM_CHOICES, null=True, blank=True
    )
    oss = models.CharField(max_length=255, default="", null=True, blank=True)
    protocol = models.CharField(
        max_length=10, choices=PROTOCOL_CHOICES, null=True, blank=True
    )
    ip = models.CharField(max_length=255, default="", null=True, blank=True)
    port = models.IntegerField(blank=True, null=True)
    level = models.CharField(
        max_length=10, choices=LEVEL_CHOICES, null=True, blank=True
    )
    data_user = models.CharField(max_length=255, default="", null=True, blank=True)
    data_pass = models.CharField(max_length=255, default="", null=True, blank=True)
    data_path = models.CharField(max_length=255, default="", null=True, blank=True)
    data_name = models.CharField(max_length=255, null=True, blank=True)
    data_sheet = models.CharField(max_length=255, null=True, blank=True)
    data_format = models.CharField(max_length=50, null=True, blank=True)
    data_file_delay = models.IntegerField(default=1, null=True, blank=True)
    data_kpi_delay = models.IntegerField(default=3, null=True, blank=True)
    data_header_name = models.JSONField(
        default=dict, null=True, blank=True,
        help_text="JSON mapping: {'Original_Col': ['kpi', 'new_col_name']}"
    )
    data_header_row = models.IntegerField(default=1, null=True, blank=True)
    data_table = models.CharField(max_length=255, default="", null=True, blank=True)
    datetime_file = models.CharField(
        max_length=50, default="%Y_%m_%d-%H", null=True, blank=True
    )
    datetime_kpi = models.CharField(
        max_length=50, default="%m.%d.%Y %H:00:00", null=True, blank=True
    )
    created_time = models.DateTimeField(default=datetime.now, null=True, blank=True)
    updated_time = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        db_table = "data_collector_source"
        ordering = ["-_id"]
        verbose_name = "Data Source"
        verbose_name_plural = "Data Sources"

    def __str__(self):
        return f"[{self.system}] {self.vendor} - {self.ip}/{self.data_name}"


class SourceRealtime(models.Model):
    """
    Bảng cấu hình data source cho thu thập dữ liệu realtime (15min/30min/60min).
    """
    PROTOCOL_CHOICES = [
        ("SFTP", "SFTP"),
        ("FTP", "FTP"),
    ]

    SYSTEM_CHOICES = [
        ("2G", "2G"),
        ("3G", "3G"),
        ("4G", "4G"),
        ("5G", "5G"),
        ("VoLTE", "VoLTE"),
    ]

    CYCLE_CHOICES = [
        (15, "15 minutes"),
        (30, "30 minutes"),
        (60, "60 minutes"),
    ]

    _id = models.AutoField(primary_key=True)
    vendor = models.CharField(max_length=255, null=True, blank=True)
    system = models.CharField(
        max_length=10, choices=SYSTEM_CHOICES, null=True, blank=True
    )
    protocol = models.CharField(
        max_length=10, choices=PROTOCOL_CHOICES, null=True, blank=True
    )
    ip = models.CharField(max_length=255, null=True, blank=True)
    port = models.IntegerField(blank=True, null=True)

    data_user = models.CharField(max_length=255, default="", null=True, blank=True)
    data_pass = models.CharField(max_length=255, default="", null=True, blank=True)
    data_path = models.CharField(max_length=255, default="", null=True, blank=True)
    data_name = models.CharField(max_length=255, null=True, blank=True)
    datetime_file = models.CharField(
        max_length=50, default="%Y%m%d%H%M", null=True, blank=True
    )
    data_format = models.CharField(max_length=50, null=True, blank=True)
    data_sheet = models.CharField(
        max_length=255, null=True, blank=True
    )
    data_header_row = models.IntegerField(
        default=0, null=True, blank=True
    )
    data_header_name = models.TextField(
        null=True, blank=True,
        help_text="JSON string mapping header columns"
    )
    data_skiprows = models.IntegerField(default=0, null=True, blank=True)

    cycle_minutes = models.IntegerField(
        default=60, choices=CYCLE_CHOICES, null=True, blank=True
    )
    level = models.CharField(max_length=255, null=True, blank=True)

    active = models.BooleanField(default=True)
    last_fetch_time = models.DateTimeField(null=True, blank=True)
    last_file_name = models.CharField(max_length=255, null=True, blank=True)
    created_time = models.DateTimeField(default=datetime.now, null=True, blank=True)
    updated_time = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        db_table = "data_collector_source_realtime"
        ordering = ["-_id"]
        verbose_name = "Realtime Source"
        verbose_name_plural = "Realtime Sources"

    def __str__(self):
        return f"[{self.system}] {self.ip}:{self.data_path}/{self.data_name}"

    def get_header_mapping(self) -> dict:
        """Parse data_header_name JSON string to dict."""
        if not self.data_header_name:
            return {}
        try:
            import json
            return json.loads(self.data_header_name)
        except (json.JSONDecodeError, TypeError):
            return {}


class Threshold(models.Model):
    """
    Bảng cấu hình ngưỡng cảnh báo cho dữ liệu batch.
    """
    _id = models.AutoField(primary_key=True)
    _system = models.CharField(max_length=255, null=True, blank=True)
    _level = models.CharField(max_length=255, null=True, blank=True)
    threshold = models.JSONField(
        default=dict, null=True, blank=True,
        help_text="JSON: {'kpi_name': {'min': 0, 'max': 100, 'warning': 90}}"
    )
    status = models.CharField(max_length=255, null=True, blank=True)
    created_time = models.DateTimeField(default=datetime.now, null=True, blank=True)
    updated_time = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        db_table = "data_collector_threshold"
        ordering = ["-_id"]
        verbose_name = "Threshold"
        verbose_name_plural = "Thresholds"

    def __str__(self):
        return f"[{self._system}] {self._level}"


class ThresholdRealtime(models.Model):
    """
    Bảng cấu hình ngưỡng cảnh báo realtime.
    """
    _id = models.AutoField(primary_key=True)
    _system = models.CharField(max_length=255, null=True, blank=True)
    _level = models.CharField(max_length=255, null=True, blank=True)
    threshold = models.JSONField(
        default=dict, null=True, blank=True,
        help_text="JSON: {'kpi_name': {'min': 0, 'max': 100, 'warning': 90}}"
    )
    status = models.CharField(max_length=255, null=True, blank=True)
    created_time = models.DateTimeField(default=datetime.now, null=True, blank=True)
    updated_time = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        db_table = "data_collector_threshold_realtime"
        ordering = ["-_id"]
        verbose_name = "Threshold Realtime"
        verbose_name_plural = "Thresholds Realtime"

    def __str__(self):
        return f"[{self._system}] {self._level}"


class CollectionLog(models.Model):
    """
    Bảng ghi log thực hiện test collect dữ liệu.
    Lưu trữ chi tiết từng bước: kết nối SFTP, tìm file, đọc dữ liệu, ghi database.
    """
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("success", "Success"),
        ("failed", "Failed"),
        ("warning", "Warning"),
    ]

    SOURCE_TYPE_CHOICES = [
        ("source", "Batch Source"),
        ("source_realtime", "Realtime Source"),
    ]

    _id = models.AutoField(primary_key=True)
    source_type = models.CharField(
        max_length=20, choices=SOURCE_TYPE_CHOICES, null=True, blank=True
    )
    source_id = models.IntegerField(null=True, blank=True)
    source_name = models.CharField(max_length=255, null=True, blank=True)

    test_datetime = models.DateTimeField(default=datetime.now, null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending", null=True, blank=True
    )

    steps = models.JSONField(
        default=list, null=True, blank=True,
        help_text="Danh sách các bước thực hiện: [{'step': 1, 'name': 'Connect SFTP', 'status': 'success', 'message': '...', 'details': {...}}]"
    )

    data_preview = models.JSONField(
        default=list, null=True, blank=True,
        help_text="Preview dữ liệu đã đọc được (JSON array)"
    )

    rows_fetched = models.IntegerField(default=0, null=True, blank=True)
    rows_written = models.IntegerField(default=0, null=True, blank=True)

    error_message = models.TextField(null=True, blank=True)
    execution_time = models.FloatField(
        default=0, null=True, blank=True,
        help_text="Thời gian thực thi (giây)"
    )

    test_hour = models.IntegerField(
        null=True, blank=True,
        help_text="Giờ được chọn để test (0-23)"
    )
    test_date = models.DateField(
        null=True, blank=True,
        help_text="Ngày được chọn để test"
    )

    created_time = models.DateTimeField(default=datetime.now, null=True, blank=True)

    class Meta:
        db_table = "data_collector_collection_log"
        ordering = ["-created_time"]
        verbose_name = "Collection Log"
        verbose_name_plural = "Collection Logs"
        indexes = [
            models.Index(fields=["source_type", "source_id"]),
            models.Index(fields=["status"]),
            models.Index(fields=["test_datetime"]),
        ]

    def __str__(self):
        return f"Log #{self._id} - {self.source_name} ({self.status})"

    def add_step(
        self,
        step: int,
        name: str,
        status: str,
        message: str = "",
        details: dict = None
    ):
        """Thêm một bước vào log."""
        if self.steps is None:
            self.steps = []
        self.steps.append({
            "step": step,
            "name": name,
            "status": status,
            "message": message,
            "details": details or {}
        })
        self.save(update_fields=["steps"])

    def set_success(self, rows_fetched: int = 0, rows_written: int = 0):
        """Đánh dấu log là thành công."""
        self.status = "success"
        self.rows_fetched = rows_fetched
        self.rows_written = rows_written
        self.save(update_fields=["status", "rows_fetched", "rows_written"])

    def set_failed(self, error_message: str):
        """Đánh dấu log là thất bại."""
        self.status = "failed"
        self.error_message = error_message
        self.save(update_fields=["status", "error_message"])
