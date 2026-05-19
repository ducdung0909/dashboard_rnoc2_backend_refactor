---
name: python-code-standards
description: >
  Áp dụng chuẩn code Python cho automation/integration platform. Kích hoạt skill này BẮT BUỘC
  khi user yêu cầu viết hoặc review Python code liên quan đến: exception handling, error propagation,
  type hints, dataclass, Pydantic models, logging, observability, tracing, secrets management,
  input validation, API authentication, hoặc bất kỳ câu hỏi nào dạng "code này có an toàn không",
  "handle lỗi thế nào", "log ở đâu", "validate input ra sao", "bảo mật API key".
  Dùng SAU system-architect và flow-orchestrator — đây là lớp quality gate khi implement từng service.
---

# Python Code Standards Skill

## Mục tiêu
Đảm bảo mọi code được sinh ra hoặc review đều tuân thủ 4 tiêu chuẩn:
1. **Exception handling** — lỗi được bắt đúng chỗ, propagate đúng cách
2. **Type safety** — type hints + Pydantic cho tất cả boundary points
3. **Observability** — log có context, traceable từ đầu đến cuối
4. **Security** — không có secret trong code, input được validate trước khi dùng

---

## TIÊU CHUẨN 1 — Exception Handling & Error Propagation

### Nguyên tắc cốt lõi

```
RULE 1: Catch specific, not broad
RULE 2: Errors propagate UP, recovery happens at the RIGHT layer
RULE 3: Always log before re-raise
RULE 4: External calls (DB, API, queue) PHẢI có try/except
RULE 5: Business logic KHÔNG raise raw Exception — dùng custom exceptions
```

### Custom Exception Hierarchy (bắt buộc cho mọi project)

```python
# core/exceptions.py

class AppError(Exception):
    """Base exception cho toàn bộ application."""
    def __init__(self, message: str, code: str = "UNKNOWN", context: dict = None):
        super().__init__(message)
        self.code = code
        self.context = context or {}

# --- Infrastructure errors (layer thấp nhất) ---
class InfrastructureError(AppError):
    """Lỗi từ external systems: DB, queue, cache."""

class DatabaseError(InfrastructureError):
    pass

class ExternalAPIError(InfrastructureError):
    def __init__(self, message: str, status_code: int = None, **kwargs):
        super().__init__(message, **kwargs)
        self.status_code = status_code

class ConnectionError(InfrastructureError):
    pass

# --- Service errors (business logic) ---
class ServiceError(AppError):
    """Lỗi business logic — expected failures."""

class ValidationError(ServiceError):
    pass

class NotFoundError(ServiceError):
    pass

class ConflictError(ServiceError):
    pass

class AuthorizationError(ServiceError):
    pass

# --- Orchestration errors ---
class PipelineError(AppError):
    def __init__(self, message: str, step_name: str = None, **kwargs):
        super().__init__(message, **kwargs)
        self.step_name = step_name
```

### Pattern đúng — Infrastructure Layer

```python
# infrastructure/external_apis/client.py
import httpx
from core.exceptions import ExternalAPIError, ConnectionError

class APIClient:
    async def get(self, url: str, **kwargs) -> dict:
        try:
            response = await self._client.get(url, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            # Wrap external exception thành AppError
            raise ExternalAPIError(
                message=f"API returned {e.response.status_code}: {url}",
                status_code=e.response.status_code,
                code="API_HTTP_ERROR",
                context={"url": url, "status": e.response.status_code}
            ) from e  # LUÔN dùng 'from e' để giữ traceback gốc
        except httpx.ConnectError as e:
            raise ConnectionError(
                message=f"Cannot connect to {url}",
                code="CONNECTION_FAILED",
                context={"url": url}
            ) from e
```

### Pattern đúng — Service Layer

```python
# services/integration/sync_service.py
from core.exceptions import ExternalAPIError, ValidationError, ServiceError
import logging

logger = logging.getLogger(__name__)

class SyncService:
    async def sync_data(self, source_id: str) -> SyncResult:
        # Validate trước khi làm bất cứ điều gì
        if not source_id or not source_id.strip():
            raise ValidationError(
                "source_id cannot be empty",
                code="INVALID_SOURCE_ID",
                context={"source_id": source_id}
            )

        try:
            raw_data = await self._api_client.get(f"/sources/{source_id}")
        except ExternalAPIError as e:
            if e.status_code == 404:
                raise NotFoundError(
                    f"Source {source_id} not found",
                    code="SOURCE_NOT_FOUND",
                    context={"source_id": source_id}
                ) from e
            # Lỗi khác: log và re-raise (để pipeline xử lý retry)
            logger.warning("API error during sync", extra={
                "source_id": source_id,
                "error_code": e.code,
                "status_code": e.status_code
            })
            raise  # Re-raise nguyên gốc, KHÔNG wrap thêm
```

