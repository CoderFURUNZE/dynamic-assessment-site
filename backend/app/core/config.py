from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "dynamic-assessment"
    api_prefix: str = "/api"
    database_url: str = "sqlite:///./app.db"
    secret_key: str = "CHANGE_ME"
    # Default to 7 days to match the frontend "7天" remember option.
    access_token_exp_minutes: int = 60 * 24 * 7
    cors_origins: str = "http://localhost:5173"
    media_dir: str = "media"
    media_url: str = "/media"


settings = Settings()
