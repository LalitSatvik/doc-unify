"""Liveness/readiness check, used by docker-compose and the frontend to
confirm the backend is up before enabling upload/chat.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
