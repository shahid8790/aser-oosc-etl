"""Shared settings: database connection and folders.

Credentials come from environment variables (or a local .env file that is
git-ignored). They are never written in the code.
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

load_dotenv()

DATA_DIR = Path(os.getenv("DATA_DIR", "data/raw"))
CHART_DIR = Path(os.getenv("CHART_DIR", "outputs/charts"))
TABLE_DIR = Path(os.getenv("TABLE_DIR", "outputs/tables"))


def get_engine():
    missing = [v for v in ("PG_USER", "PG_PASSWORD") if not os.getenv(v)]
    if missing:
        sys.exit(
            f"Missing {', '.join(missing)}. Copy .env.example to .env "
            "and fill in your PostgreSQL credentials."
        )
    url = URL.create(
        "postgresql+psycopg2",
        username=os.environ["PG_USER"],
        password=os.environ["PG_PASSWORD"],
        host=os.getenv("PG_HOST", "localhost"),
        port=int(os.getenv("PG_PORT", "5432")),
        database=os.getenv("PG_DATABASE", "aser_2012"),
    )
    return create_engine(url)
