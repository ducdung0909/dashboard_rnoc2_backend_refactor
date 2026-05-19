"""
Business logic layer cho data_collector app.
Chứa các service classes xử lý nghiệp vụ: test connection, collect, export, import.
"""
import csv
import io
import json
import time
from datetime import datetime, timedelta
from typing import Any, Optional

import pandas as pd
import paramiko
from django.db.models import QuerySet
from ftplib import FTP

from .models import (
    CollectionLog,
    DataSource,
    Kpi2g15min,
    Kpi3g15min,
    Kpi4g15min,
    Kpi5g15min,
    KpiVolte15min,
    Kpi2g60min,
    Kpi3g60min,
    Kpi4g60min,
    Kpi5g60min,
    KpiVolte60min,
    ThresholdConfig,
)

# Backward compatibility aliases
Source = DataSource
SourceRealtime = DataSource
Threshold = ThresholdConfig
ThresholdRealtime = ThresholdConfig


class SourceService:
    """Service xử lý nghiệp vụ cho DataSource."""

    @staticmethod
    def get_source(source_id: int) -> Optional[DataSource]:
        """Lấy source theo id."""
        return DataSource.objects.filter(_id=source_id).first()

    @staticmethod
    def get_sources_by_cycle(cycle_minutes: int = None) -> QuerySet:
        """
        Lấy danh sách sources theo chu kỳ.
        cycle_minutes=None: Batch (60min)
        cycle_minutes=15/30/60: Realtime
        """
        if cycle_minutes is None:
            return DataSource.objects.filter(cycle_minutes__isnull=True)
        return DataSource.objects.filter(cycle_minutes=cycle_minutes)

    @staticmethod
    def test_sftp_connection(source: Source | SourceRealtime) -> tuple[bool, str, dict]:
        """
        Test kết nối SFTP.
        Returns: (success, message, details)
        """
        details = {}
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            port = source.port or 22
            ssh.connect(
                hostname=source.ip,
                port=port,
                username=source.data_user,
                password=source.data_pass,
                timeout=10
            )
            details["ssh_connected"] = True
            details["server_banner"] = ssh.get_transport().remote_version

            sftp = ssh.open_sftp()
            sftp.listdir(source.data_path)
            details["sftp_connected"] = True
            details["path_accessible"] = True
            details["path"] = source.data_path

            sftp.close()
            ssh.close()

            return True, "Kết nối SFTP thành công!", details

        except paramiko.AuthenticationException:
            return False, "Xác thực thất bại. Kiểm tra username/password.", details
        except paramiko.SSHException as e:
            return False, f"Lỗi SSH: {str(e)}", details
        except FileNotFoundError:
            return False, f"Không tìm thấy đường dẫn: {source.data_path}", details
        except Exception as e:
            return False, f"Lỗi kết nối: {str(e)}", details

    @staticmethod
    def test_ftp_connection(source: Source | SourceRealtime) -> tuple[bool, str, dict]:
        """
        Test kết nối FTP.
        Returns: (success, message, details)
        """
        details = {}
        try:
            ftp = FTP()
            port = source.port or 21

            ftp.connect(host=source.ip, port=port, timeout=10)
            details["connected"] = True

            ftp.login(user=source.data_user, passwd=source.data_pass)
            details["authenticated"] = True

            if source.data_path:
                ftp.cwd(source.data_path)
            details["path"] = source.data_path

            files = ftp.nlst()
            details["files_count"] = len(files)
            details["sample_files"] = files[:5] if files else []

            ftp.quit()

            return True, "Kết nối FTP thành công!", details

        except Exception as e:
            return False, f"Lỗi kết nối FTP: {str(e)}", details

    @staticmethod
    def test_connection(source_id: int) -> tuple[bool, str, dict]:
        """Test kết nối cho source."""
        source = SourceService.get_source(source_id)
        if not source:
            return False, f"Source không tồn tại (id={source_id})", {}

        protocol = (source.protocol or "SFTP").upper()
        if protocol == "SFTP":
            return SourceService.test_sftp_connection(source)
        elif protocol == "FTP":
            return SourceService.test_ftp_connection(source)
        else:
            return False, f"Protocol không được hỗ trợ: {protocol}", {}


