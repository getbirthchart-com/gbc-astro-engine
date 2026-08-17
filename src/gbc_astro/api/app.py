"""FastAPI application factory for the gbc-astro HTTP adapter."""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from gbc_astro.api.auth import InternalSecretMiddleware
from gbc_astro.api.dependencies import API_VERSION, build_engine
from gbc_astro.api.errors import register_exception_handlers
from gbc_astro.api.routes import (
    forecast,
    health,
    natal,
    professional,
    relationship,
)
from gbc_astro.constants import ENGINE_NAME, ENGINE_VERSION

logger = logging.getLogger("gbc_astro.api")


def _configure_logging() -> None:
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )


def _cors_origins() -> list[str]:
    raw = os.environ.get("GBC_API_CORS_ORIGINS", "").strip()
    if not raw:
        return []
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    _configure_logging()
    app.state.engine = build_engine()
    logger.info(
        "api_started engine=%s engine_version=%s api_version=%s",
        ENGINE_NAME,
        ENGINE_VERSION,
        API_VERSION,
    )
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="GetBirthChart Astrology API",
        version=API_VERSION,
        description=(
            "Thin HTTP adapter over the gbc-astro AstrologyEngine. "
            "All natal calculations are performed by the existing Python engine; "
            "this service does not reimplement astrology math, geocoding, "
            "persistence, or interpretation."
        ),
        lifespan=lifespan,
    )
    origins = _cors_origins()
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Content-Type", "Accept", "Authorization"],
        )

    app.add_middleware(InternalSecretMiddleware)
    register_exception_handlers(app)
    app.include_router(health.router)
    app.include_router(natal.router)
    app.include_router(relationship.router)
    app.include_router(forecast.router)
    app.include_router(professional.charts)
    app.include_router(professional.forecast)
    app.include_router(professional.analysis)
    app.include_router(professional.maps)
    app.include_router(professional.data)
    return app


app = create_app()
