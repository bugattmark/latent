from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")
    openai_api_key: str | None = None
    summary_daily_cap_usd: float = 1.0
    summary_max_items: int = 12
    summary_auto: bool = False

    reddit_client_id: str | None = None
    reddit_client_secret: str | None = None
    reddit_user_agent: str = "researcherbrief/1.0"

    cors_origins: str = "http://localhost:5173,http://localhost:5174"
    db_path: str = "data/brief.db"

    hot_window_days: int = 3
    hot_bucket_hours: int = 6
    study_window_days: int = 21

def get_settings() -> Settings:
    return Settings()