### Pattern đúng — Orchestrator / Pipeline Layer

```python
# orchestrator/pipeline.py — error handling trong pipeline runner
async def _execute_with_retry(self, step, ctx):
    last_error = None
    for attempt in range(step.retry_count + 1):
        try:
            return await step.handler(ctx)
        except ValidationError:
            # Validation errors: KHÔNG retry — data sai thì retry cũng vô nghĩa
            raise
        except (ExternalAPIError, ConnectionError) as e:
            last_error = e
            if attempt < step.retry_count:
                wait = step.retry_delay * (2 ** attempt)  # Exponential backoff
                logger.warning(f"Step {step.name} failed (attempt {attempt+1}), retry in {wait}s",
                    extra={"step": step.name, "attempt": attempt + 1, "error": str(e)})
                await asyncio.sleep(wait)
        except AppError:
            raise  # Business errors: không retry
        except Exception as e:
            # Unexpected error — wrap để không leak internal details
            raise PipelineError(
                f"Unexpected error in step {step.name}",
                step_name=step.name,
                code="PIPELINE_UNEXPECTED_ERROR"
            ) from e
    raise last_error
```

### Presentation Layer (FastAPI)

```python
# routes/api.py — xử lý exception thành HTTP response đúng cách
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    return JSONResponse(status_code=422, content={
        "error": exc.code,
        "message": str(exc),
        # KHÔNG expose exc.context ra ngoài — có thể chứa internal data
    })

@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError):
    return JSONResponse(status_code=404, content={
        "error": exc.code, "message": str(exc)
    })

@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    logger.error("Unhandled AppError", extra={"code": exc.code, "context": exc.context})
    return JSONResponse(status_code=500, content={
        "error": exc.code, "message": "Internal error"  # KHÔNG expose context
    })
```

---

## TIÊU CHUẨN 2 — Type Hints & Pydantic

### Nguyên tắc cốt lõi

```
RULE 1: Tất cả function signatures PHẢI có type hints (params + return type)
RULE 2: Pydantic cho MỌI data đến từ bên ngoài (API request, DB row, config)
RULE 3: Dataclass cho internal domain objects (không cần validation)
RULE 4: TypedDict cho dict structures tạm thời
RULE 5: Optional[X] thay vì X = None, Union thay vì Any
```

### Pydantic — External Boundary Models

```python
# core/models/external.py
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional
from datetime import datetime
from enum import Enum

class IntegrationStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"

class APIWebhookPayload(BaseModel):
    """Model cho incoming webhook — validate TRƯỚC khi dùng."""
    event_type: str = Field(..., min_length=1, max_length=100)
    source_id: str = Field(..., pattern=r"^[a-zA-Z0-9_-]+$")
    timestamp: datetime
    data: dict
    status: IntegrationStatus = IntegrationStatus.ACTIVE

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        allowed = {"created", "updated", "deleted", "triggered"}
        if v not in allowed:
            raise ValueError(f"event_type must be one of {allowed}")
        return v

    @model_validator(mode="after")
    def validate_data_not_empty(self) -> "APIWebhookPayload":
        if not self.data:
            raise ValueError("data payload cannot be empty")
        return self

class SyncConfig(BaseModel):
    """Config từ environment — validate khi startup."""
    api_base_url: str = Field(..., pattern=r"^https?://")
    batch_size: int = Field(default=100, ge=1, le=1000)
    timeout_seconds: float = Field(default=30.0, gt=0)
    retry_count: int = Field(default=3, ge=0, le=10)

    class Config:
        frozen = True  # Config không được thay đổi sau khi load
```

### Dataclass — Internal Domain Objects

```python
# core/models/domain.py
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime

@dataclass
class SyncResult:
    """Kết quả của một sync operation — internal use only."""
    run_id: str
    source_id: str
    records_processed: int
    records_failed: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    errors: List[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.records_processed == 0:
            return 0.0
        return (self.records_processed - self.records_failed) / self.records_processed

    @property
    def is_successful(self) -> bool:
        return self.records_failed == 0 and self.completed_at is not None
```

### Service Function Signatures — Chuẩn bắt buộc

