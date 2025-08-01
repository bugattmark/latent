from pydantic_settings import BaseSettings
from pathlib import Path

def read_secret(path:str)->str|None:
    try:
        with open(path,"r",encoding="utf-8") as f:return f.read().strip()
    except Exception:return None

class Settings(BaseSettings):
    BRIEF_DOMAIN: str = "http://localhost:8080"
    OAUTH_REDIRECT: str = "http://localhost:8000/oauth/reddit/callback"
    DAILY_BRIEF_TIME_ICT: str = "10:00"
    ALLOW_EMAIL: str = "example@example.com"
    ENABLE_ALERTS: bool = True
    MARKET_ALERTS: bool = False
    AI_KEYWORDS: str = ""
    POLICY_KEYWORDS: str = ""
    DATA_DIR: Path = Path("data")
    SNAPSHOT_DIR: Path = Path("snapshots")
    DB_PATH: Path = Path("data/brief.db")
    REDDIT_CLIENT_ID_FILE: str|None = None
    REDDIT_CLIENT_SECRET_FILE: str|None = None
    OPENAI_API_KEY: str|None = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    DAILY_BUDGET_USD: float = 1.0
    @property
    def reddit_client_id(self)->str|None:
        return read_secret(self.REDDIT_CLIENT_ID_FILE) if self.REDDIT_CLIENT_ID_FILE else None
    @property
    def reddit_client_secret(self)->str|None:
        return read_secret(self.REDDIT_CLIENT_SECRET_FILE) if self.REDDIT_CLIENT_SECRET_FILE else None

settings = Settings()
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