class TestCollectService:
    """
    Service xử lý test collect với ghi log chi tiết từng bước.
    """

    def __init__(self, source_id: int, test_date: str = None, test_hour: int = None):
        self.source_id = source_id
        self.test_date = test_date
        self.test_hour = test_hour
        self.log: Optional[CollectionLog] = None
        self.start_time = None

    def _create_log(self) -> CollectionLog:
        """Tạo collection log record."""
        source = SourceService.get_source(self.source_id)
        source_name = str(source) if source else f"Unknown (id={self.source_id})"

        log = CollectionLog.objects.create(
            source_id=self.source_id,
            source_name=source_name,
            test_date=datetime.strptime(self.test_date, "%Y-%m-%d").date() if self.test_date else None,
            test_hour=self.test_hour,
            status="running",
            steps=[]
        )
        return log

    def _add_step(
        self,
        step: int,
        name: str,
        status: str,
        message: str = "",
        details: dict = None
    ):
        """Thêm một bước vào log."""
        if self.log:
            self.log.add_step(step, name, status, message, details)

    def _set_success(self, rows_fetched: int, rows_written: int):
        """Đánh dấu thành công."""
        if self.log:
            execution_time = time.time() - self.start_time
            self.log.execution_time = round(execution_time, 2)
            self.log.set_success(rows_fetched, rows_written)

    def _set_failed(self, error_message: str):
        """Đánh dấu thất bại."""
        if self.log:
            execution_time = time.time() - self.start_time
            self.log.execution_time = round(execution_time, 2)
            self.log.set_failed(error_message)

    def execute(self) -> dict:
        """
        Thực thi test collect với ghi log chi tiết.
        Returns dict với kết quả và log_id.
        """
        self.start_time = time.time()
        self.log = self._create_log()

        try:
            # Step 1: Validate source
            self._add_step(1, "Validate Source", "running", "Đang kiểm tra source...")
            source = SourceService.get_source(self.source_id)

            if not source:
                raise Exception(f"Source không tồn tại (id={self.source_id})")

            cycle_info = "batch" if source.is_batch() else f"{source.cycle_minutes}min"
            self._add_step(
                1, "Validate Source", "success",
                f"Tìm thấy source: {source} ({cycle_info})",
                {"source_id": source._id, "protocol": source.protocol, "cycle": cycle_info}
            )

            # Step 2: Test connection
            self._add_step(2, "Test Connection", "running", "Đang kết nối...")
            success, msg, conn_details = SourceService.test_connection(self.source_id)

            if not success:
                self._add_step(2, "Test Connection", "failed", msg, conn_details)
                raise Exception(msg)

            self._add_step(2, "Test Connection", "success", msg, conn_details)

            # Step 3: Find files
            self._add_step(3, "Find Files", "running", "Đang tìm file...")
            file_info = self._find_files(source)
            self._add_step(3, "Find Files", "success", file_info["message"], file_info)

            if not file_info.get("found"):
                self._add_step(4, "Read Data", "warning", "Không tìm thấy file phù hợp")
                self._set_success(0, 0)
                return {
                    "success": True,
                    "log_id": self.log._id,
                    "message": "Kết nối thành công nhưng không tìm thấy file",
                    "data": None,
                    "steps": self.log.steps
                }

            # Step 4: Read data
            self._add_step(4, "Read Data", "running", "Đang đọc dữ liệu...")
            data_result = self._read_data(source, file_info)
            self._add_step(4, "Read Data", "success", data_result["message"], data_result)

            # Step 5: Preview data
            self._add_step(5, "Preview Data", "running", "Đang xem trước dữ liệu...")
            df = data_result.get("dataframe")
            preview = self._preview_data(df)
            self._add_step(5, "Preview Data", "success", f"Preview {len(preview)} rows", {"rows": len(preview)})

            # Lưu preview vào log
            self.log.data_preview = preview
            self.log.save(update_fields=["data_preview"])

            # Step 6: Write to database (test mode - không ghi thực sự)
            rows_fetched = len(df) if df is not None else 0
            self._add_step(
                6, "Write Database", "success",
                f"Test mode: đọc được {rows_fetched} rows",
                {"rows_fetched": rows_fetched, "mode": "test"}
            )

            self._set_success(rows_fetched, 0)
            return {
                "success": True,
                "log_id": self.log._id,
                "message": "Test collect thành công",
                "data": preview,
                "data_info": {
                    "total_rows": rows_fetched,
                    "columns": list(df.columns) if df is not None else [],
                    "file_found": file_info.get("file_name"),
                    "file_path": file_info.get("file_path")
                },
                "steps": self.log.steps
            }

        except Exception as e:
            self._set_failed(str(e))
            return {
                "success": False,
                "log_id": self.log._id,
                "message": f"Test collect thất bại: {str(e)}",
                "error": str(e),
                "steps": self.log.steps if self.log else []
            }

    def _find_files(self, source: Source | SourceRealtime) -> dict:
        """Tìm files trên SFTP/FTP server."""
        result = {
            "found": False,
            "message": "",
            "files": [],
            "file_name": None,
            "file_path": None,
            "file_timestamp": None
        }

        try:
            # Tính thời gian test
            now = datetime.now()
            if self.test_date:
                test_dt = datetime.strptime(self.test_date, "%Y-%m-%d")
                if self.test_hour is not None:
                    test_dt = test_dt.replace(hour=self.test_hour)
            else:
                test_dt = now

            # Áp dụng file_delay
            file_dt = test_dt - timedelta(hours=source.data_file_delay or 1)
            file_st = file_dt.strftime(source.datetime_file or "%Y_%m_%d-%H")

            result["calculated_time"] = {
                "test_datetime": test_dt.isoformat(),
                "file_datetime": file_dt.isoformat(),
                "file_pattern": file_st
            }

            protocol = (source.protocol or "SFTP").upper()

            if protocol == "SFTP":
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(
                    hostname=source.ip,
                    port=source.port or 22,
                    username=source.data_user,
                    password=source.data_pass,
                    timeout=10
                )
                sftp = ssh.open_sftp()

                all_files = sftp.listdir(source.data_path)
                result["all_files_count"] = len(all_files)
                result["path"] = source.data_path

                # Tìm file match pattern
                matching_files = [
                    f for f in all_files
                    if source.data_name in f and file_st in f
                ]

                result["matching_files"] = matching_files

                if matching_files:
                    result["found"] = True
                    result["file_name"] = matching_files[0]
                    result["file_path"] = source.data_path + matching_files[0]

                    # Lấy thêm thông tin file
                    stat = sftp.stat(source.data_path + matching_files[0])
                    result["file_size"] = stat.st_size
                    result["file_mtime"] = datetime.fromtimestamp(stat.st_mtime).isoformat()

                    result["message"] = f"Tìm thấy {len(matching_files)} file(s), sử dụng: {matching_files[0]}"
                else:
                    result["message"] = f"Không tìm thấy file phù hợp với pattern: {source.data_name}*{file_st}*"

                sftp.close()
                ssh.close()

            elif protocol == "FTP":
                ftp = FTP()
                ftp.connect(host=source.ip, port=source.port or 21, timeout=10)
                ftp.login(user=source.data_user, passwd=source.data_pass)
                ftp.cwd(source.data_path)

                all_files = ftp.nlst()
                result["all_files_count"] = len(all_files)
                result["path"] = source.data_path

                matching_files = [
                    f for f in all_files
                    if source.data_name in f and file_st in f
                ]
                result["matching_files"] = matching_files

                if matching_files:
                    result["found"] = True
                    result["file_name"] = matching_files[0]
                    result["file_path"] = source.data_path + matching_files[0]
                    result["message"] = f"Tìm thấy {len(matching_files)} file(s), sử dụng: {matching_files[0]}"
                else:
                    result["message"] = f"Không tìm thấy file phù hợp với pattern: {source.data_name}*{file_st}*"

                ftp.quit()

            return result

        except Exception as e:
            result["message"] = f"Lỗi tìm file: {str(e)}"
            result["error"] = str(e)
            return result

    def _read_data(self, source: Source | SourceRealtime, file_info: dict) -> dict:
        """Đọc dữ liệu từ file."""
        result = {
            "success": False,
            "message": "",
            "dataframe": None,
            "columns": [],
            "rows": 0
        }

        if not file_info.get("found"):
            result["message"] = "Không tìm thấy file để đọc"
            return result

        try:
            file_path = file_info.get("file_path")
            protocol = (source.protocol or "SFTP").upper()

            # Tính KPI datetime
            now = datetime.now()
            if self.test_date:
                test_dt = datetime.strptime(self.test_date, "%Y-%m-%d")
                if self.test_hour is not None:
                    test_dt = test_dt.replace(hour=self.test_hour)
            else:
                test_dt = now

            kpi_dt = test_dt - timedelta(hours=source.data_kpi_delay or 3)
            kpi_st = kpi_dt.strftime("%Y-%m-%d %H")

            result["kpi_datetime"] = kpi_st

            df = None

            if protocol == "SFTP":
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(
                    hostname=source.ip,
                    port=source.port or 22,
                    username=source.data_user,
                    password=source.data_pass,
                    timeout=30
                )
                sftp = ssh.open_sftp()

                with sftp.open(file_path) as f:
                    if source.data_format and ".csv" in source.data_format.lower():
                        df = pd.read_csv(f, sep=";")
                    else:
                        header_row = int(source.data_header_row or 1) - 1
                        df = pd.read_excel(
                            f,
                            header=header_row,
                            sheet_name=source.data_sheet or 0
                        )

                sftp.close()
                ssh.close()

            elif protocol == "FTP":
                ftp = FTP()
                ftp.connect(host=source.ip, port=source.port or 21, timeout=30)
                ftp.login(user=source.data_user, passwd=source.data_pass)

                bio = io.BytesIO()
                ftp.retrbinary(f"RETR {file_path}", bio.write)
                bio.seek(0)

                if source.data_format and ".csv" in source.data_format.lower():
                    df = pd.read_csv(bio, sep=";")
                else:
                    header_row = int(source.data_header_row or 1) - 1
                    df = pd.read_excel(
                        bio,
                        header=header_row,
                        sheet_name=source.data_sheet or 0
                    )

                ftp.quit()

            if df is not None:
                # Xử lý columns theo header mapping
                header_mapping = {}
                if source.data_header_name:
                    if isinstance(source.data_header_name, dict):
                        header_mapping = source.data_header_name
                    elif isinstance(source.data_header_name, str):
                        try:
                            header_mapping = json.loads(source.data_header_name)
                        except json.JSONDecodeError:
                            pass

                # Rename columns
                for col in df.columns:
                    if col in header_mapping:
                        mapping = header_mapping[col]
                        if isinstance(mapping, list) and len(mapping) >= 2:
                            new_name = mapping[1]
                            df.rename(columns={col: new_name}, inplace=True)

                # Filter by datetime
                if "_sta_datetime" in df.columns:
                    df["_sta_datetime"] = pd.to_datetime(df["_sta_datetime"], format=source.datetime_kpi, errors="coerce")
                    df["_sta_datetime"] = df["_sta_datetime"].dt.strftime("%Y-%m-%d %H")
                    df = df[df["_sta_datetime"] == kpi_st]

                result["dataframe"] = df
                result["columns"] = list(df.columns)
                result["rows"] = len(df)
                result["success"] = True
                result["message"] = f"Đọc thành công {len(df)} rows với {len(df.columns)} columns"

            return result

        except Exception as e:
            result["message"] = f"Lỗi đọc dữ liệu: {str(e)}"
            result["error"] = str(e)
            return result

    def _preview_data(self, df: pd.DataFrame) -> list:
        """Tạo preview data (max 10 rows)."""
        if df is None or len(df) == 0:
            return []

        preview_df = df.head(10)

        # Chuyển đổi datetime thành string để serialize
        for col in preview_df.columns:
            if hasattr(preview_df[col].dtype, "tz") or "datetime" in str(preview_df[col].dtype):
                preview_df[col] = preview_df[col].astype(str)

        return preview_df.to_dict(orient="records")


