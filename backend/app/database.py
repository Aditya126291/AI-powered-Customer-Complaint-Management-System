import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

# Load .env from project root
_project_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(_project_root / ".env")

# Primary Database URL configured for MySQL (or PostgreSQL as specified in requirements)
DEFAULT_MYSQL_URL = "mysql+pymysql://root:password@localhost:3306/qms_complaints"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_MYSQL_URL)

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

try:
    engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
    # Verify database connection
    with engine.connect() as conn:
        pass
except Exception:
    # If target MySQL/PostgreSQL server is offline, fallback gracefully to SQLite so local dev never breaks
    fallback_url = f"sqlite:///{(_project_root / 'complaints.db').as_posix()}"
    engine = create_engine(fallback_url, connect_args={"check_same_thread": False})
    DATABASE_URL = fallback_url

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_type() -> str:
    url_lower = DATABASE_URL.lower()
    if "mysql" in url_lower:
        return "MySQL"
    elif "postgres" in url_lower:
        return "PostgreSQL"
    return "SQLite (Development Fallback)"
