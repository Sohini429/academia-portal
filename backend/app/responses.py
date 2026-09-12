"""Standard API payload contract (manual §5).

Every response - success or failure - is wrapped as:
    {"status": ..., "data": ..., "timestamp": ..., "errors": ...}
"""
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ok(data: Any = None) -> dict:
    return {"status": "success", "data": data, "timestamp": _now(), "errors": None}


def fail(errors: list[str], data: Any = None) -> dict:
    return {"status": "error", "data": data, "timestamp": _now(), "errors": errors}


async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, list) else [str(exc.detail)]
    return JSONResponse(status_code=exc.status_code, content=fail(detail), headers=exc.headers)


async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [f"{'.'.join(str(p) for p in e['loc'][1:])}: {e['msg']}" for e in exc.errors()]
    return JSONResponse(status_code=422, content=fail(errors))
