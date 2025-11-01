from __future__ import annotations

import asyncio
import json
import logging
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from datetime import timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from fastapi import Depends
from fastapi import FastAPI
from fastapi import File
from fastapi import Form
from fastapi import HTTPException
from fastapi import UploadFile
from fastapi import status
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import subprocess
import shutil
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import ValidationError

from pdf2zh_next import __version__
from pdf2zh_next.auth import GUEST_USER
from pdf2zh_next.auth import InvalidCredentialsError
from pdf2zh_next.auth import User
from pdf2zh_next.auth import UserExistsError
from pdf2zh_next.auth import authenticate_user
from pdf2zh_next.auth import get_current_user
from pdf2zh_next.auth import get_optional_user
from pdf2zh_next.auth import get_user_or_guest
from pdf2zh_next.auth import register_user
from pdf2zh_next.config.cli_env_model import CLIEnvSettingsModel
from pdf2zh_next.config.main import ConfigManager
from pdf2zh_next.config.model import SettingsModel
from pdf2zh_next.db import get_connection
from pdf2zh_next.high_level import TranslationError
from pdf2zh_next.high_level import do_translate_async_stream

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"


class ResultMode(str, Enum):
    mono = "mono"
    dual = "dual"
    original = "original"


@dataclass
class TaskRecord:
    """Internal task representation."""

    id: str
    owner: str
    filename: str
    input_path: Path
    output_dir: Path
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    retention_days: int | None = None
    progress: float = 0.0
    message: str | None = None
    result: dict[str, Any] | None = None
    events: list[dict[str, Any]] = field(default_factory=list)


class TaskResultModel(BaseModel):
    original_pdf: str | None = None
    mono_pdf: str | None = None
    dual_pdf: str | None = None
    output_dir: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TaskSummaryModel(BaseModel):
    id: str
    filename: str
    status: TaskStatus
    progress: float
    message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaskDetailModel(TaskSummaryModel):
    events: list[dict[str, Any]] = Field(default_factory=list)
    result: TaskResultModel | None = None


class UserProfileModel(BaseModel):
    username: str
    display_name: str | None = None
    retention_days: int | None = None

    model_config = ConfigDict(from_attributes=True)


class AuthRequestModel(BaseModel):
    username: str
    password: str


class AuthResponseModel(BaseModel):
    token: str
    profile: UserProfileModel


def _profile_from_user(user: User) -> UserProfileModel:
    return UserProfileModel(
        username=user.username,
        display_name=user.display_name,
        retention_days=user.retention_days,
    )


def _is_expired(record: TaskRecord) -> bool:
    if record.retention_days is None:
        return False
    return datetime.utcnow() - record.created_at > timedelta(days=record.retention_days)


