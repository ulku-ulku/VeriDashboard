"""
Satış analizi modülü.

Satış trendleri, AOV, bölgesel performans ve kanal analizlerini içerir.
CSV veya PostgreSQL kaynaklarından veri okuyabilir.
"""

import pandas as pd

from src.config import PROCESSED_DATA_DIR
from src.utils.logger import logger


def _load_table(name: str) -> pd.DataFrame:
    """CSV'den tablo yükler (DB bağlantısı olmadan da çalışır)."""
    path = PROCESSED_DATA_DIR / f"{name}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Veri dosyası bulunamadı: {path}")
    return pd.read_csv(path, parse_dates=["order_date"] if name == "orders" else None)


def get_sales_trends() -> pd.DataFrame:
    """
    Aylık satış trendi hesaplar.

    Returns:
        sales_month, revenue, order_count, unique_customers sütunları
    """
    orders = _load_table("orders")
    order_items = _load_table("order_items")

    completed = orders[orders["order_status"] == "completed"].copy()
    completed["order_date"] = pd.to_datetime(completed["order_date"])
    merged = completed.merge(order_items, on="order_id")

    trends = (
        merged.groupby(merged["order_date"].dt.to_period("M"))
        .agg(
            revenue=("line_total", "sum"),
            order_count=("order_id", "nunique"),
            unique_customers=("customer_id", "nunique"),
        )
        .reset_index()
    )
    trends["sales_month"] = trends["order_date"].astype(str)
    trends = trends.drop(columns=["order_date"])
    logger.info("sales_trends_calculated", months=len(trends))
    return trends


def get_top_products(n: int = 20) -> pd.DataFrame:
    """En karlı ürünleri döndürür."""
    products = _load_table("products")
    order_items = _load_table("order_items")
    orders = _load_table("orders")

    completed_orders = orders[orders["order_status"] == "completed"]["order_id"]
    items = order_items[order_items["order_id"].isin(completed_orders)]
    merged = items.merge(products, on="product_id")
    merged["item_cost"] = merged["unit_cost"] * merged["quantity"]

    product_stats = (
        merged.groupby(["product_id", "product_name", "category"])
        .agg(
            total_revenue=("line_total", "sum"),
            total_quantity=("quantity", "sum"),
            total_cost=("item_cost", "sum"),
        )
        .reset_index()
    )
    product_stats["gross_profit"] = product_stats["total_revenue"] - product_stats["total_cost"]
    product_stats["profit_margin_pct"] = (
        product_stats["gross_profit"] / product_stats["total_revenue"] * 100
    ).round(2)

    return product_stats.nlargest(n, "gross_profit")


def get_regional_performance() -> pd.DataFrame:
    """Bölgesel satış performansı."""
    orders = _load_table("orders")
    order_items = _load_table("order_items")

    completed = orders[orders["order_status"] == "completed"]
    merged = completed.merge(order_items, on="order_id")

    regional = (
        merged.groupby("shipping_region")
        .agg(
            total_orders=("order_id", "nunique"),
            total_revenue=("line_total", "sum"),
            avg_order_value=("line_total", "mean"),
            unique_customers=("customer_id", "nunique"),
        )
        .reset_index()
        .round(2)
    )
    return regional.sort_values("total_revenue", ascending=False)


def get_average_order_value() -> dict:
    """Genel ve kanal bazlı ortalama sepet tutarı."""
    orders = _load_table("orders")
    order_items = _load_table("order_items")

    completed = orders[orders["order_status"] == "completed"]
    order_totals = order_items.groupby("order_id")["line_total"].sum().reset_index()
    order_totals.columns = ["order_id", "order_total"]
    merged = completed.merge(order_totals, on="order_id")

    overall_aov = merged["order_total"].mean()
    channel_aov = merged.groupby("order_channel")["order_total"].mean().round(2)

    return {
        "overall_aov": round(overall_aov, 2),
        "channel_aov": channel_aov.to_dict(),
    }


def get_channel_conversion() -> pd.DataFrame:
    """Kanal bazlı dönüşüm oranları (website events)."""
    events = _load_table("website_events")

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

    funnel["conversion_rate_pct"] = (
        funnel["purchases"] / funnel["sessions"] * 100
    ).round(2)
    return funnel.sort_values("conversion_rate_pct", ascending=False)


def get_kpi_summary() -> dict:
    """Executive summary için KPI özeti."""
    orders = _load_table("orders")
    order_items = _load_table("order_items")
    customers = _load_table("customers")

    completed = orders[orders["order_status"] == "completed"]
    merged = completed.merge(order_items, on="order_id")

    total_revenue = merged["line_total"].sum()
    total_orders = completed["order_id"].nunique()
    total_customers = customers["customer_id"].nunique()
    aov = total_revenue / total_orders if total_orders > 0 else 0

    # Tekrar satın alma
    order_counts = completed.groupby("customer_id")["order_id"].nunique()
    repeat_rate = (order_counts >= 2).sum() / len(order_counts) * 100 if len(order_counts) > 0 else 0

    return {
        "total_revenue": round(total_revenue, 2),
        "total_orders": total_orders,
        "total_customers": total_customers,
        "average_order_value": round(aov, 2),
        "repeat_purchase_rate": round(repeat_rate, 2),
    }
