"""FastAPI application entrypoint: lifespan, RFC 7807 errors, router wiring."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from auto48 import models as _models  # noqa: F401  (register all ORM metadata)
from auto48.api.routers import (
    auth,
    billing,
    conversations,
    dealer_analytics,
    escrow,
    feeds,
    geo,
    health,
    import_calculator,
    listings,
    nl_search,
    photos,
    recommendations,
    risk,
    saved_searches,
    stolen,
    tco,
    test_drives,
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

    # CORS: allow the browser frontend (different origin in dev) to call the API.
    # Explicit allowlist from settings — never "*" alongside credentials.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

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
    app.include_router(risk.router)
    app.include_router(tco.router)
    app.include_router(test_drives.router)
    app.include_router(recommendations.router)
    app.include_router(escrow.router)
    app.include_router(import_calculator.router)
    app.include_router(dealer_analytics.router)
    app.include_router(geo.router)
    app.include_router(nl_search.router)
    app.include_router(stolen.router)
    return app


app = create_app()
