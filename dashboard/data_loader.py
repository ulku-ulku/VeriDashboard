"""
Streamlit Dashboard - Gelişmiş veri yükleme katmanı.

Filtre destekli, önbellekli analitik fonksiyonlar.
"""

import json

import pandas as pd
import streamlit as st

from src.config import PROCESSED_DATA_DIR, REPORTS_DIR
from src.utils.data_access import DataFilters, get_merged_orders, load_table


def filter_cache_key(filters: DataFilters | None) -> str:
    """Filtre kombinasyonu için cache key."""
    if filters is None or filters.is_empty():
        return "all"
    raw = f"{filters.date_start}|{filters.date_end}|{filters.regions}|{filters.channels}|{filters.categories}"
    from hashlib import md5
    return md5(raw.encode()).hexdigest()[:12]


@st.cache_data(ttl=1800)
def load_csv(table_name: str) -> pd.DataFrame:
    """CSV tablosunu önbellekli yükler."""
    path = PROCESSED_DATA_DIR / f"{table_name}.csv"
    if not path.exists():
        return pd.DataFrame()
    from src.utils.data_access import DATE_PARSE
    return pd.read_csv(path, parse_dates=DATE_PARSE.get(table_name))


@st.cache_data(ttl=1800)
def load_kpi_summary(_key: str, filters_json: str) -> dict:
    """Filtrelenmiş KPI özeti."""
    filters = _deserialize_filters(filters_json)
    merged = get_merged_orders(filters)
    customers = load_table("customers")

    if merged.empty:
        return {"total_revenue": 0, "total_orders": 0, "total_customers": 0,
                "average_order_value": 0, "repeat_purchase_rate": 0}

    total_revenue = merged["line_total"].sum()
    total_orders = merged["order_id"].nunique()
    active_customers = merged["customer_id"].nunique()
    aov = total_revenue / total_orders if total_orders else 0

    order_counts = merged.groupby("customer_id")["order_id"].nunique()
    repeat_rate = (order_counts >= 2).sum() / len(order_counts) * 100 if len(order_counts) else 0

    return {
        "total_revenue": round(total_revenue, 2),
        "total_orders": total_orders,
        "total_customers": active_customers if filters and not filters.is_empty() else len(customers),
        "average_order_value": round(aov, 2),
        "repeat_purchase_rate": round(repeat_rate, 2),
    }


@st.cache_data(ttl=1800)
def load_sales_trends(_key: str, filters_json: str) -> pd.DataFrame:
    filters = _deserialize_filters(filters_json)
    merged = get_merged_orders(filters)
    if merged.empty:
        return pd.DataFrame()

    trends = (
        merged.groupby(merged["order_date"].dt.to_period("M"))
        .agg(
            revenue=("line_total", "sum"),
            order_count=("order_id", "nunique"),
            unique_customers=("customer_id", "nunique"),
            gross_profit=("gross_profit", "sum") if "gross_profit" in merged.columns else ("line_total", "sum"),
        )
        .reset_index()
    )
    trends["sales_month"] = trends["order_date"].astype(str)
    return trends.drop(columns=["order_date"])


@st.cache_data(ttl=1800)
def load_regional_performance(_key: str, filters_json: str) -> pd.DataFrame:
    filters = _deserialize_filters(filters_json)
    merged = get_merged_orders(filters)
    if merged.empty:
        return pd.DataFrame()

    return (
        merged.groupby("shipping_region")
        .agg(
            total_orders=("order_id", "nunique"),
            total_revenue=("line_total", "sum"),
            avg_order_value=("line_total", "mean"),
            unique_customers=("customer_id", "nunique"),
        )
        .reset_index()
        .round(2)
        .sort_values("total_revenue", ascending=False)
    )


@st.cache_data(ttl=1800)
def load_top_products(_key: str, filters_json: str, n: int = 20) -> pd.DataFrame:
    filters = _deserialize_filters(filters_json)
    merged = get_merged_orders(filters)
    if merged.empty or "product_name" not in merged.columns:
        return pd.DataFrame()

    stats = (
        merged.groupby(["product_id", "product_name", "category"])
        .agg(
            total_revenue=("line_total", "sum"),
            total_quantity=("quantity", "sum"),
            total_cost=("item_cost", "sum") if "item_cost" in merged.columns else ("line_total", lambda x: 0),
            gross_profit=("gross_profit", "sum") if "gross_profit" in merged.columns else ("line_total", "sum"),
        )
        .reset_index()
    )
    stats["profit_margin_pct"] = (stats["gross_profit"] / stats["total_revenue"] * 100).round(2)
    return stats.nlargest(n, "gross_profit")


@st.cache_data(ttl=1800)
def load_growth_metrics(_key: str, filters_json: str) -> dict:
    from src.analysis.advanced_analytics import get_growth_metrics
    filters = _deserialize_filters(filters_json)
    return get_growth_metrics(filters)