class TaskStorage:
    """SQLite-backed persistent task storage."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()

    def _row_to_record(self, row) -> TaskRecord:
        created_at = datetime.fromisoformat(row["created_at"])
        updated_at = datetime.fromisoformat(row["updated_at"])
        events = json.loads(row["events_json"]) if row["events_json"] else []
        result = json.loads(row["result_json"]) if row["result_json"] else None
        return TaskRecord(
            id=row["id"],
            owner=row["owner"],
            filename=row["filename"],
            input_path=Path(row["input_path"]),
            output_dir=Path(row["output_dir"]),
            status=TaskStatus(row["status"]),
            created_at=created_at,
            updated_at=updated_at,
            retention_days=row["retention_days"],
            progress=row["progress"] or 0.0,
            message=row["message"],
            result=result,
            events=events,
        )

    async def create(self, record: TaskRecord) -> TaskRecord:
        async with self._lock:
            with get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO tasks (
                        id, owner, filename, input_path, output_dir, status,
                        created_at, updated_at, retention_days, progress,
                        message, result_json, events_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.id,
                        record.owner,
                        record.filename,
                        str(record.input_path),
                        str(record.output_dir),
                        record.status.value,
                        record.created_at.isoformat(),
                        record.updated_at.isoformat(),
                        record.retention_days,
                        record.progress,
                        record.message,
                        json.dumps(record.result) if record.result else None,
                        json.dumps(record.events),
                    ),
                )
                conn.commit()
        return record

    async def _fetch(self, task_id: str) -> TaskRecord:
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not row:
            raise KeyError(task_id)
        record = self._row_to_record(row)
        if _is_expired(record):
            await self.delete(task_id)
            raise KeyError(task_id)
        return record

    async def get(self, task_id: str) -> TaskRecord:
        async with self._lock:
            return await self._fetch(task_id)

    async def list(self, owner: str, limit: int = 20) -> list[TaskRecord]:
        async with self._lock:
            with get_connection() as conn:
                rows = conn.execute(
                    "SELECT * FROM tasks WHERE owner = ? ORDER BY created_at DESC",
                    (owner,),
                ).fetchall()
        records: list[TaskRecord] = []
        for row in rows:
            record = self._row_to_record(row)
            if _is_expired(record):
                await self.delete(record.id)
                continue
            records.append(record)
            if len(records) >= limit:
                break
        return records

    async def update(self, task_id: str, **kwargs: Any) -> TaskRecord:
        async with self._lock:
            fields: dict[str, Any] = {}
            for key, value in kwargs.items():
                if key == "status" and isinstance(value, TaskStatus):
                    fields["status"] = value.value
                elif key == "progress":
                    fields["progress"] = float(value)
                elif key == "message":
                    fields["message"] = value
                elif key == "result":
                    fields["result_json"] = json.dumps(value) if value is not None else None
                elif key == "retention_days":
                    fields["retention_days"] = value
            if not fields:
                return await self._fetch(task_id)
            fields["updated_at"] = datetime.utcnow().isoformat()
            columns = ", ".join(f"{column} = ?" for column in fields)
            values = list(fields.values()) + [task_id]
            with get_connection() as conn:
                conn.execute(f"UPDATE tasks SET {columns} WHERE id = ?", values)
                conn.commit()
            return await self._fetch(task_id)

    async def append_event(self, task_id: str, event: dict[str, Any]) -> None:
        sanitized = event
        async with self._lock:
            with get_connection() as conn:
                row = conn.execute(
                    "SELECT events_json FROM tasks WHERE id = ?",
                    (task_id,),
                ).fetchone()
                if not row:
                    raise KeyError(task_id)
                events = json.loads(row["events_json"]) if row["events_json"] else []
                events.append(sanitized)
                conn.execute(
                    "UPDATE tasks SET events_json = ?, updated_at = ? WHERE id = ?",
                    (json.dumps(events), datetime.utcnow().isoformat(), task_id),
                )
                conn.commit()

    async def delete(self, task_id: str) -> None:
        async with self._lock:
            with get_connection() as conn:
                conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
                conn.commit()


class InvalidConfigError(Exception):
    """Raised when user supplied overrides fail validation."""


def _jsonify(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _jsonify(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonify(v) for v in value]
    return str(value)


def _extract_result(result: Any) -> dict[str, str | None] | None:
    if result is None:
        return None
    try:
        return {
            "original_pdf": (
                str(getattr(result, "original_pdf_path"))
                if getattr(result, "original_pdf_path", None)
                else None
            ),
            "mono_pdf": (
                str(getattr(result, "mono_pdf_path"))
                if getattr(result, "mono_pdf_path", None)
                else None
            ),
            "dual_pdf": (
                str(getattr(result, "dual_pdf_path"))
                if getattr(result, "dual_pdf_path", None)
                else None
            ),
            "output_dir": (
                str(getattr(result, "output_dir"))
                if getattr(result, "output_dir", None)
                else None
            ),
        }
    except Exception:  # pragma: no cover - defensive fallback
        logger.debug("Unable to extract translate_result payload", exc_info=True)
        return None


def _sanitize_event(event: dict[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in event.items():
        if key == "translate_result":
            sanitized[key] = _extract_result(value)
        else:
            sanitized[key] = _jsonify(value)
    return sanitized


class TranslationService:
    """Submit translation jobs and bridge to BabelDOC pipeline."""

    def __init__(self, storage: TaskStorage, workspace: Path) -> None:
        self._storage = storage
        self._workspace = workspace
        self._config_manager = ConfigManager()
        self._workspace.mkdir(parents=True, exist_ok=True)

    async def submit(
        self, upload: UploadFile, overrides: dict[str, Any], user: User
    ) -> TaskRecord:
        task_id = uuid.uuid4().hex
        safe_name = Path(upload.filename or f"{task_id}.pdf").name
        if not safe_name.lower().endswith(".pdf"):
            safe_name += ".pdf"

        task_dir = self._workspace / task_id
        input_dir = task_dir / "input"
        output_dir = task_dir / "output"
        input_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)

        input_path = input_dir / safe_name
        await self._save_upload(upload, input_path)

        record = TaskRecord(
            id=task_id,
            owner=user.username,
            retention_days=user.retention_days,
            filename=safe_name,
            input_path=input_path,
            output_dir=output_dir,
            status=TaskStatus.PENDING,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        await self._storage.create(record)

        try:
            settings = self._build_settings(overrides, output_dir)
        except InvalidConfigError as exc:  # validation error
            await self._storage.update(
                task_id,
                status=TaskStatus.FAILED,
                message=str(exc),
            )
            raise

        asyncio.create_task(self._run_task(task_id, settings, input_path))
        return record

    async def _save_upload(self, upload: UploadFile, target: Path) -> None:
        with target.open("wb") as buffer:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                buffer.write(chunk)
        await upload.seek(0)

    def _build_settings(
        self, overrides: dict[str, Any], output_dir: Path
    ) -> SettingsModel:
        base_cli = CLIEnvSettingsModel()
        base_dict = base_cli.model_dump(mode="python")
        merged_dict = base_dict
        if overrides:
            if not isinstance(overrides, dict):
                raise InvalidConfigError("config must be a JSON object")
            merged_dict = self._config_manager.merge_settings([overrides, base_dict])
        try:
            cli_model = self._config_manager._build_model_from_args(
                CLIEnvSettingsModel, merged_dict
            )
        except ValidationError as exc:
            raise InvalidConfigError(exc.errors()) from exc
        settings = cli_model.to_settings_model()
        settings.basic.gui = False
        settings.basic.debug = False
        settings.translation.output = str(output_dir)
        return settings

    async def _run_task(
        self, task_id: str, settings, input_path: Path
    ) -> None:  # pragma: no cover - background task
        await self._storage.update(task_id, status=TaskStatus.RUNNING)
        try:
            async for event in do_translate_async_stream(settings, input_path):
                sanitized = _sanitize_event(event)
                await self._storage.append_event(task_id, sanitized)

                if isinstance(event.get("progress"), (int, float)):
                    await self._storage.update(
                        task_id, progress=float(event["progress"])
                    )

                event_type = event.get("type")
                if event_type == "finish":
                    result_data = _extract_result(event.get("translate_result"))
                    # Optional: linearize PDFs for faster web view
                    try:
                        if settings.pdf.linearize_output and result_data:
                            for key in ("mono_pdf", "dual_pdf", "original_pdf"):
                                pdf_path = result_data.get(key)
                                if not pdf_path:
                                    continue
                                _try_linearize_pdf(Path(pdf_path))
                    except Exception:
                        logger.debug("linearize step skipped", exc_info=True)
                    # Ensure output_dir is always available to the client
                    try:
                        output_dir_value = settings.translation.output
                        if isinstance(output_dir_value, Path):
                            output_dir_value = str(output_dir_value)
                    except Exception:
                        output_dir_value = None
                    if isinstance(result_data, dict) and output_dir_value:
                        result_data.setdefault("output_dir", output_dir_value)
                    elif output_dir_value:
                        result_data = {"output_dir": output_dir_value}
                    await self._storage.update(
                        task_id,
                        status=TaskStatus.DONE,
                        progress=1.0,
                        message="Completed",
                        result=result_data,
                    )
                    return
                if event_type == "error":
                    message = str(event.get("error", "Translation failed"))
                    await self._storage.update(
                        task_id,
                        status=TaskStatus.FAILED,
                        message=message,
                    )
                    return

            # fallback when stream ends without finish event
            await self._storage.update(
                task_id,
                status=TaskStatus.DONE,
                progress=1.0,
                message="Completed",
            )
        except TranslationError as exc:
            logger.error("Translation error for task %s: %s", task_id, exc)
            await self._storage.update(
                task_id, status=TaskStatus.FAILED, message=str(exc)
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.exception("Unexpected error running task %s", task_id)
            await self._storage.update(
                task_id, status=TaskStatus.FAILED, message=str(exc)
            )


def _parse_config(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid config JSON: {exc.msg}",
        ) from exc
    if not isinstance(parsed, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="config must be a JSON object",
        )
    return parsed


def _serialize_summary(record: TaskRecord) -> TaskSummaryModel:
    return TaskSummaryModel.model_validate(record)


def _serialize_detail(record: TaskRecord) -> TaskDetailModel:
    detail = TaskDetailModel.model_validate(record)
    if record.result:
        result_data = dict(record.result)
        # Backfill output_dir for older records that don't have it in result
        if not result_data.get("output_dir"):
            result_data["output_dir"] = str(record.output_dir)
        detail.result = TaskResultModel.model_validate(result_data)
    return detail


TASK_WORKSPACE = Path(tempfile.gettempdir()) / "pdfmathtranslate-api-tasks"
storage = TaskStorage()
service = TranslationService(storage=storage, workspace=TASK_WORKSPACE)

app = FastAPI(
    title="PDFMathTranslate API",
    version=__version__,
    description="HTTP API wrapper for PDFMathTranslate translation pipeline.",
)

# Enable CORS (configurable via env P2Z_CORS_ORIGINS, comma-separated). Defaults to allow all.
origins_env = os.environ.get("P2Z_CORS_ORIGINS")
if origins_env:
    allowed_origins = [o.strip() for o in origins_env.split(",") if o.strip()]
else:
    allowed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)


# Optional linearization (Fast Web View) helpers
def _try_linearize_pdf(path: Path) -> None:
    if not path or not path.exists():
        return
    # Try pikepdf first
    try:
        import pikepdf  # type: ignore

        tmp_path = path.with_suffix(path.suffix + ".lin.pdf")
        with pikepdf.open(str(path)) as pdf:
            pdf.save(str(tmp_path), linearize=True)
        tmp_path.replace(path)
        logger.info("Linearized PDF via pikepdf: %s", path)
        return
    except Exception:
        logger.debug("pikepdf not available or failed; will try qpdf if present", exc_info=True)

    # Fallback to qpdf CLI if available
    if shutil.which("qpdf"):
        try:
            tmp_path = path.with_suffix(path.suffix + ".lin.pdf")
            subprocess.run(["qpdf", "--linearize", str(path), str(tmp_path)], check=True)
            tmp_path.replace(path)
            logger.info("Linearized PDF via qpdf: %s", path)
        except Exception:
            logger.debug("qpdf linearize failed", exc_info=True)


@app.post(
    "/api/auth/register",
    response_model=AuthResponseModel,
    status_code=status.HTTP_201_CREATED,
)
async def register_endpoint(payload: AuthRequestModel) -> AuthResponseModel:
    username = payload.username.strip()
    if len(username) < 3:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名至少 3 个字符")
    if len(payload.password) < 6:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="密码至少 6 个字符")
    try:
        user, token = register_user(username, payload.password)
    except UserExistsError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名已存在") from exc
    return AuthResponseModel(token=token, profile=_profile_from_user(user))


@app.post("/api/auth/login", response_model=AuthResponseModel)
async def login_endpoint(payload: AuthRequestModel) -> AuthResponseModel:
    try:
        user, token = authenticate_user(payload.username, payload.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误") from exc
    return AuthResponseModel(token=token, profile=_profile_from_user(user))


@app.post(
    "/api/tasks",
    response_model=TaskDetailModel,
    status_code=status.HTTP_201_CREATED,
)
async def create_task(
    file: UploadFile = File(...),
    config: str | None = Form(None),
    user: User = Depends(get_user_or_guest),
) -> TaskDetailModel:
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported.",
        )
    overrides = _parse_config(config)
    try:
        record = await service.submit(file, overrides, user=user)
    except InvalidConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return _serialize_detail(record)


@app.get("/api/tasks", response_model=list[TaskSummaryModel])
async def list_tasks(
    limit: int = 20, user: User = Depends(get_user_or_guest)
) -> list[TaskSummaryModel]:
    limit = max(1, min(limit, 100))
    records = await storage.list(owner=user.username, limit=limit)
    return [_serialize_summary(record) for record in records]


@app.get("/api/tasks/{task_id}", response_model=TaskDetailModel)
async def get_task(task_id: str, user: User = Depends(get_user_or_guest)) -> TaskDetailModel:
    try:
        record = await storage.get(task_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if record.owner != user.username:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if _is_expired(record):
        await storage.delete(task_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return _serialize_detail(record)


@app.get("/api/tasks/{task_id}/result")
async def download_result(
    task_id: str,
    mode: ResultMode = ResultMode.mono,
    disposition: str = "attachment",
    user: User = Depends(get_user_or_guest),
):
    try:
        record = await storage.get(task_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if record.owner != user.username:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if _is_expired(record):
        await storage.delete(task_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if not record.result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result not available yet.",
        )
    key = {
        ResultMode.mono: "mono_pdf",
        ResultMode.dual: "dual_pdf",
        ResultMode.original: "original_pdf",
    }[mode]
    result_path = record.result.get(key)
    if not result_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{mode.value} PDF not available.",
        )
    path = Path(result_path)
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File missing on server.",
        )
    response = FileResponse(
        path,
        media_type="application/pdf",
        filename=path.name,
    )
    # 明确设置 Content-Disposition，避免浏览器插件（如 IDM）因默认 attachment 而强制下载
    if str(disposition).lower() == "inline":
        response.headers["Content-Disposition"] = f'inline; filename="{path.name}"'
    else:
        response.headers["Content-Disposition"] = f'attachment; filename="{path.name}"'
    return response


@app.get("/api/tasks/{task_id}/archive")
async def download_archive(
    task_id: str,
    user: User = Depends(get_user_or_guest),
):
    try:
        record = await storage.get(task_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if record.owner != user.username:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if _is_expired(record):
        await storage.delete(task_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if not record.result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result not available yet.",
        )
    output_dir_str = None
    try:
        output_dir_str = (record.result or {}).get("output_dir")
    except Exception:
        output_dir_str = None
    if not output_dir_str:
        # Fallback for legacy records
        output_dir_str = str(record.output_dir)
    output_dir = Path(output_dir_str)
    if not output_dir.exists() or not output_dir.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Output directory missing on server.",
        )

    task_dir = output_dir.parent
    zip_base = task_dir / "package"
    zip_path = Path(shutil.make_archive(str(zip_base), "zip", root_dir=str(output_dir)))
    if not zip_path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create archive.",
        )
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=f"{task_id}.zip",
    )


@app.get("/api/auth/me", response_model=UserProfileModel)
async def read_current_user(user: User = Depends(get_current_user)) -> UserProfileModel:
    return _profile_from_user(user)


__all__ = ["app"]
