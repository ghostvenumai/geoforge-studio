from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def error_payload(request: Request, code: str, message: str, details: Any = None) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "request_id": getattr(request.state, "request_id", None),
        }
    }


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    message = str(exc.detail) if not isinstance(exc.detail, dict) else "Request failed"
    details = exc.detail if isinstance(exc.detail, dict) else None
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload(request, f"http_{exc.status_code}", message, details),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    safe_errors = [
        {"location": list(item["loc"]), "message": item["msg"], "type": item["type"]}
        for item in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=error_payload(
            request, "validation_error", "Request validation failed", safe_errors
        ),
    )
