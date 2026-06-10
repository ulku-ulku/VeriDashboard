"""
Merkezi veri erişim katmanı.

Tüm analiz modülleri bu katman üzerinden filtrelenmiş veri alır.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

import pandas as pd

from src.config import PROCESSED_DATA_DIR

DATE_PARSE = {
    "customers": ["registration_date"],
    "orders": ["order_date"],
    "products": ["created_at"],
    "payments": ["payment_date"],
    "website_events": ["event_timestamp"],
}


@dataclass
class DataFilters:
    """Dashboard ve analiz filtreleri."""
    date_start: Optional[pd.Timestamp] = None
    date_end: Optional[pd.Timestamp] = None
    regions: list[str] = field(default_factory=list)
    channels: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not any([self.date_start, self.date_end, self.regions, self.channels, self.categories])


def load_table(name: str) -> pd.DataFrame:
    """CSV tablosunu yükler."""
    path = PROCESSED_DATA_DIR / f"{name}.csv"
    if not path.exists():
        return pd.DataFrame()
    parse = DATE_PARSE.get(name)
    return pd.read_csv(path, parse_dates=parse)


def get_merged_orders(filters: DataFilters | None = None) -> pd.DataFrame:
    """
    Tamamlanan siparişleri order_items ile birleştirir ve filtre uygular.

    Returns:
        order_id, customer_id, order_date, shipping_region, order_channel,
        line_total, quantity, product_id, category vb.
    """
    orders = load_table("orders")
    order_items = load_table("order_items")
    products = load_table("products")

    if orders.empty or order_items.empty:
        return pd.DataFrame()

    completed = orders[orders["order_status"] == "completed"].copy()
    completed["order_date"] = pd.to_datetime(completed["order_date"])

    merged = completed.merge(order_items, on="order_id")
    if not products.empty:
        merged = merged.merge(
            products[["product_id", "category", "product_name", "unit_cost"]],
            on="product_id",
            how="left",
        )
        merged["item_cost"] = merged["unit_cost"] * merged["quantity"]
        merged["gross_profit"] = merged["line_total"] - merged["item_cost"]

    if filters and not filters.is_empty():
        merged = apply_filters(merged, filters)

    return merged


def apply_filters(df: pd.DataFrame, filters: DataFilters) -> pd.DataFrame:
    """DataFrame'e filtre uygular."""
    result = df.copy()
    if filters.date_start is not None and "order_date" in result.columns:
        result = result[result["order_date"] >= filters.date_start]
    if filters.date_end is not None and "order_date" in result.columns:
        result = result[result["order_date"] <= filters.date_end]
    if filters.regions and "shipping_region" in result.columns:
        result = result[result["shipping_region"].isin(filters.regions)]
    if filters.channels and "order_channel" in result.columns:
        result = result[result["order_channel"].isin(filters.channels)]
    if filters.categories and "category" in result.columns:
        result = result[result["category"].isin(filters.categories)]
    return result


def filter_events(filters: DataFilters | None = None) -> pd.DataFrame:
    """Website events tablosuna filtre uygular."""
    events = load_table("website_events")
    if events.empty:
        return events
    events["event_timestamp"] = pd.to_datetime(events["event_timestamp"])
    if filters is None or filters.is_empty():
        return events
    result = events.copy()
    if filters.date_start is not None:
        result = result[result["event_timestamp"] >= filters.date_start]
    if filters.date_end is not None:
        result = result[result["event_timestamp"] <= filters.date_end]
    if filters.channels:
        result = result[result["channel"].isin(filters.channels)]
    return result


def get_date_bounds() -> tuple[pd.Timestamp, pd.Timestamp]:
    """Sipariş verisindeki min/max tarih aralığı."""
    orders = load_table("orders")
    if orders.empty:
        return pd.Timestamp("2023-01-01"), pd.Timestamp.now()
    orders["order_date"] = pd.to_datetime(orders["order_date"])
    return orders["order_date"].min(), orders["order_date"].max()


def get_filter_options() -> dict:
    """Dashboard filtre seçeneklerini döndürür."""
    orders = load_table("orders")
    products = load_table("products")
    return {
        "regions": sorted(orders["shipping_region"].dropna().unique().tolist()) if not orders.empty else [],
        "channels": sorted(orders["order_channel"].dropna().unique().tolist()) if not orders.empty else [],
        "categories": sorted(products["category"].dropna().unique().tolist()) if not products.empty else [],
        "event_channels": sorted(
            load_table("website_events")["channel"].dropna().unique().tolist()
        ) if not load_table("website_events").empty else [],
    }
