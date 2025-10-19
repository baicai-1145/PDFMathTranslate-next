from __future__ import annotations

import asyncio
import json
import logging
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi import File
from fastapi import Form
from fastapi import HTTPException
from fastapi import UploadFile
from fastapi import status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import ValidationError

from pdf2zh_next import __version__
from pdf2zh_next.config.cli_env_model import CLIEnvSettingsModel
from pdf2zh_next.config.main import ConfigManager
from pdf2zh_next.config.model import SettingsModel
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
    filename: str
    input_path: Path
    output_dir: Path
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
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


class TaskStorage:
    """In-memory task storage with async locks."""

    def __init__(self) -> None:
        self._tasks: dict[str, TaskRecord] = {}
        self._lock = asyncio.Lock()

    async def create(self, record: TaskRecord) -> TaskRecord:
        async with self._lock:
            self._tasks[record.id] = record
        return record

    async def get(self, task_id: str) -> TaskRecord:
        async with self._lock:
            record = self._tasks.get(task_id)
        if record is None:
            raise KeyError(task_id)
        return record

    async def list(self, limit: int = 20) -> list[TaskRecord]:
        async with self._lock:
            records = list(self._tasks.values())
        records.sort(key=lambda r: r.created_at, reverse=True)
        return records[:limit]

    async def update(self, task_id: str, **kwargs: Any) -> TaskRecord:
        async with self._lock:
            record = self._tasks[task_id]
            for key, value in kwargs.items():
                setattr(record, key, value)
            record.updated_at = datetime.utcnow()
            self._tasks[task_id] = record
            return record

    async def append_event(self, task_id: str, event: dict[str, Any]) -> None:
        async with self._lock:
            record = self._tasks[task_id]
            record.events.append(event)
            record.updated_at = datetime.utcnow()
            self._tasks[task_id] = record


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
        self, upload: UploadFile, overrides: dict[str, Any]
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
        detail.result = TaskResultModel.model_validate(record.result)
    return detail


TASK_WORKSPACE = Path(tempfile.gettempdir()) / "pdfmathtranslate-api-tasks"
storage = TaskStorage()
service = TranslationService(storage=storage, workspace=TASK_WORKSPACE)

app = FastAPI(
    title="PDFMathTranslate API",
    version=__version__,
    description="HTTP API wrapper for PDFMathTranslate translation pipeline.",
)


@app.post(
    "/api/tasks",
    response_model=TaskDetailModel,
    status_code=status.HTTP_201_CREATED,
)
async def create_task(
    file: UploadFile = File(...),
    config: str | None = Form(None),
) -> TaskDetailModel:
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported.",
        )
    overrides = _parse_config(config)
    try:
        record = await service.submit(file, overrides)
    except InvalidConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return _serialize_detail(record)


@app.get("/api/tasks", response_model=list[TaskSummaryModel])
async def list_tasks(limit: int = 20) -> list[TaskSummaryModel]:
    limit = max(1, min(limit, 100))
    records = await storage.list(limit=limit)
    return [_serialize_summary(record) for record in records]


@app.get("/api/tasks/{task_id}", response_model=TaskDetailModel)
async def get_task(task_id: str) -> TaskDetailModel:
    try:
        record = await storage.get(task_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return _serialize_detail(record)


@app.get("/api/tasks/{task_id}/result")
async def download_result(task_id: str, mode: ResultMode = ResultMode.mono):
    try:
        record = await storage.get(task_id)
    except KeyError:
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
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=path.name,
    )


__all__ = ["app"]
