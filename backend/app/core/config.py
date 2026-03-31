from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _normalize_database_url(database_url: str) -> str:
    if not database_url.startswith("sqlite:///"):
        return database_url
    raw = database_url.removeprefix("sqlite:///")
    db_path = Path(raw)
    if db_path.is_absolute():
        return database_url
    backend_dir = Path(__file__).resolve().parents[2]
    resolved = (backend_dir / db_path).resolve()
    return f"sqlite:///{resolved}"


class Settings(BaseSettings):
    _backend_env = str(Path(__file__).resolve().parents[2] / ".env")
    model_config = SettingsConfigDict(env_file=_backend_env, extra="ignore")

    app_name: str = "dynamic-assessment"
    app_env: str = "development"
    api_prefix: str = "/api"
    database_url: str = "sqlite:///./app.db"
    secret_key: str = "CHANGE_ME"
    # Default to 7 days to match the frontend "7天" remember option.
    access_token_exp_minutes: int = 60 * 24 * 7
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    media_dir: str = "media"
    media_url: str = "/media"


settings = Settings()
settings.database_url = _normalize_database_url(settings.database_url)