```python
# ĐÚNG — đầy đủ type hints
async def process_webhook(
    payload: APIWebhookPayload,
    config: SyncConfig,
    *,  # keyword-only args sau đây
    dry_run: bool = False,
) -> SyncResult:
    ...

# SAI — thiếu type hints
async def process_webhook(payload, config, dry_run=False):
    ...

# SAI — dùng Any
from typing import Any
async def process_webhook(payload: Any) -> Any:
    ...
```

---

## TIÊU CHUẨN 3 — Logging & Observability

### Nguyên tắc cốt lõi

```
RULE 1: Mỗi module có logger riêng: logger = logging.getLogger(__name__)
RULE 2: Log có CONTEXT — không log string thuần, dùng 'extra' dict
RULE 3: Mỗi request/pipeline run có correlation_id duy nhất
RULE 4: KHÔNG log sensitive data (password, token, PII)
RULE 5: Log level đúng: DEBUG=dev detail, INFO=business events, WARNING=recoverable, ERROR=needs attention
```

### Setup Logging chuẩn

```python
# config/logging.py
import logging
import json
from datetime import datetime, timezone

class JSONFormatter(logging.Formatter):
    """Structured JSON logs — dễ query trong Datadog/CloudWatch."""
    SENSITIVE_KEYS = {"password", "token", "secret", "api_key", "authorization"}

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Thêm extra context nếu có, filter sensitive keys
        if hasattr(record, "__dict__"):
            for key, val in record.__dict__.items():
                if key not in logging.LogRecord.__dict__ and \
                   key.lower() not in self.SENSITIVE_KEYS:
                    log_data[key] = val
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data, default=str)

def setup_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logging.basicConfig(level=level, handlers=[handler], force=True)
```

### Correlation ID — Request Tracing

```python
# core/context.py
import contextvars
import uuid

# Context variable — tự động propagate qua async calls
correlation_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default="no-correlation-id"
)

def get_correlation_id() -> str:
    return correlation_id.get()

def set_correlation_id(cid: str | None = None) -> str:
    cid = cid or str(uuid.uuid4())
    correlation_id.set(cid)
    return cid

# Middleware FastAPI — inject vào mỗi request
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class CorrelationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        cid = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        set_correlation_id(cid)
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = cid
        return response
```

### Logging Pattern trong Services

```python
# services/integration/sync_service.py
import logging
from core.context import get_correlation_id

logger = logging.getLogger(__name__)

class SyncService:
    async def sync_data(self, source_id: str) -> SyncResult:
        cid = get_correlation_id()

        logger.info("Sync started", extra={
            "correlation_id": cid,
            "source_id": source_id,
            "action": "sync.start"
        })

        try:
            result = await self._do_sync(source_id)

            logger.info("Sync completed", extra={
                "correlation_id": cid,
                "source_id": source_id,
                "action": "sync.complete",
                "records_processed": result.records_processed,
                "success_rate": round(result.success_rate, 3)
                # KHÔNG log: raw data, API responses, tokens
            })
            return result

        except AppError as e:
            logger.error("Sync failed", extra={
                "correlation_id": cid,
                "source_id": source_id,
                "action": "sync.failed",
                "error_code": e.code,
                # KHÔNG log: e.context (có thể chứa sensitive data)
            })
            raise
```

---

## TIÊU CHUẨN 4 — Security

### Nguyên tắc cốt lõi

```
RULE 1: KHÔNG bao giờ hardcode secret trong code hoặc commit lên git
RULE 2: Tất cả input từ bên ngoài phải qua Pydantic validation trước khi dùng
RULE 3: API keys/tokens KHÔNG được log, KHÔNG được include trong error messages
RULE 4: Mọi external API call phải authenticate — không có unauthenticated calls
RULE 5: Timeout bắt buộc cho tất cả network calls
```

### Secrets Management

```python
# config/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr

class Settings(BaseSettings):
    """Load từ environment variables hoặc .env file.
    SecretStr tự động mask khi log/print.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # API credentials — dùng SecretStr để mask khi log
    api_key: SecretStr = Field(..., description="External API key")
    db_password: SecretStr = Field(..., description="Database password")
    webhook_secret: SecretStr = Field(..., description="Webhook signing secret")

    # Non-sensitive config
    api_base_url: str = Field(..., pattern=r"^https://")  # Chỉ chấp nhận HTTPS
    db_host: str
    db_port: int = Field(default=5432, ge=1, le=65535)
    environment: str = Field(default="development",
                             pattern=r"^(development|staging|production)$")

    def get_api_key(self) -> str:
        """Expose secret value chỉ khi cần thiết, không cache."""
        return self.api_key.get_secret_value()

# Singleton — load một lần khi startup
_settings: Settings | None = None

def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
```

