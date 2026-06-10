"""
ETL (Extract, Transform, Load) modülü.

CSV dosyalarından veriyi okur, dönüştürür ve PostgreSQL'e yükler.
Veri doğrulama kuralları uygulanır.
"""

from pathlib import Path

import pandas as pd

from src.config import PROCESSED_DATA_DIR, SQL_DIR
from src.data_quality.quality_checks import run_all_quality_checks
from src.utils.db import execute_sql_file, get_engine, load_dataframe_to_db
from src.utils.logger import logger

# Tablo yükleme sırası (foreign key bağımlılıkları)
TABLE_LOAD_ORDER = [
    "customers",
    "products",
    "orders",
    "order_items",
    "payments",
    "website_events",
]

# Tarih sütunları - datetime'a dönüştürülecek
DATE_COLUMNS = {
    "customers": ["registration_date"],
    "products": ["created_at"],
    "orders": ["order_date"],
    "payments": ["payment_date"],
    "website_events": ["event_timestamp"],
}


def transform_dataframe(df: pd.DataFrame, table_name: str) -> pd.DataFrame:
    """
    Tabloya özel dönüşümler uygular.

    - Tarih sütunlarını parse eder
    - Veri tiplerini düzeltir
    - Geçersiz kayıtları temizler
    """
    df = df.copy()

    # Tarih dönüşümleri
    if table_name in DATE_COLUMNS:
        for col in DATE_COLUMNS[table_name]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

    # orders: geçersiz status temizliği
    if table_name == "orders":
        valid_statuses = {"completed", "cancelled", "returned", "pending"}
        df = df[df["order_status"].isin(valid_statuses)]

    # order_items: negatif miktar/fiyat temizliği
    if table_name == "order_items":
        df = df[(df["quantity"] > 0) & (df["unit_price"] > 0)]

    # payments: sadece başarılı ödemeleri koru (analiz için)
    if table_name == "payments":
        df["payment_status"] = df["payment_status"].fillna("success")

    return df


def extract_from_csv(table_name: str) -> pd.DataFrame:
    """CSV dosyasından veri okur."""
    filepath = PROCESSED_DATA_DIR / f"{table_name}.csv"
    if not filepath.exists():
        raise FileNotFoundError(
            f"Veri dosyası bulunamadı: {filepath}. "
            "Önce 'python -m src.data_generation.generate_data' çalıştırın."
        )
    df = pd.read_csv(filepath, encoding="utf-8")
    logger.info("csv_extracted", table=table_name, rows=len(df))
    return df


def load_schema() -> None:
    """Veritabanı şemasını oluşturur."""
    schema_file = SQL_DIR / "01_schema.sql"
    if schema_file.exists():
        execute_sql_file(str(schema_file))
        logger.info("schema_loaded")
    else:
        logger.warning("schema_file_not_found", path=str(schema_file))


def run_etl() -> dict[str, int]:
    """
    Tam ETL pipeline'ını çalıştırır.

    Returns:
        Tablo adı -> yüklenen satır sayısı sözlüğü
    """
    logger.info("etl_started")

    # Şema oluştur
    load_schema()

    load_counts = {}

    for table_name in TABLE_LOAD_ORDER:
        # Extract
        df = extract_from_csv(table_name)

        # Transform
        df = transform_dataframe(df, table_name)

        # Veri kalitesi kontrolleri
        run_all_quality_checks(df, table_name)

        # Load
        count = load_dataframe_to_db(df, table_name, if_exists="replace")
        load_counts[table_name] = count

    total = sum(load_counts.values())
    logger.info("etl_completed", total_rows=total, breakdown=load_counts)
    return load_counts


def main() -> None:
    """CLI entry point."""
    counts = run_etl()
    print(f"\nETL tamamlandı. Toplam yüklenen satır: {sum(counts.values()):,}")
    for table, count in counts.items():
        print(f"  {table}: {count:,}")


if __name__ == "__main__":
    main()
