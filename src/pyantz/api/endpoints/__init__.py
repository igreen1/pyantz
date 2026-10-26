"""The API endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from . import get_jobs, get_parameters, pipelines

router = APIRouter(prefix="/api/v1.0")
"""Every endpoint of the api, under ``/api/v1.0``."""
router.include_router(get_jobs.router)
router.include_router(get_parameters.router)
router.include_router(pipelines.router)
router.include_router(pipelines.runs_router)

__all__ = [
    "router",
]
