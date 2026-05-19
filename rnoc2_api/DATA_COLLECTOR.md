# Data Collector App - Hướng Dẫn Sử Dụng

## Giới Thiệu

App `data_collector` là module thống nhất để quản lý việc thu thập dữ liệu KPI từ các nguồn SFTP/FTP, hỗ trợ CRUD cho cấu hình nguồn dữ liệu, test collect với ghi log chi tiết, và export/import dữ liệu.

## Cài Đặt

### 1. Tạo Database Tables

```bash
cd d:/Code/CDS_NOC2/dashboard_rnoc2_backend_refactor/rnoc2_api
python manage.py makemigrations data_collector
python manage.py migrate
```

### 2. Chạy Development Server

```bash
python manage.py runserver
```

Truy cập: http://localhost:8000/data-collector/

## Cấu Trúc URL

### Web UI

| URL | Mô tả |
|-----|--------|
| `/data-collector/` | Trang chủ - Danh sách Data Sources |
| `/data-collector/sources/` | Danh sách Data Sources |
| `/data-collector/sources/add/` | Thêm Data Source mới |
| `/data-collector/sources/{id}/edit/` | Sửa Data Source |
| `/data-collector/sources/{id}/delete/` | Xóa Data Source |
| `/data-collector/sources-realtime/` | Danh sách Realtime Sources |
| `/data-collector/sources-realtime/add/` | Thêm Realtime Source |
| `/data-collector/test-collect/` | Test Collect (quan trọng) |
| `/data-collector/export-import/` | Export/Import dữ liệu |
| `/data-collector/collection-logs/` | Lịch sử Collection Logs |
| `/data-collector/collection-logs/{id}/` | Chi tiết Collection Log |

### API Endpoints

| Method | URL | Mô tả |
|--------|-----|--------|
| GET | `/data-collector/api/sources/` | List all sources |
| POST | `/data-collector/api/sources/` | Create source |
| GET | `/data-collector/api/sources/{id}/` | Get source detail |
| PUT | `/data-collector/api/sources/{id}/` | Update source |
| DELETE | `/data-collector/api/sources/{id}/` | Delete source |
| GET | `/data-collector/api/sources-realtime/` | List realtime sources |
| POST | `/data-collector/api/test-connection/` | Test SFTP/FTP connection |
| POST | `/data-collector/api/test-collect/` | Run test collect với ghi log |
| GET | `/data-collector/api/export/{model}/` | Export table ra JSON/CSV |
| POST | `/data-collector/api/import/{model}/` | Import JSON vào table |

## Các Tính Năng

### 1. Quản Lý Data Sources (Batch)

Dùng để thu thập dữ liệu theo giờ (hourly batch).

**Các trường quan trọng:**
- `vendor`: Huawei, Ericsson, Nokia, ZTE
- `system`: 2G, 3G, 4G, 5G, VoLTE
- `protocol`: SFTP, FTP
- `ip`, `port`, `data_user`, `data_pass`: Thông tin kết nối
- `data_path`, `data_name`: Đường dẫn và tên file pattern
- `datetime_file`: Format thời gian trong tên file (VD: `%Y_%m_%d-%H`)
- `data_header_name`: JSON mapping cột (VD: `{"Original_Col": ["kpi", "cs_3g_cssr"]}`)

### 2. Quản Lý Realtime Sources

Dùng để thu thập dữ liệu theo chu kỳ 15/30/60 phút.

**Các trường quan trọng:**
- `cycle_minutes`: 15, 30, hoặc 60 phút
- `datetime_file`: Format thời gian (VD: `%Y%m%d%H%M`)

### 3. Test Collect (Tính năng quan trọng)

**Mục đích:** Kiểm tra việc thu thập dữ liệu từ một source bất kỳ, ghi lại chi tiết từng bước.

**Cách sử dụng:**
1. Truy cập `/data-collector/test-collect/`
2. Chọn source từ dropdown
3. Chọn ngày và giờ để test (hoặc để trống để test với thời gian hiện tại)
4. Click "Run Test Collect"

**Các bước được ghi log:**
1. **Validate Source** - Kiểm tra source tồn tại
2. **Test Connection** - Kết nối SFTP/FTP
3. **Find Files** - Tìm file theo pattern thời gian
4. **Read Data** - Đọc dữ liệu từ file
5. **Preview Data** - Xem trước dữ liệu
6. **Write Database** - Ghi vào database (test mode)

**Xem chi tiết log:**
- Truy cập `/data-collector/collection-logs/` để xem danh sách
- Click vào log để xem chi tiết từng bước và data preview

### 4. Export/Import Dữ Liệu

**Export:**
1. Truy cập `/data-collector/export-import/`
2. Chọn table và format (JSON/CSV)
3. Click Export

**Import:**
1. Chọn table đích
2. Chọn mode (Upsert/Insert/Update)
3. Dán JSON array hoặc upload file
4. Click Import

**Supported models cho export:**
- `source`, `sourcerealtime`, `threshold`, `threshold_realtime`
- `collection_log`
- KPI tables: `kpi2g`, `kpi3g`, `kpi4g`, `kpi5g`, `kpivolte`

## Models

### Source
```python
- _id, active, vendor, system, oss
- protocol, ip, port, level
- data_user, data_pass, data_path, data_name
- data_sheet, data_format, data_header_name (JSON)
- data_file_delay, data_kpi_delay
- datetime_file, datetime_kpi
```

### SourceRealtime
```python
- _id, vendor, system, protocol, ip, port
- data_user, data_pass, data_path, data_name
- datetime_file, data_format, data_sheet
- data_header_row, data_header_name, data_skiprows
- cycle_minutes, level, active
- last_fetch_time, last_file_name
```

### CollectionLog
```python
- _id, source_type, source_id, source_name
- test_datetime, status, steps (JSON - chi tiết từng bước)
- data_preview (JSON - preview dữ liệu)
- rows_fetched, rows_written
- error_message, execution_time
- test_hour, test_date
```

## Celery Tasks

```python
collect_all_sources()           # Thu thập tất cả sources
collect_sources_by_system()     # Theo system (2G, 3G, 4G, 5G)
collect_realtime_sources()      # Theo chu kỳ (15, 30, 60 phút)
collect_single_source()          # Một source cụ thể
collect_batch_sources()         # Nhiều sources cụ thể
```

## Ví Dụ Sử Dụng API

### Test Connection
```bash
curl -X POST http://localhost:8000/data-collector/api/test-connection/ \
  -H "Content-Type: application/json" \
  -d '{"source_type": "source", "source_id": 1}'
```

### Run Test Collect
```bash
curl -X POST http://localhost:8000/data-collector/api/test-collect/ \
  -H "Content-Type: application/json" \
  -d '{"source_type": "source", "source_id": 1, "test_hour": 10}'
```

### Export Data
```bash
curl -O http://localhost:8000/data-collector/api/export/source/
```

## Database Tables

| Table Name | Mô tả |
|------------|--------|
| `data_collector_source` | Cấu hình batch data sources |
| `data_collector_source_realtime` | Cấu hình realtime sources |
| `data_collector_threshold` | Ngưỡng cảnh báo batch |
| `data_collector_threshold_realtime` | Ngưỡng cảnh báo realtime |
| `data_collector_collection_log` | Logs test collect |

## Notes

- App sử dụng Bootstrap 5 cho giao diện
- DataTables được sử dụng cho các bảng lớn
- Tất cả JSON fields được hỗ trợ đầy đủ
- Logs được lưu trong database để debug
