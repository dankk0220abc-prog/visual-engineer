import asyncio
import json
import logging
import re
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager, suppress
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from starlette.responses import Response

from visual_engineer_api.api.health import router as health_router
from visual_engineer_api.api.reviews import router as reviews_router
from visual_engineer_api.api.runner_protocol import router as runner_protocol_router
from visual_engineer_api.api.runners import router as runners_router
from visual_engineer_api.api.runs import router as runs_router
from visual_engineer_api.api.tasks import router as tasks_router
from visual_engineer_api.api.validations import router as validations_router
from visual_engineer_api.api.workspaces import router as workspaces_router
from visual_engineer_api.core.config import get_settings
from visual_engineer_api.db.session import get_engine
from visual_engineer_api.services.runner import RunnerService
from visual_engineer_runner_protocol import (
    MAX_PROTOCOL_PAYLOAD_BYTES,
    RUNNER_PROTOCOL_PREFIX,
)

REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def _request_id(request: Request) -> str:
    value = getattr(request.state, "request_id", None)
    return value if isinstance(value, str) else str(uuid.uuid4())


def _error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    details: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    request_id = _request_id(request)
    body: dict[str, Any] = {"error": {"code": code, "message": message, "request_id": request_id}}
    if details is not None:
        body["error"]["details"] = details
    return JSONResponse(body, status_code=status_code, headers={"X-Request-ID": request_id})


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    logger = logging.getLogger("visual_engineer_api.requests")

    async def lease_reaper_loop() -> None:
        while True:
            await asyncio.sleep(settings.runner_reaper_interval_seconds)

            def reap_once() -> None:
                with Session(get_engine()) as session:
                    RunnerService(session, settings).reap_expired()

            try:
                await asyncio.to_thread(reap_once)
            except Exception as exc:
                logger.error(
                    json.dumps(
                        {
                            "event": "lease_reaper_error",
                            "exception_type": type(exc).__name__,
                        },
                        separators=(",", ":"),
                    )
                )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        reaper_task: asyncio.Task[None] | None = None
        if settings.runner_reaper_enabled:
            reaper_task = asyncio.create_task(lease_reaper_loop())
        try:
            yield
        finally:
            if reaper_task is not None:
                reaper_task.cancel()
                with suppress(asyncio.CancelledError):
                    await reaper_task

    app = FastAPI(
        title="VisualEngineer API",
        version="0.5.0",
        description=(
            "Phase 5 Control Plane API for governed planning, isolated fixture workspaces, "
            "and fixed-profile Validation Runs. Plan approval alone never authorizes "
            "execution."
        ),
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "Idempotency-Key",
            "X-Request-ID",
        ],
        expose_headers=["Idempotent-Replay", "X-Request-ID"],
    )

    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        supplied = request.headers.get("X-Request-ID", "")
        request_id = supplied if REQUEST_ID_PATTERN.fullmatch(supplied) else str(uuid.uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()
        if request.method == "POST" and request.url.path.startswith(RUNNER_PROTOCOL_PREFIX):
            content_length = request.headers.get("Content-Length")
            if content_length is not None:
                try:
                    declared_length = int(content_length)
                except ValueError:
                    declared_length = MAX_PROTOCOL_PAYLOAD_BYTES + 1
                if declared_length > MAX_PROTOCOL_PAYLOAD_BYTES:
                    return _error_response(
                        request,
                        status_code=413,
                        code="protocol_payload_too_large",
                        message="Runner protocol payload exceeds the size limit",
                    )
            if len(await request.body()) > MAX_PROTOCOL_PAYLOAD_BYTES:
                return _error_response(
                    request,
                    status_code=413,
                    code="protocol_payload_too_large",
                    message="Runner protocol payload exceeds the size limit",
                )
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            json.dumps(
                {
                    "event": "http_request",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                },
                separators=(",", ":"),
            )
        )
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {
                "location": [str(part) for part in error["loc"]],
                "message": error["msg"],
                "type": error["type"],
            }
            for error in exc.errors()
        ]
        return _error_response(
            request,
            status_code=422,
            code="validation_error",
            message="Request validation failed",
            details=details,
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        detail: dict[str, Any] = exc.detail if isinstance(exc.detail, dict) else {}
        return _error_response(
            request,
            status_code=exc.status_code,
            code=str(detail.get("code", "http_error")),
            message=str(detail.get("message", "Request failed")),
            details=detail.get("details") if isinstance(detail.get("details"), list) else None,
        )

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            json.dumps(
                {
                    "event": "unhandled_request_error",
                    "request_id": _request_id(request),
                    "exception_type": type(exc).__name__,
                },
                separators=(",", ":"),
            )
        )
        return _error_response(
            request,
            status_code=500,
            code="internal_error",
            message="An internal error occurred",
        )

    app.include_router(health_router)
    app.include_router(tasks_router)
    app.include_router(runs_router)
    app.include_router(runners_router)
    app.include_router(workspaces_router)
    app.include_router(validations_router)
    app.include_router(reviews_router)
    app.include_router(runner_protocol_router)
    return app


app = create_app()
