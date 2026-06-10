"""
Veri kalitesi kontrol modülü.

Eksik veri, aykırı değer ve iş kuralı doğrulamalarını içerir.
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from src.utils.logger import logger


@dataclass
class QualityReport:
    """Veri kalitesi raporu sonuçları."""
    table_name: str
    total_rows: int
    missing_data: dict = field(default_factory=dict)
    outliers: dict = field(default_factory=dict)
    validation_errors: list = field(default_factory=list)
    passed: bool = True


# Tablo bazlı doğrulama kuralları
VALIDATION_RULES = {
    "customers": {
        "required_columns": ["customer_id", "email", "registration_date"],
        "unique_columns": ["customer_id", "email"],
    },
    "products": {
        "required_columns": ["product_id", "unit_price", "unit_cost"],
        "positive_columns": ["unit_price", "unit_cost"],
    },
    "orders": {
        "required_columns": ["order_id", "customer_id", "order_date"],
        "valid_values": {"order_status": ["completed", "cancelled", "returned", "pending"]},
    },
    "order_items": {
        "required_columns": ["order_item_id", "order_id", "product_id", "quantity"],
        "positive_columns": ["quantity", "unit_price", "line_total"],
    },
    "payments": {
        "required_columns": ["payment_id", "order_id", "payment_method"],
    },
    "website_events": {
        "required_columns": ["event_id", "customer_id", "event_type", "event_timestamp"],
    },
}


def analyze_missing_data(df: pd.DataFrame) -> dict:
    """
    Eksik veri analizi yapar.

    Her sütun için eksik sayısı ve yüzdesini döndürür.
    """
    missing = {}
    for col in df.columns:
        null_count = df[col].isna().sum()
        if null_count > 0:
            missing[col] = {
                "count": int(null_count),
                "percentage": round(null_count / len(df) * 100, 2),
            }
    return missing


def detect_outliers_iqr(df: pd.DataFrame, columns: list[str]) -> dict:
    """
    IQR yöntemi ile aykırı değer tespiti.

    Q1 - 1.5*IQR ve Q3 + 1.5*IQR dışındaki değerler aykırı kabul edilir.
    """
    outliers = {}
    for col in columns:
        if col not in df.columns or not pd.api.types.is_numeric_dtype(df[col]):
            continue
        series = df[col].dropna()
        if len(series) == 0:
            continue
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        outlier_count = int(((series < lower) | (series > upper)).sum())
        if outlier_count > 0:
            outliers[col] = {
                "count": outlier_count,
                "percentage": round(outlier_count / len(series) * 100, 2),
                "lower_bound": round(float(lower), 2),
                "upper_bound": round(float(upper), 2),
            }
    return outliers


def validate_business_rules(df: pd.DataFrame, table_name: str) -> list[str]:
    """İş kuralı doğrulamalarını uygular."""
    errors = []
    rules = VALIDATION_RULES.get(table_name, {})

    # Zorunlu sütun kontrolü
    for col in rules.get("required_columns", []):
        if col not in df.columns:
            errors.append(f"Zorunlu sütun eksik: {col}")
        elif df[col].isna().all():
            errors.append(f"Zorunlu sütun tamamen boş: {col}")

    # Benzersizlik kontrolü
    for col in rules.get("unique_columns", []):
        if col in df.columns:
            dup_count = df[col].duplicated().sum()
            if dup_count > 0:
                errors.append(f"Benzersizlik ihlali '{col}': {dup_count} tekrar")

    # Pozitif değer kontrolü
    for col in rules.get("positive_columns", []):
        if col in df.columns:
            neg_count = (df[col] < 0).sum()
            if neg_count > 0:
                errors.append(f"Negatif değer '{col}': {neg_count} kayıt")

    # Geçerli değer kontrolü
    for col, valid_vals in rules.get("valid_values", {}).items():
        if col in df.columns:
            invalid = ~df[col].isin(valid_vals) & df[col].notna()
            if invalid.sum() > 0:
                errors.append(f"Geçersiz değer '{col}': {invalid.sum()} kayıt")

    # Ürün: maliyet fiyattan büyük olamaz
    if table_name == "products" and "unit_price" in df.columns and "unit_cost" in df.columns:
        invalid_margin = (df["unit_cost"] > df["unit_price"]).sum()
        if invalid_margin > 0:
            errors.append(f"Maliyet > Fiyat: {invalid_margin} ürün")

    return errors


def run_all_quality_checks(df: pd.DataFrame, table_name: str) -> QualityReport:
    """
    Tüm veri kalitesi kontrollerini çalıştırır.

    Args:
        df: Kontrol edilecek DataFrame
        table_name: Tablo adı

    Returns:
        QualityReport nesnesi
    """
    logger.info("quality_check_started", table=table_name, rows=len(df))

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    missing = analyze_missing_data(df)
    outliers = detect_outliers_iqr(df, numeric_cols)
    validation_errors = validate_business_rules(df, table_name)

    report = QualityReport(
        table_name=table_name,
        total_rows=len(df),
        missing_data=missing,
        outliers=outliers,
        validation_errors=validation_errors,
        passed=len(validation_errors) == 0,
    )

    if missing:
        logger.warning("missing_data_detected", table=table_name, details=missing)
    if outliers:
        logger.info("outliers_detected", table=table_name, details=outliers)
    if validation_errors:
        logger.error("validation_failed", table=table_name, errors=validation_errors)
    else:
        logger.info("quality_check_passed", table=table_name)

    return report
