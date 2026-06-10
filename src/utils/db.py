"""Veritabanı yardımcı fonksiyonları."""

from contextlib import contextmanager
from typing import Generator

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.config import DATABASE_URL
from src.utils.logger import logger


def get_engine() -> Engine:
    """SQLAlchemy engine oluşturur."""
    return create_engine(DATABASE_URL, pool_pre_ping=True)


@contextmanager
def get_connection() -> Generator:
    """Bağlantı context manager'ı - otomatik kapatma sağlar."""
    engine = get_engine()
    conn = engine.connect()
    try:
        yield conn
    finally:
        conn.close()
        engine.dispose()


def execute_sql_file(filepath: str) -> None:
    """SQL dosyasını veritabanında çalıştırır."""
    from pathlib import Path

    sql_path = Path(filepath)
    if not sql_path.exists():
        raise FileNotFoundError(f"SQL dosyası bulunamadı: {filepath}")

    sql_content = sql_path.read_text(encoding="utf-8")
    engine = get_engine()

    with engine.begin() as conn:
        # Birden fazla statement varsa ayır ve çalıştır
        statements = [s.strip() for s in sql_content.split(";") if s.strip()]
        for statement in statements:
            if statement and not statement.startswith("--"):
                conn.execute(text(statement))

    logger.info("sql_file_executed", filepath=str(filepath))


def read_sql_query(query: str, params: dict | None = None) -> pd.DataFrame:
    """SQL sorgusunu çalıştırıp DataFrame döndürür."""
    engine = get_engine()
    return pd.read_sql(text(query), engine, params=params or {})


def load_dataframe_to_db(
    df: pd.DataFrame,
    table_name: str,
    if_exists: str = "replace",
    schema: str = "public",
) -> int:
    """
    DataFrame'i PostgreSQL tablosuna yükler.

    Returns:
        Yüklenen satır sayısı
    """
    engine = get_engine()
    row_count = len(df)
    df.to_sql(table_name, engine, if_exists=if_exists, index=False, schema=schema)
    logger.info("dataframe_loaded", table=table_name, rows=row_count)
    return row_count
