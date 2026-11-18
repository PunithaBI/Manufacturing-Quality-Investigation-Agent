from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

EVALUATION_DB = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "evaluation"
    / "evaluation.db"
)

DATABASE_URL = f"sqlite:///{EVALUATION_DB.as_posix()}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
)

EvaluationSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)