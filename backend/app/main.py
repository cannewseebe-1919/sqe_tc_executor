"""Test Executor — FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.core.database import engine, Base
from app.api import auth, devices, execution, streaming, runner
from app.services.device_monitor import device_monitor
from app.services.scheduler import scheduler

settings = get_settings()

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("Starting %s ...", settings.APP_NAME)

    # Validate critical settings
    if settings.JWT_SECRET == "change-me-in-production":
        logger.warning(
            "JWT_SECRET is using the default value! "
            "Set a strong secret in .env for production."
        )

    # Create tables (dev convenience — use Alembic in production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Connect scheduler (Redis)
    await scheduler.connect()

    # Start device monitor (adb devices polling)
    await device_monitor.start()

    logger.info("%s is ready.", settings.APP_NAME)
    yield

    # Shutdown
    await device_monitor.stop()
    await scheduler.disconnect()
    await engine.dispose()
    logger.info("%s shut down.", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(devices.router)
app.include_router(execution.router)
app.include_router(streaming.router)
app.include_router(runner.router)

# Static files (screenshots)
import os
from pathlib import Path as _Path
_screenshot_abs = str(_Path(__file__).resolve().parent.parent / settings.SCREENSHOT_DIR)
os.makedirs(_screenshot_abs, exist_ok=True)
app.mount("/screenshots", StaticFiles(directory=_screenshot_abs), name="screenshots")


@app.get("/health")
async def health():
    from pathlib import Path as _P
    import app.services.test_runner as _tr
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "screenshot_abs": _screenshot_abs,
        "tr_file": str(_P(_tr.__file__).resolve()),
    }
