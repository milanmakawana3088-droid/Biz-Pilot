import hashlib
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse
from starlette.types import ASGIApp

from app.db.session import async_session_factory
from app.modules.audit.service import AuditService


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """
    Guarantees that state-changing requests with an Idempotency-Key header
    execute exactly once. If a duplicate request is received, the cached response
    is returned without re-executing stock deductions or ledger writes.
    """

    def __init__(self, app: ASGIApp, header_name: str = "Idempotency-Key"):
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        idempotency_key = request.headers.get(self.header_name) or request.headers.get("X-Idempotency-Key")

        # Only inspect state-mutating requests with an idempotency key
        if not idempotency_key or request.method not in ("POST", "PATCH", "PUT"):
            return await call_next(request)

        # Read body and compute hash
        body_bytes = await request.body()
        req_hash = hashlib.sha256(f"{request.url.path}:{body_bytes.decode('utf-8', errors='ignore')}".encode("utf-8")).hexdigest()

        # Check existing record
        async with async_session_factory() as session:
            existing = await AuditService.get_idempotency_record(session, idempotency_key)
            if existing:
                # Return cached response directly
                return StarletteResponse(
                    content=existing.response_body,
                    status_code=existing.status_code,
                    media_type="application/json",
                    headers={"X-Cache-Lookup": "HIT-IDEMPOTENCY"},
                )

        # Execute downstream request
        response: Response = await call_next(request)

        # Capture response body for successful executions (2xx)
        if 200 <= response.status_code < 300:
            resp_body = [section async for section in response.body_iterator]
            full_body = b"".join(resp_body).decode("utf-8", errors="ignore")

            async with async_session_factory() as session:
                await AuditService.save_idempotency_record(
                    session=session,
                    key=idempotency_key,
                    endpoint=request.url.path,
                    request_hash=req_hash,
                    status_code=response.status_code,
                    response_body=full_body,
                )
                await session.commit()

            # Return a new response with the captured body
            return StarletteResponse(
                content=full_body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )

        return response
