from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from .config import settings
engine = create_engine(f"sqlite:///{settings.DB_PATH}", future=True, echo=False)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

def init_db():
    with engine.begin() as conn:
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS items (
            id TEXT PRIMARY KEY,
            section TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT NOT NULL,
            urls TEXT NOT NULL,
            evidence TEXT,
            why TEXT,
            actionables TEXT,
            published_at TEXT,
            collected_at TEXT,
            badges TEXT,
            domain TEXT,
            base_score REAL DEFAULT 0.0,
            embed BLOB,
            ai_take TEXT,
            ai_cost REAL DEFAULT 0.0,
            comments TEXT
        );"""))
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS briefs (
            date_ict TEXT PRIMARY KEY,
            generated_at TEXT NOT NULL,
            sections TEXT NOT NULL,
            meta TEXT NOT NULL,
            top_picks TEXT
        );"""))
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            event TEXT NOT NULL,
            item_id TEXT,
            domain TEXT,
            meta TEXT
        );"""))
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS models (
            name TEXT PRIMARY KEY,
            blob BLOB NOT NULL,
            created_at TEXT NOT NULL
        );"""))