### Input Validation — Defense in Depth

```python
# Tầng 1: Pydantic model (type + format validation)
class CreateIntegrationRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255,
                      pattern=r"^[a-zA-Z0-9 _-]+$")  # Whitelist chars
    webhook_url: str = Field(..., pattern=r"^https://")   # HTTPS only
    events: list[str] = Field(..., min_length=1, max_length=10)

# Tầng 2: Business validation trong service
class IntegrationService:
    ALLOWED_EVENTS = {"created", "updated", "deleted"}

    async def create(self, request: CreateIntegrationRequest) -> Integration:
        # Validate business rules sau khi Pydantic đã pass
        invalid_events = set(request.events) - self.ALLOWED_EVENTS
        if invalid_events:
            raise ValidationError(
                f"Invalid events: {invalid_events}",
                code="INVALID_EVENTS",
                context={"invalid": list(invalid_events)}
            )
        # Tiếp tục xử lý...
```

### Webhook Signature Verification

```python
# infrastructure/security/webhook_verifier.py
import hmac
import hashlib
import time
from core.exceptions import AuthorizationError

class WebhookVerifier:
    MAX_TIMESTAMP_DRIFT_SECONDS = 300  # 5 phút

    def __init__(self, secret: str):
        self._secret = secret.encode()

    def verify(self, payload: bytes, signature: str, timestamp: str) -> None:
        """Verify webhook signature — raise AuthorizationError nếu invalid."""
        # 1. Check timestamp để chống replay attack
        try:
            ts = int(timestamp)
        except ValueError:
            raise AuthorizationError("Invalid timestamp", code="INVALID_TIMESTAMP")

        if abs(time.time() - ts) > self.MAX_TIMESTAMP_DRIFT_SECONDS:
            raise AuthorizationError("Timestamp too old", code="TIMESTAMP_EXPIRED")

        # 2. Compute expected signature
        message = f"{timestamp}.{payload.decode()}".encode()
        expected = hmac.new(self._secret, message, hashlib.sha256).hexdigest()

        # 3. Constant-time comparison — chống timing attack
        if not hmac.compare_digest(f"sha256={expected}", signature):
            raise AuthorizationError("Invalid signature", code="INVALID_SIGNATURE")
```

### HTTP Client với Security Defaults

```python
# infrastructure/external_apis/base_client.py
import httpx
from config.settings import get_settings

def create_secure_http_client() -> httpx.AsyncClient:
    """Client với security defaults bắt buộc."""
    settings = get_settings()
    return httpx.AsyncClient(
        base_url=settings.api_base_url,
        timeout=httpx.Timeout(
            connect=5.0,   # Connection timeout
            read=30.0,     # Read timeout
            write=10.0,    # Write timeout
            pool=5.0       # Pool timeout
        ),
        headers={
            "Authorization": f"Bearer {settings.get_api_key()}",
            "User-Agent": "MyPlatform/1.0",
        },
        verify=True,        # SSL verification LUÔN bật
        follow_redirects=False,  # Không follow redirects tự động
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10)
    )
```

---

## CHECKLIST — Review Code trước khi commit

```
EXCEPTION HANDLING:
  [ ] Không có bare `except:` hoặc `except Exception:` ở infrastructure layer
  [ ] Tất cả external calls có try/except với custom exception
  [ ] Re-raise dùng `raise ... from e` (giữ traceback)
  [ ] Presentation layer có exception handler cho từng AppError subclass

TYPE SAFETY:
  [ ] Tất cả function có type hints (params + return)
  [ ] Data từ external source đi qua Pydantic model
  [ ] Không có `Any` type trừ khi có lý do rõ ràng

LOGGING:
  [ ] Mỗi module có `logger = logging.getLogger(__name__)`
  [ ] Log dùng `extra={}` dict, không dùng f-string thuần
  [ ] correlation_id có mặt trong mọi log entry của request
  [ ] Không có token/password/secret trong log messages

SECURITY:
  [ ] Không có hardcoded credentials
  [ ] Tất cả secrets dùng SecretStr hoặc environment variable
  [ ] HTTP client có timeout
  [ ] Webhook có signature verification
  [ ] Input validation qua Pydantic trước khi dùng
```

---

## Cách tích hợp với 2 skills còn lại

```
system-architect   → định nghĩa INTERFACES (abstract base classes)
flow-orchestrator  → định nghĩa ERROR PROPAGATION giữa pipeline steps
python-code-standards → implement TỪNG SERVICE theo 4 tiêu chuẩn trên
```

Khi implement một service mới, chạy checklist bên trên trước khi báo "done".