class ExportImportService:
    """Service xử lý export/import dữ liệu."""

    # Mapping model_name -> Model class
    MODEL_MAPPING = {
        "datasource": DataSource,
        "thresholdconfig": ThresholdConfig,
        "collection_log": CollectionLog,
        # KPI models 60min (batch/hourly)
        "kpi2g_60min": Kpi2g60min,
        "kpi3g_60min": Kpi3g60min,
        "kpi4g_60min": Kpi4g60min,
        "kpi5g_60min": Kpi5g60min,
        "kpivolte_60min": KpiVolte60min,
        # KPI models 15min (realtime)
        "kpi2g_15min": Kpi2g15min,
        "kpi3g_15min": Kpi3g15min,
        "kpi4g_15min": Kpi4g15min,
        "kpi5g_15min": Kpi5g15min,
        "kpivolte_15min": KpiVolte15min,
    }

    @classmethod
    def get_model(cls, model_name: str):
        """Lấy model class từ model_name."""
        return cls.MODEL_MAPPING.get(model_name.lower())

    @classmethod
    def export_table(
        cls,
        model_name: str,
        filters: dict = None,
        format: str = "json"
    ) -> dict:
        """
        Export dữ liệu ra JSON/CSV.
        Returns: {"success": bool, "data": list/dict, "count": int}
        """
        model = cls.get_model(model_name)
        if not model:
            return {"success": False, "error": f"Model không tồn tại: {model_name}"}

        try:
            queryset = model.objects.all()

            # Apply filters
            if filters:
                queryset = queryset.filter(**filters)

            # Convert to list of dicts
            data = []
            for obj in queryset:
                obj_data = {}
                for field in obj._meta.fields:
                    fname = field.name
                    value = getattr(obj, fname)

                    # Handle special types
                    if hasattr(value, "isoformat"):
                        value = value.isoformat()
                    elif isinstance(value, (dict, list)):
                        value = json.dumps(value)

                    obj_data[fname] = value

                data.append(obj_data)

            if format == "csv":
                # Convert to CSV
                output = io.StringIO()
                if data:
                    writer = csv.DictWriter(output, fieldnames=data[0].keys())
                    writer.writeheader()
                    writer.writerows(data)
                csv_data = output.getvalue()
                return {"success": True, "data": csv_data, "count": len(data), "format": "csv"}

            return {"success": True, "data": data, "count": len(data), "format": "json"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    @classmethod
    def import_data(
        cls,
        model_name: str,
        data: list,
        mode: str = "upsert"
    ) -> dict:
        """
        Import dữ liệu từ JSON.
        mode: upsert (default) | insert | update
        Returns: {"success": bool, "imported": int, "updated": int, "errors": list}
        """
        model = cls.get_model(model_name)
        if not model:
            return {"success": False, "error": f"Model không tồn tại: {model_name}"}

        imported = 0
        updated = 0
        errors = []

        for idx, item in enumerate(data):
            try:
                item_copy = dict(item)

                # Extract _id if exists
                obj_id = item_copy.pop("_id", None)

                if mode == "update" and not obj_id:
                    errors.append(f"Row {idx}: Thiếu _id để update")
                    continue

                if mode == "upsert" and obj_id:
                    # Try to update
                    try:
                        obj = model.objects.get(_id=obj_id)
                        for key, value in item_copy.items():
                            if key != "_id":
                                setattr(obj, key, value)
                        obj.save()
                        updated += 1
                    except model.DoesNotExist:
                        # Insert new
                        model.objects.create(**item_copy)
                        imported += 1

                elif mode == "insert":
                    if "_id" in item_copy:
                        del item_copy["_id"]
                    model.objects.create(**item_copy)
                    imported += 1

                elif mode == "update":
                    obj = model.objects.get(_id=obj_id)
                    for key, value in item_copy.items():
                        if key != "_id":
                            setattr(obj, key, value)
                    obj.save()
                    updated += 1

            except Exception as e:
                errors.append(f"Row {idx}: {str(e)}")

        return {
            "success": len(errors) == 0,
            "imported": imported,
            "updated": updated,
            "errors": errors[:100]  # Limit errors
        }
