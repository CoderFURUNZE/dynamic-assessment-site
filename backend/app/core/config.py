from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    _backend_env = str(Path(__file__).resolve().parents[2] / ".env")
    model_config = SettingsConfigDict(env_file=_backend_env, extra="ignore")

    app_name: str = "dynamic-assessment"
    app_env: str = "development"
    api_prefix: str = "/api"
    database_url: str = "mysql+pymysql://root:root123@localhost:3306/dynamic_assessment?charset=utf8mb4"
    secret_key: str = "CHANGE_ME"
    access_token_exp_minutes: int = 60 * 24 * 7
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    media_dir: str = "media"
    media_url: str = "/media"
    bailian_enabled: bool = False
    bailian_api_key: str = ""
    dashscope_api_key: str = ""
    bailian_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    bailian_model: str = "qwen-plus"
    bailian_timeout_seconds: float = 8.0


settings = Settings()
