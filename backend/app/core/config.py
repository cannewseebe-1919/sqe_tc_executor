"""Application configuration."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Test Executor"
    DEBUG: bool = False
    DEV_MODE: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/test_executor"
    DATABASE_ECHO: bool = False

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # ADB
    ADB_PATH: str = "adb"
    ADB_POLL_INTERVAL: int = 5  # seconds
    ADB_ENABLED: bool = True  # set False in DEV_MODE to skip real ADB polling

    # Runner App
    RUNNER_APP_PORT: int = 8080
    RUNNER_APP_APK_PATH: str = "runner-app/prebuilt/app-debug.apk"
    # Port exposed to the outside (Docker: 8001, direct: same as PORT)
    # Used for adb reverse so the Runner App can reach the backend via USB
    BACKEND_EXTERNAL_PORT: int = 8001

    # Scrcpy
    SCRCPY_PATH: str = "scrcpy"

    # SAML
    SAML_SETTINGS_PATH: str = "app/core/saml/settings.json"

    # JWT (service-to-service)
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    # Execution
    DEFAULT_STEP_TIMEOUT: int = 30
    SCREENSHOT_DIR: str = "screenshots"
    LOG_DIR: str = "logs"

    # Crash detection
    LOGCAT_POLL_INTERVAL: float = 0.5

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:3001"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
