"""
Collectors cho data_collector app.
Cung cấp các hàm để đọc dữ liệu từ SFTP/FTP servers.
"""
import io
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import paramiko
from ftplib import FTP

from .models import Source, SourceRealtime


def list_remote_files_with_mtime_sftp(source: Source | SourceRealtime) -> list[tuple]:
    """
    Liệt kê files trên SFTP server với modification time.
    Returns: [(filename, mtime_timestamp), ...]
    """
    try:
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

        files = sftp.listdir_attr(source.data_path)
        result = [
            (f.filename, f.st_mtime)
            for f in files
            if f.filename.startswith(source.data_name or "")
        ]

        sftp.close()
        ssh.close()

        return result

    except Exception as e:
        print(f"Error listing SFTP files: {e}")
        return []


def list_remote_files_with_mtime_ftp(source: Source | SourceRealtime) -> list[tuple]:
    """
    Liệt kê files trên FTP server với modification time.
    Returns: [(filename, mtime_timestamp), ...]
    """
    try:
        ftp = FTP()
        ftp.connect(host=source.ip, port=source.port or 21, timeout=30)
        ftp.login(user=source.data_user, passwd=source.data_pass)
        ftp.cwd(source.data_path)

        files = []
        try:
            for filename in ftp.nlst():
                try:
                    mtime = ftp.sendcmd(f"MDTM {filename}").split(" ")[1]
                    mtime_ts = datetime.strptime(mtime, "%Y%m%d%H%M%S").timestamp()
                    files.append((filename, mtime_ts))
                except Exception:
                    files.append((filename, 0))
        except Exception:
            pass

        ftp.quit()
        return files

    except Exception as e:
        print(f"Error listing FTP files: {e}")
        return []


def read_file_from_sftp(
    source: Source | SourceRealtime,
    file_path: str
) -> pd.DataFrame:
    """
    Đọc file từ SFTP server và trả về DataFrame.
    """
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=source.ip,
            port=source.port or 22,
            username=source.data_user,
            password=source.data_pass,
            timeout=60
        )
        sftp = ssh.open_sftp()

        with sftp.open(file_path) as f:
            if source.data_format and ".csv" in source.data_format.lower():
                df = pd.read_csv(f, sep=";")
            else:
                header_row = int(source.data_header_row or 1) - 1
                sheet_name = source.data_sheet or 0
                df = pd.read_excel(f, header=header_row, sheet_name=sheet_name)

        sftp.close()
        ssh.close()

        return df

    except Exception as e:
        print(f"Error reading SFTP file: {e}")
        return pd.DataFrame()


def read_file_from_ftp(
    source: Source | SourceRealtime,
    file_path: str
) -> pd.DataFrame:
    """
    Đọc file từ FTP server và trả về DataFrame.
    """
    try:
        ftp = FTP()
        ftp.connect(host=source.ip, port=source.port or 21, timeout=60)
        ftp.login(user=source.data_user, passwd=source.data_pass)

        bio = io.BytesIO()
        ftp.retrbinary(f"RETR {file_path}", bio.write)
        bio.seek(0)

        if source.data_format and ".csv" in source.data_format.lower():
            df = pd.read_csv(bio, sep=";")
        else:
            header_row = int(source.data_header_row or 1) - 1
            sheet_name = source.data_sheet or 0
            df = pd.read_excel(bio, header=header_row, sheet_name=sheet_name)

        ftp.quit()

        return df

    except Exception as e:
        print(f"Error reading FTP file: {e}")
        return pd.DataFrame()


def find_matching_file(
    source: Source | SourceRealtime,
    target_datetime: datetime,
    use_file_delay: bool = True
) -> Optional[str]:
    """
    Tìm file phù hợp với datetime pattern.
    Returns: file_path hoặc None
    """
    # Tính datetime cho file
    if use_file_delay:
        file_dt = target_datetime - timedelta(hours=source.data_file_delay or 1)
    else:
        file_dt = target_datetime

    file_pattern = file_dt.strftime(source.datetime_file or "%Y_%m_%d-%H")

    # Lấy danh sách files
    protocol = (source.protocol or "SFTP").upper()

    if protocol == "SFTP":
        files = list_remote_files_with_mtime_sftp(source)
    elif protocol == "FTP":
        files = list_remote_files_with_mtime_ftp(source)
    else:
        return None

    # Tìm file match
    for filename, mtime in files:
        if source.data_name in filename and file_pattern in filename:
            return source.data_path + "/" + filename

    return None


def collect_data_from_source(
    source: Source | SourceRealtime,
    target_datetime: datetime,
    write_to_db: bool = True
) -> dict:
    """
    Thu thập dữ liệu từ một source.
    Returns: {"success": bool, "rows": int, "message": str, "dataframe": pd.DataFrame}
    """
    result = {
        "success": False,
        "rows": 0,
        "message": "",
        "dataframe": None
    }

    try:
        # Tìm file
        file_path = find_matching_file(source, target_datetime)

        if not file_path:
            result["message"] = "Không tìm thấy file phù hợp"
            return result

        # Đọc file
        protocol = (source.protocol or "SFTP").upper()

        if protocol == "SFTP":
            df = read_file_from_sftp(source, file_path)
        elif protocol == "FTP":
            df = read_file_from_ftp(source, file_path)
        else:
            result["message"] = f"Protocol không được hỗ trợ: {protocol}"
            return result

        if df is None or len(df) == 0:
            result["message"] = "File rỗng hoặc không đọc được"
            return result

        result["dataframe"] = df
        result["rows"] = len(df)
        result["success"] = True
        result["message"] = f"Đọc thành công {len(df)} rows"

        # Xử lý data...

        return result

    except Exception as e:
        result["message"] = f"Lỗi: {str(e)}"
        return result


def test_collect(source: Source | SourceRealtime, test_hour: int = None) -> dict:
    """
    Test thu thập dữ liệu (không ghi vào DB).
    Returns: {"success": bool, "rows": int, "file": str, "preview": list}
    """
    result = {
        "success": False,
        "rows": 0,
        "file": None,
        "preview": []
    }

    try:
        # Tính target datetime
        if test_hour is not None:
            now = datetime.now()
            target_dt = now.replace(hour=test_hour, minute=0, second=0, microsecond=0)
        else:
            target_dt = datetime.now()

        # Tìm file
        file_path = find_matching_file(source, target_dt)

        if not file_path:
            result["file"] = None
            result["message"] = "Không tìm thấy file"
            return result

        result["file"] = file_path

        # Đọc file
        protocol = (source.protocol or "SFTP").upper()

        if protocol == "SFTP":
            df = read_file_from_sftp(source, file_path)
        elif protocol == "FTP":
            df = read_file_from_ftp(source, file_path)
        else:
            result["message"] = f"Protocol không được hỗ trợ: {protocol}"
            return result

        if df is None or len(df) == 0:
            result["message"] = "File rỗng"
            return result

        # Preview (max 10 rows)
        preview = df.head(10).to_dict(orient="records")

        result["rows"] = len(df)
        result["preview"] = preview
        result["columns"] = list(df.columns)
        result["success"] = True
        result["message"] = f"Đọc thành công {len(df)} rows"

        return result

    except Exception as e:
        result["message"] = f"Lỗi: {str(e)}"
        return result
