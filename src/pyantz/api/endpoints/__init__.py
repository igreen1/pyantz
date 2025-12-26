"""The API endpoints."""

from fastapi import APIRouter

from . import get_jobs, get_parameters

router = APIRouter(prefix="/api/v1.0")
router.include_router(get_jobs.router)
router.include_router(get_parameters.router)

__all__ = [
    "router",
]