@st.cache_data(ttl=1800)
def load_clv_analysis(_key: str, filters_json: str) -> pd.DataFrame:
    from src.analysis.advanced_analytics import get_clv_analysis
    filters = _deserialize_filters(filters_json)
    return get_clv_analysis(filters)


@st.cache_data(ttl=1800)
def load_journey_funnel(_key: str, filters_json: str) -> pd.DataFrame:
    from src.analysis.advanced_analytics import get_customer_journey_funnel
    filters = _deserialize_filters(filters_json)
    return get_customer_journey_funnel(filters)


@st.cache_data(ttl=1800)
def load_basket_analysis(_key: str, filters_json: str) -> pd.DataFrame:
    from src.analysis.advanced_analytics import get_basket_analysis
    filters = _deserialize_filters(filters_json)
    return get_basket_analysis(filters)


@st.cache_data(ttl=1800)
def load_anomalies(_key: str, filters_json: str) -> pd.DataFrame:
    from src.analysis.advanced_analytics import get_anomaly_detection
    filters = _deserialize_filters(filters_json)
    return get_anomaly_detection(filters)


@st.cache_data(ttl=1800)
def load_payment_analysis(_key: str, filters_json: str) -> pd.DataFrame:
    from src.analysis.advanced_analytics import get_payment_analysis
    filters = _deserialize_filters(filters_json)
    return get_payment_analysis(filters)


@st.cache_data(ttl=1800)
def load_hourly_patterns(_key: str, filters_json: str):
    from src.analysis.advanced_analytics import get_hourly_pattern
    filters = _deserialize_filters(filters_json)
    return get_hourly_pattern(filters)


@st.cache_data(ttl=3600)
def load_rfm_analysis() -> pd.DataFrame:
    from src.analysis.customer_analysis import get_rfm_analysis
    try:
        return get_rfm_analysis()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=3600)
def load_cohort_analysis() -> pd.DataFrame:
    from src.analysis.customer_analysis import get_cohort_analysis
    try:
        return get_cohort_analysis()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=1800)
def load_channel_conversion(_key: str, filters_json: str) -> pd.DataFrame:
    from src.utils.data_access import filter_events
    filters = _deserialize_filters(filters_json)
    events = filter_events(filters)
    if events.empty:
        return pd.DataFrame()

    funnel = (
        events.groupby("channel")
        .apply(
            lambda g: pd.Series({
                "sessions": g["session_id"].nunique(),
                "product_views": g[g["event_type"] == "product_view"]["session_id"].nunique(),
                "add_to_carts": g[g["event_type"] == "add_to_cart"]["session_id"].nunique(),
                "purchases": g[g["event_type"] == "purchase"]["session_id"].nunique(),
            }),
            include_groups=False,
        )
        .reset_index()
    )
    funnel["conversion_rate_pct"] = (funnel["purchases"] / funnel["sessions"] * 100).round(2)
    return funnel.sort_values("conversion_rate_pct", ascending=False)


def load_churn_metrics() -> dict:
    path = REPORTS_DIR / "churn_model_metrics.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def load_forecast_metrics() -> dict:
    path = REPORTS_DIR / "forecast_metrics.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def load_churn_scores() -> pd.DataFrame:
    path = REPORTS_DIR / "churn_scores.csv"
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


def check_data_availability() -> bool:
    required = ["customers.csv", "orders.csv", "order_items.csv", "products.csv"]
    return all((PROCESSED_DATA_DIR / f).exists() for f in required)


def get_data_quality_summary() -> dict:
    from src.data_quality.quality_checks import run_all_quality_checks
    summary = {}
    for table in ["customers", "products", "orders", "order_items", "payments", "website_events"]:
        path = PROCESSED_DATA_DIR / f"{table}.csv"
        if path.exists():
            df = pd.read_csv(path)
            report = run_all_quality_checks(df, table)
            summary[table] = {
                "rows": report.total_rows,
                "missing_columns": len(report.missing_data),
                "outlier_columns": len(report.outliers),
                "validation_errors": len(report.validation_errors),
                "passed": report.passed,
                "missing_details": report.missing_data,
                "validation_details": report.validation_errors,
            }
    return summary


def serialize_filters(filters: DataFilters) -> str:
    return json.dumps({
        "date_start": str(filters.date_start) if filters.date_start else None,
        "date_end": str(filters.date_end) if filters.date_end else None,
        "regions": filters.regions,
        "channels": filters.channels,
        "categories": filters.categories,
    })


def _deserialize_filters(filters_json: str) -> DataFilters:
    data = json.loads(filters_json)
    return DataFilters(
        date_start=pd.Timestamp(data["date_start"]) if data.get("date_start") else None,
        date_end=pd.Timestamp(data["date_end"]) if data.get("date_end") else None,
        regions=data.get("regions", []),
        channels=data.get("channels", []),
        categories=data.get("categories", []),
    )
