import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

# Load .env from project root
_project_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(_project_root / ".env")

# Default database URL (MySQL / Postgres SQL format)
# Format for MySQL: mysql+pymysql://root:password@localhost:3306/qms_db
# Format for Postgres: postgresql://postgres:password@localhost:5432/qms_db
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{(_project_root / 'complaints.db').as_posix()}"
)

# Connect args for SQLite if used as fallback
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

try:
    engine = create_engine(DATABASE_URL, connect_args=connect_args)
    # Test connection
    with engine.connect() as conn:
        pass
except Exception:
    # Fallback to local SQLite if specified MySQL/Postgres server is unreachable
    sqlite_url = f"sqlite:///{(_project_root / 'complaints.db').as_posix()}"
    engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})
    DATABASE_URL = sqlite_url

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_type() -> str:
    if "mysql" in DATABASE_URL.lower():
        return "MySQL"
    elif "postgres" in DATABASE_URL.lower():
        return "PostgreSQL"
    return "SQLite"
