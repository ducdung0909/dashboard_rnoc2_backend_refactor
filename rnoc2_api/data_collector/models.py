from datetime import datetime

from django.db import models


# =============================================================================
# DataSource - Unified Source Model
# =============================================================================


class DataSource(models.Model):
    """
    Bảng cấu hình data source hợp nhất cho thu thập dữ liệu.
    Hỗ trợ cả batch (60min) và realtime (15/30/60 min).
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

    # Chu kỳ thu thập dữ liệu
    # - None hoặc 0: Batch (60min, theo giờ)
    # - 15: Realtime 15 phút
    # - 30: Realtime 30 phút
    # - 60: Realtime 60 phút
    CYCLE_CHOICES = [
        (None, "Batch (60min)"),
        (15, "15 minutes"),
        (30, "30 minutes"),
        (60, "60 minutes"),
    ]

    _id = models.AutoField(primary_key=True)
    name = models.CharField(
        max_length=255,
        null=True, blank=True,
        help_text="Tên hiển thị cho source"
    )
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
        max_length=50, null=True, blank=True,
        help_text="Format thời gian trong tên file. VD: %Y_%m_%d-%H (batch) hoặc %Y%m%d%H%M (realtime)"
    )
    datetime_kpi = models.CharField(
        max_length=50, default="%m.%d.%Y %H:00:00", null=True, blank=True
    )
    data_skiprows = models.IntegerField(default=0, null=True, blank=True)

    # Chu kỳ thu thập dữ liệu
    # None = Batch (60min), 15/30/60 = Realtime
    cycle_minutes = models.IntegerField(
        choices=CYCLE_CHOICES,
        default=None, null=True, blank=True,
        help_text="Chu kỳ thu thập: None=Batch(60min), 15/30/60=Realtime"
    )

    active = models.BooleanField(default=True)
    last_fetch_time = models.DateTimeField(null=True, blank=True)
    last_file_name = models.CharField(max_length=255, null=True, blank=True)

    created_time = models.DateTimeField(default=datetime.now, null=True, blank=True)
    updated_time = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        db_table = "data_collector_datasource"
        ordering = ["-_id"]
        verbose_name = "Data Source"
        verbose_name_plural = "Data Sources"

    def __str__(self):
        cycle_str = f"{self.cycle_minutes}min" if self.cycle_minutes else "batch"
        return f"[{self.system}] {self.vendor} - {self.ip}/{self.data_name} ({cycle_str})"

    def get_header_mapping(self) -> dict:
        """Parse data_header_name JSON to dict."""
        if not self.data_header_name:
            return {}
        if isinstance(self.data_header_name, dict):
            return self.data_header_name
        try:
            import json
            return json.loads(self.data_header_name)
        except (json.JSONDecodeError, TypeError):
            return {}

    def is_realtime(self) -> bool:
        """Kiểm tra xem đây có phải là source realtime không."""
        return self.cycle_minutes in [15, 30, 60]

    def is_batch(self) -> bool:
        """Kiểm tra xem đây có phải là source batch không."""
        return self.cycle_minutes is None


# =============================================================================
# ThresholdConfig - Unified Threshold Model
# =============================================================================


class ThresholdConfig(models.Model):
    """
    Bảng cấu hình ngưỡng cảnh báo hợp nhất.
    Hỗ trợ cả batch (60min) và realtime (15/30/60 min).
    """
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
        ("Cell", "Cell"),
    ]

    # Chu kỳ dữ liệu áp dụng
    # - None hoặc 0: Batch (60min)
    # - 15: Realtime 15 phút
    # - 30: Realtime 30 phút
    # - 60: Realtime 60 phút
    CYCLE_CHOICES = [
        (None, "Batch (60min)"),
        (15, "15 minutes"),
        (30, "30 minutes"),
        (60, "60 minutes"),
    ]

    _id = models.AutoField(primary_key=True)
    name = models.CharField(
        max_length=255,
        null=True, blank=True,
        help_text="Tên hiển thị cho threshold config"
    )
    _system = models.CharField(
        max_length=10, choices=SYSTEM_CHOICES, null=True, blank=True,
        help_text="Hệ thống (2G/3G/4G/5G/VoLTE)"
    )
    _level = models.CharField(
        max_length=50, choices=LEVEL_CHOICES, null=True, blank=True,
        help_text="Level (BSC/RNC/eNB/gNB/Cell)"
    )

    # Chu kỳ dữ liệu áp dụng threshold
    cycle_minutes = models.IntegerField(
        choices=CYCLE_CHOICES,
        default=None, null=True, blank=True,
        help_text="Chu kỳ dữ liệu: None=Batch(60min), 15/30/60=Realtime"
    )

    threshold = models.JSONField(
        default=dict, null=True, blank=True,
        help_text="JSON: {'kpi_name': {'min': 0, 'max': 100, 'warning': 90}}"
    )
    status = models.CharField(max_length=255, null=True, blank=True)
    created_time = models.DateTimeField(default=datetime.now, null=True, blank=True)
    updated_time = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        db_table = "data_collector_threshold_config"
        ordering = ["-_id"]
        verbose_name = "Threshold Config"
        verbose_name_plural = "Threshold Configs"

    def __str__(self):
        cycle_str = f"{self.cycle_minutes}min" if self.cycle_minutes else "batch"
        return f"[{self._system}] {self._level} ({cycle_str})"

    def is_realtime(self) -> bool:
        """Kiểm tra xem threshold này áp dụng cho realtime không."""
        return self.cycle_minutes in [15, 30, 60]

    def is_batch(self) -> bool:
        """Kiểm tra xem threshold này áp dụng cho batch không."""
        return self.cycle_minutes is None


# =============================================================================
# CollectionLog
# =============================================================================


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

    _id = models.AutoField(primary_key=True)
    source_id = models.IntegerField(null=True, blank=True)
    source_name = models.CharField(max_length=255, null=True, blank=True)

    test_datetime = models.DateTimeField(default=datetime.now, null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending", null=True, blank=True
    )

    steps = models.JSONField(
        default=list, null=True, blank=True,
        help_text="Danh sách các bước thực hiện"
    )

    data_preview = models.JSONField(
        default=list, null=True, blank=True,
        help_text="Preview dữ liệu đã đọc được"
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
            models.Index(fields=["source_id"]),
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


# =============================================================================
# KPI Models - 60min (Batch/Hourly data)
# =============================================================================


class Kpi2g60min(models.Model):
    """Bảng lưu trữ KPI 2G theo chu kỳ 60 phút (batch/hourly)."""
    _id = models.AutoField(primary_key=True)
    _node_name = models.CharField(max_length=255, default="", null=True, blank=True, db_index=True)
    _level = models.CharField(max_length=50, null=True, blank=True)
    _vendor = models.CharField(max_length=50, null=True, blank=True)
    _sta_datetime = models.DateTimeField(default=datetime.now, blank=True, db_index=True)

    cs_2g_cssrv1 = models.FloatField(default=0, null=True, blank=True)
    cs_2g_dcr = models.FloatField(default=0, null=True, blank=True)
    cs_2g_hosr = models.FloatField(default=0, null=True, blank=True)
    cs_2g_sdccd_blkr = models.FloatField(default=0, null=True, blank=True)
    cs_2g_tch_blkr = models.FloatField(default=0, null=True, blank=True)
    cs_2g_traffic = models.FloatField(default=0, null=True, blank=True)

    class Meta:
        db_table = "data_collector_kpi2g_60min"
        indexes = [
            models.Index(fields=["_node_name", "_sta_datetime"]),
            models.Index(fields=["_sta_datetime"]),
        ]
        verbose_name = "KPI 2G 60min"
        verbose_name_plural = "KPI 2G 60min"

    def __str__(self):
        return f"{self._node_name} @ {self._sta_datetime}"


class Kpi3g60min(models.Model):
    """Bảng lưu trữ KPI 3G theo chu kỳ 60 phút (batch/hourly)."""
    _id = models.AutoField(primary_key=True)
    _node_name = models.CharField(max_length=255, default="", null=True, blank=True, db_index=True)
    _level = models.CharField(max_length=50, null=True, blank=True)
    _vendor = models.CharField(max_length=50, null=True, blank=True)
    _sta_datetime = models.DateTimeField(default=datetime.now, blank=True, db_index=True)

    cs_3g_cssr = models.FloatField(default=0, null=True, blank=True)
    cs_3g_dcr = models.FloatField(default=0, null=True, blank=True)
    cs_3g_rab_conges = models.FloatField(default=0, null=True, blank=True)
    cs_3g_soft_ho = models.FloatField(default=0, null=True, blank=True)
    cs_3g_inter_ho = models.FloatField(default=0, null=True, blank=True)
    cs_3g_irat_ho = models.FloatField(default=0, null=True, blank=True)
    cs_3g_traffic = models.FloatField(default=0, null=True, blank=True)
    ps_3g_cssr = models.FloatField(default=0, null=True, blank=True)
    ps_3g_dcr = models.FloatField(default=0, null=True, blank=True)
    ps_3g_rab_conges = models.FloatField(default=0, null=True, blank=True)
    ps_3g_soft_ho = models.FloatField(default=0, null=True, blank=True)
    ps_3g_traffic = models.FloatField(default=0, null=True, blank=True)

    class Meta:
        db_table = "data_collector_kpi3g_60min"
        indexes = [
            models.Index(fields=["_node_name", "_sta_datetime"]),
            models.Index(fields=["_sta_datetime"]),
        ]
        verbose_name = "KPI 3G 60min"
        verbose_name_plural = "KPI 3G 60min"

    def __str__(self):
        return f"{self._node_name} @ {self._sta_datetime}"


class Kpi4g60min(models.Model):
    """Bảng lưu trữ KPI 4G theo chu kỳ 60 phút (batch/hourly)."""
    _id = models.AutoField(primary_key=True)
    _node_name = models.CharField(max_length=255, default="", null=True, blank=True, db_index=True)
    _level = models.CharField(max_length=50, null=True, blank=True)
    _vendor = models.CharField(max_length=50, null=True, blank=True)
    _sta_datetime = models.DateTimeField(default=datetime.now, blank=True, db_index=True)

    ps_4g_rrc_csssr = models.FloatField(default=0, null=True, blank=True)
    ps_4g_erab_ssr = models.FloatField(default=0, null=True, blank=True)
    ps_4g_cssr = models.FloatField(default=0, null=True, blank=True)
    ps_4g_dcr = models.FloatField(default=0, null=True, blank=True)
    ps_4g_intra_ho = models.FloatField(default=0, null=True, blank=True)
    ps_4g_inter_ho = models.FloatField(default=0, null=True, blank=True)
    ps_4g_irat_ho = models.FloatField(default=0, null=True, blank=True)
    ps_4g_eutran_csfb = models.FloatField(default=0, null=True, blank=True)
    ps_4g_dl_rbul = models.FloatField(default=0, null=True, blank=True)
    ps_4g_ul_rbdl = models.FloatField(default=0, null=True, blank=True)
    ps_4g_traffic = models.FloatField(default=0, null=True, blank=True)
    ps_4g_userdl_thrp = models.FloatField(default=0, null=True, blank=True)

    class Meta:
        db_table = "data_collector_kpi4g_60min"
        indexes = [
            models.Index(fields=["_node_name", "_sta_datetime"]),
            models.Index(fields=["_sta_datetime"]),
        ]
        verbose_name = "KPI 4G 60min"
        verbose_name_plural = "KPI 4G 60min"

    def __str__(self):
        return f"{self._node_name} @ {self._sta_datetime}"


class Kpi5g60min(models.Model):
    """Bảng lưu trữ KPI 5G theo chu kỳ 60 phút (batch/hourly)."""
    _id = models.AutoField(primary_key=True)
    _node_name = models.CharField(max_length=255, default="", null=True, blank=True, db_index=True)
    _level = models.CharField(max_length=50, null=True, blank=True)
    _vendor = models.CharField(max_length=50, null=True, blank=True)
    _sta_datetime = models.DateTimeField(default=datetime.now, blank=True, db_index=True)

    fiveg_sgnb_add_ssr = models.FloatField(null=True, blank=True)
    fiveg_sgnb_abn_ssr = models.FloatField(null=True, blank=True)
    fiveg_intrasgnb_pscellchg_ssr = models.FloatField(null=True, blank=True)
    fiveg_intersgnb_pscellchg_ssr = models.FloatField(null=True, blank=True)
    fiveg_user_dlthrp = models.FloatField(null=True, blank=True)

    class Meta:
        db_table = "data_collector_kpi5g_60min"
        indexes = [
            models.Index(fields=["_node_name", "_sta_datetime"]),
            models.Index(fields=["_sta_datetime"]),
        ]
        verbose_name = "KPI 5G 60min"
        verbose_name_plural = "KPI 5G 60min"

    def __str__(self):
        return f"{self._node_name} @ {self._sta_datetime}"


class KpiVolte60min(models.Model):
    """Bảng lưu trữ KPI VoLTE theo chu kỳ 60 phút (batch/hourly)."""
    _id = models.AutoField(primary_key=True)
    _node_name = models.CharField(max_length=255, default="", null=True, blank=True, db_index=True)
    _level = models.CharField(max_length=50, null=True, blank=True)
    _vendor = models.CharField(max_length=50, null=True, blank=True)
    _sta_datetime = models.DateTimeField(default=datetime.now, blank=True, db_index=True)

    volte_4g_dcr = models.FloatField(default=0, null=True, blank=True)
    volte_4g_erab_ssr = models.FloatField(default=0, null=True, blank=True)
    volte_4g_traffic = models.FloatField(default=0, null=True, blank=True)
    volte_4g_srvcc_ssr = models.FloatField(default=0, null=True, blank=True)
    volte_4g_intra_ho = models.FloatField(default=0, null=True, blank=True)
    volte_4g_inter_ho = models.FloatField(default=0, null=True, blank=True)

    class Meta:
        db_table = "data_collector_kpivolte_60min"
        indexes = [
            models.Index(fields=["_node_name", "_sta_datetime"]),
            models.Index(fields=["_sta_datetime"]),
        ]
        verbose_name = "KPI VoLTE 60min"
        verbose_name_plural = "KPI VoLTE 60min"

    def __str__(self):
        return f"{self._node_name} @ {self._sta_datetime}"


# =============================================================================
# KPI Models - 15min (Realtime data - chu kỳ 15 phút)
# =============================================================================


class Kpi2g15min(models.Model):
    """Bảng lưu trữ KPI 2G theo chu kỳ 15 phút (realtime)."""
    _id = models.AutoField(primary_key=True)
    _node_name = models.CharField(max_length=255, default="", null=True, blank=True, db_index=True)
    _level = models.CharField(max_length=50, null=True, blank=True)
    _vendor = models.CharField(max_length=50, null=True, blank=True)
    _sta_datetime = models.DateTimeField(default=datetime.now, blank=True, db_index=True)

    cs_2g_cssrv1 = models.FloatField(default=0, null=True, blank=True)
    cs_2g_dcr = models.FloatField(default=0, null=True, blank=True)
    cs_2g_hosr = models.FloatField(default=0, null=True, blank=True)
    cs_2g_sdccd_blkr = models.FloatField(default=0, null=True, blank=True)
    cs_2g_tch_blkr = models.FloatField(default=0, null=True, blank=True)
    cs_2g_traffic = models.FloatField(default=0, null=True, blank=True)

    class Meta:
        db_table = "data_collector_kpi2g_15min"
        indexes = [
            models.Index(fields=["_node_name", "_sta_datetime"]),
            models.Index(fields=["_sta_datetime"]),
        ]
        verbose_name = "KPI 2G 15min"
        verbose_name_plural = "KPI 2G 15min"

    def __str__(self):
        return f"{self._node_name} @ {self._sta_datetime}"


class Kpi3g15min(models.Model):
    """Bảng lưu trữ KPI 3G theo chu kỳ 15 phút (realtime)."""
    _id = models.AutoField(primary_key=True)
    _node_name = models.CharField(max_length=255, default="", null=True, blank=True, db_index=True)
    _level = models.CharField(max_length=50, null=True, blank=True)
    _vendor = models.CharField(max_length=50, null=True, blank=True)
    _sta_datetime = models.DateTimeField(default=datetime.now, blank=True, db_index=True)

    cs_3g_cssr = models.FloatField(default=0, null=True, blank=True)
    cs_3g_dcr = models.FloatField(default=0, null=True, blank=True)
    cs_3g_rab_conges = models.FloatField(default=0, null=True, blank=True)
    cs_3g_soft_ho = models.FloatField(default=0, null=True, blank=True)
    cs_3g_inter_ho = models.FloatField(default=0, null=True, blank=True)
    cs_3g_irat_ho = models.FloatField(default=0, null=True, blank=True)
    cs_3g_traffic = models.FloatField(default=0, null=True, blank=True)
    ps_3g_cssr = models.FloatField(default=0, null=True, blank=True)
    ps_3g_dcr = models.FloatField(default=0, null=True, blank=True)
    ps_3g_rab_conges = models.FloatField(default=0, null=True, blank=True)
    ps_3g_soft_ho = models.FloatField(default=0, null=True, blank=True)
    ps_3g_traffic = models.FloatField(default=0, null=True, blank=True)

    class Meta:
        db_table = "data_collector_kpi3g_15min"
        indexes = [
            models.Index(fields=["_node_name", "_sta_datetime"]),
            models.Index(fields=["_sta_datetime"]),
        ]
        verbose_name = "KPI 3G 15min"
        verbose_name_plural = "KPI 3G 15min"

    def __str__(self):
        return f"{self._node_name} @ {self._sta_datetime}"


class Kpi4g15min(models.Model):
    """Bảng lưu trữ KPI 4G theo chu kỳ 15 phút (realtime)."""
    _id = models.AutoField(primary_key=True)
    _node_name = models.CharField(max_length=255, default="", null=True, blank=True, db_index=True)
    _level = models.CharField(max_length=50, null=True, blank=True)
    _vendor = models.CharField(max_length=50, null=True, blank=True)
    _sta_datetime = models.DateTimeField(default=datetime.now, blank=True, db_index=True)

    ps_4g_rrc_csssr = models.FloatField(default=0, null=True, blank=True)
    ps_4g_erab_ssr = models.FloatField(default=0, null=True, blank=True)
    ps_4g_cssr = models.FloatField(default=0, null=True, blank=True)
    ps_4g_dcr = models.FloatField(default=0, null=True, blank=True)
    ps_4g_intra_ho = models.FloatField(default=0, null=True, blank=True)
    ps_4g_inter_ho = models.FloatField(default=0, null=True, blank=True)
    ps_4g_irat_ho = models.FloatField(default=0, null=True, blank=True)
    ps_4g_eutran_csfb = models.FloatField(default=0, null=True, blank=True)
    ps_4g_dl_rbul = models.FloatField(default=0, null=True, blank=True)
    ps_4g_ul_rbdl = models.FloatField(default=0, null=True, blank=True)
    ps_4g_traffic = models.FloatField(default=0, null=True, blank=True)
    ps_4g_userdl_thrp = models.FloatField(default=0, null=True, blank=True)

    class Meta:
        db_table = "data_collector_kpi4g_15min"
        indexes = [
            models.Index(fields=["_node_name", "_sta_datetime"]),
            models.Index(fields=["_sta_datetime"]),
        ]
        verbose_name = "KPI 4G 15min"
        verbose_name_plural = "KPI 4G 15min"

    def __str__(self):
        return f"{self._node_name} @ {self._sta_datetime}"


class Kpi5g15min(models.Model):
    """Bảng lưu trữ KPI 5G theo chu kỳ 15 phút (realtime)."""
    _id = models.AutoField(primary_key=True)
    _node_name = models.CharField(max_length=255, default="", null=True, blank=True, db_index=True)
    _level = models.CharField(max_length=50, null=True, blank=True)
    _vendor = models.CharField(max_length=50, null=True, blank=True)
    _sta_datetime = models.DateTimeField(default=datetime.now, blank=True, db_index=True)

    fiveg_sgnb_add_ssr = models.FloatField(null=True, blank=True)
    fiveg_sgnb_abn_ssr = models.FloatField(null=True, blank=True)
    fiveg_intrasgnb_pscellchg_ssr = models.FloatField(null=True, blank=True)
    fiveg_intersgnb_pscellchg_ssr = models.FloatField(null=True, blank=True)
    fiveg_user_dlthrp = models.FloatField(null=True, blank=True)

    class Meta:
        db_table = "data_collector_kpi5g_15min"
        indexes = [
            models.Index(fields=["_node_name", "_sta_datetime"]),
            models.Index(fields=["_sta_datetime"]),
        ]
        verbose_name = "KPI 5G 15min"
        verbose_name_plural = "KPI 5G 15min"

    def __str__(self):
        return f"{self._node_name} @ {self._sta_datetime}"


class KpiVolte15min(models.Model):
    """Bảng lưu trữ KPI VoLTE theo chu kỳ 15 phút (realtime)."""
    _id = models.AutoField(primary_key=True)
    _node_name = models.CharField(max_length=255, default="", null=True, blank=True, db_index=True)
    _level = models.CharField(max_length=50, null=True, blank=True)
    _vendor = models.CharField(max_length=50, null=True, blank=True)
    _sta_datetime = models.DateTimeField(default=datetime.now, blank=True, db_index=True)

    volte_4g_dcr = models.FloatField(default=0, null=True, blank=True)
    volte_4g_erab_ssr = models.FloatField(default=0, null=True, blank=True)
    volte_4g_traffic = models.FloatField(default=0, null=True, blank=True)
    volte_4g_srvcc_ssr = models.FloatField(default=0, null=True, blank=True)
    volte_4g_intra_ho = models.FloatField(default=0, null=True, blank=True)
    volte_4g_inter_ho = models.FloatField(default=0, null=True, blank=True)

    class Meta:
        db_table = "data_collector_kpivolte_15min"
        indexes = [
            models.Index(fields=["_node_name", "_sta_datetime"]),
            models.Index(fields=["_sta_datetime"]),
        ]
        verbose_name = "KPI VoLTE 15min"
        verbose_name_plural = "KPI VoLTE 15min"

    def __str__(self):
        return f"{self._node_name} @ {self._sta_datetime}"


# =============================================================================
# Legacy model aliases for backward compatibility
# =============================================================================

# Aliases để tương thích ngược với code cũ
# Deprecated: Sử dụng DataSource thay vì Source hoặc SourceRealtime
Source = DataSource
SourceRealtime = DataSource

# Deprecated: Sử dụng ThresholdConfig thay vì Threshold hoặc ThresholdRealtime
Threshold = ThresholdConfig
ThresholdRealtime = ThresholdConfig
