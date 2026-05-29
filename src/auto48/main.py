"""FastAPI application entrypoint: lifespan, RFC 7807 errors, router wiring."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from auto48 import models as _models  # noqa: F401  (register all ORM metadata)
from auto48.api.routers import (
    auth,
    billing,
    conversations,
    feeds,
    health,
    listings,
    photos,
    saved_searches,
    valuations,
    vehicles,
)
from auto48.config import get_settings
from auto48.db import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    # Local dev convenience only. Real environments manage schema via Alembic
    # migrations as a separate deploy step — never create tables on every startup.
    if settings.environment == "local":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

    @app.exception_handler(HTTPException)
    async def problem_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """Render HTTPExceptions as RFC 7807 Problem Details."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "type": "about:blank",
                "title": exc.detail if isinstance(exc.detail, str) else "Error",
                "status": exc.status_code,
                "instance": str(request.url),
            },
            media_type="application/problem+json",
        )

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(listings.router)
    app.include_router(vehicles.router)
    app.include_router(photos.router)
    app.include_router(conversations.router)
    app.include_router(valuations.router)
    app.include_router(feeds.router)
    app.include_router(billing.router)
    app.include_router(saved_searches.router)
    return app


app = create_app()
