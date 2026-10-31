"""Database setup. Path does not depend on the directory uvicorn was launched from."""
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / '.env')
SQLALCHEMY_DATABASE_URL = os.getenv('DATABASE_URL', f'sqlite:///{BACKEND_DIR / "remind_ai.db"}')
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={'check_same_thread': False, 'timeout': 20} if SQLALCHEMY_DATABASE_URL.startswith('sqlite:') else {},
    pool_pre_ping=True,
    future=True,
)
if SQLALCHEMY_DATABASE_URL.startswith('sqlite:'):
    @event.listens_for(engine, 'connect')
    def configure_sqlite(connection, _record):
        cursor = connection.cursor()
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.execute('PRAGMA busy_timeout=20000')
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
