"""
İleri seviye analitik modül.

CLV, müşteri yolculuğu, sepet analizi, anomali tespiti ve büyüme metrikleri.
"""

from __future__ import annotations

import pandas as pd

from src.utils.data_access import DataFilters, filter_events, get_merged_orders, load_table
from src.utils.logger import logger


def get_clv_analysis(filters: DataFilters | None = None) -> pd.DataFrame:
    """
    Customer Lifetime Value analizi.

    Müşteri bazlı CLV, sipariş sıklığı ve ortalama sipariş değeri.
    """
    merged = get_merged_orders(filters)
    if merged.empty:
        return pd.DataFrame()

    customers = load_table("customers")
    clv = (
        merged.groupby("customer_id")
        .agg(
            total_spent=("line_total", "sum"),
            total_orders=("order_id", "nunique"),
            total_items=("quantity", "sum"),
            avg_order_value=("line_total", "mean"),
            first_order=("order_date", "min"),
            last_order=("order_date", "max"),
            gross_profit=("gross_profit", "sum") if "gross_profit" in merged.columns else ("line_total", "sum"),
        )
        .reset_index()
    )
    clv["lifetime_days"] = (clv["last_order"] - clv["first_order"]).dt.days
    clv["clv_tier"] = pd.qcut(
        clv["total_spent"].rank(method="first"),
        q=4,
        labels=["Bronze", "Silver", "Gold", "Platinum"],
    )

    if not customers.empty:
        clv = clv.merge(
            customers[["customer_id", "region", "customer_segment", "registration_channel"]],
            on="customer_id",
            how="left",
        )

    return clv.round(2)


def get_customer_journey_funnel(filters: DataFilters | None = None) -> pd.DataFrame:
    """
    Müşteri yolculuğu hunisi: page_view → product_view → add_to_cart → purchase.
    """
    events = filter_events(filters)
    if events.empty:
        return pd.DataFrame()

    stages = ["page_view", "product_view", "add_to_cart", "purchase"]
    stage_labels = {
        "page_view": "Sayfa Görüntüleme",
        "product_view": "Ürün İnceleme",
        "add_to_cart": "Sepete Ekleme",
        "purchase": "Satın Alma",
    }

    rows = []
    for stage in stages:
        count = events[events["event_type"] == stage]["session_id"].nunique()
        rows.append({"stage": stage_labels[stage], "stage_key": stage, "sessions": count})

    df = pd.DataFrame(rows)
    df["conversion_from_prev"] = df["sessions"].pct_change().fillna(1) * 100
    df["conversion_from_top"] = df["sessions"] / df["sessions"].iloc[0] * 100
    return df.round(2)


def get_basket_analysis(filters: DataFilters | None = None, top_n: int = 15) -> pd.DataFrame:
    """Birlikte satın alınan ürün çiftleri (market basket)."""
    merged = get_merged_orders(filters)
    if merged.empty:
        return pd.DataFrame()

    order_products = merged.groupby("order_id")["product_id"].apply(list).reset_index()

    from itertools import combinations
    from collections import Counter

    pair_counter: Counter = Counter()
    for products in order_products["product_id"]:
        unique = list(set(products))
        if len(unique) >= 2:
            for pair in combinations(sorted(unique), 2):
                pair_counter[pair] += 1

    if not pair_counter:
        return pd.DataFrame()

    product_names = load_table("products").set_index("product_id")["product_name"].to_dict()
    rows = []
    for (p1, p2), count in pair_counter.most_common(top_n):
        rows.append({
            "product_a": product_names.get(p1, p1),
            "product_b": product_names.get(p2, p2),
            "co_occurrence": count,
        })

    return pd.DataFrame(rows)


def get_growth_metrics(filters: DataFilters | None = None) -> dict:
    """
    MoM ve YoY büyüme metrikleri.

    Eksik kalan son ay hariç tutulur — aksi halde -%70 gibi yanıltıcı düşüşler çıkar.
    """
    merged = get_merged_orders(filters)
    if merged.empty:
        return {}

    max_date = merged["order_date"].max()
    max_period = max_date.to_period("M")

    monthly = (
        merged.groupby(merged["order_date"].dt.to_period("M"))
        .agg(revenue=("line_total", "sum"), orders=("order_id", "nunique"))
        .reset_index()
    )
    monthly.columns = ["period", "revenue", "orders"]

    # Devam eden (eksik) ayı çıkar
    if max_date.day < max_period.days_in_month:
        monthly = monthly[monthly["period"] < max_period]

    if len(monthly) < 2:
        return {
            "mom_revenue_growth": 0,
            "mom_order_growth": 0,
            "yoy_revenue_growth": 0,
            "latest_month_revenue": 0,
            "latest_month_orders": 0,
            "comparison_label": "Yetersiz veri",
        }

    latest = monthly.iloc[-1]
    prev = monthly.iloc[-2]
    mom_rev = (latest["revenue"] - prev["revenue"]) / prev["revenue"] * 100 if prev["revenue"] else 0
    mom_ord = (latest["orders"] - prev["orders"]) / prev["orders"] * 100 if prev["orders"] else 0

    yoy_rev = 0.0
    if len(monthly) >= 13:
        yoy_current = monthly.iloc[-1]["revenue"]
        yoy_prev = monthly.iloc[-13]["revenue"]
        yoy_rev = (yoy_current - yoy_prev) / yoy_prev * 100 if yoy_prev else 0

    latest_label = str(latest["period"])
    prev_label = str(prev["period"])

    return {
        "mom_revenue_growth": round(mom_rev, 2),
        "mom_order_growth": round(mom_ord, 2),
        "yoy_revenue_growth": round(yoy_rev, 2),
        "latest_month_revenue": round(float(latest["revenue"]), 2),
        "latest_month_orders": int(latest["orders"]),
        "comparison_label": f"{latest_label} vs {prev_label}",
        "latest_month_label": latest_label,
    }


def get_anomaly_detection(filters: DataFilters | None = None) -> pd.DataFrame:
    """
    Günlük gelir anomalileri (Z-score > 2).

    Beklenmedik satış artış/düşüşlerini tespit eder.
    """
    merged = get_merged_orders(filters)
    if merged.empty:
        return pd.DataFrame()

    daily = (
        merged.groupby(merged["order_date"].dt.date)
        .agg(revenue=("line_total", "sum"), orders=("order_id", "nunique"))
        .reset_index()
    )
    daily.columns = ["date", "revenue", "orders"]

    mean_rev = daily["revenue"].mean()
    std_rev = daily["revenue"].std()
    if std_rev == 0:
        return pd.DataFrame()

    daily["z_score"] = (daily["revenue"] - mean_rev) / std_rev
    daily["anomaly_type"] = daily["z_score"].apply(
        lambda z: "Spike" if z > 2 else ("Drop" if z < -2 else "Normal")
    )
    anomalies = daily[daily["anomaly_type"] != "Normal"].copy()
    anomalies["date"] = anomalies["date"].astype(str)
    return anomalies.round(2)


def get_payment_analysis(filters: DataFilters | None = None) -> pd.DataFrame:
    """Ödeme yöntemi performans analizi."""
    payments = load_table("payments")
    orders = load_table("orders")
    order_items = load_table("order_items")

    if payments.empty or orders.empty:
        return pd.DataFrame()

    completed = orders[orders["order_status"] == "completed"]
    if filters and not filters.is_empty():
        completed = completed.copy()
        completed["order_date"] = pd.to_datetime(completed["order_date"])
        from src.utils.data_access import apply_filters
        completed = apply_filters(completed, filters)

    order_totals = order_items.groupby("order_id")["line_total"].sum().reset_index()
    merged = payments.merge(completed[["order_id"]], on="order_id")
    merged = merged.merge(order_totals, on="order_id")

    return (
        merged.groupby("payment_method")
        .agg(
            transactions=("payment_id", "count"),
            success_rate=("payment_status", lambda x: (x == "success").mean() * 100),
            total_volume=("line_total", "sum"),
            avg_transaction=("line_total", "mean"),
        )
        .reset_index()
        .round(2)
        .sort_values("total_volume", ascending=False)
    )


def get_hourly_pattern(filters: DataFilters | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Saatlik ve günlük satış desenleri."""
    merged = get_merged_orders(filters)
    empty = pd.DataFrame()
    if merged.empty:
        return empty, empty

    merged["hour"] = merged["order_date"].dt.hour
    merged["day_name"] = merged["order_date"].dt.day_name()

    hourly = merged.groupby("hour").agg(
        orders=("order_id", "nunique"),
        revenue=("line_total", "sum"),
    ).reset_index()

    daily = merged.groupby("day_name").agg(
        orders=("order_id", "nunique"),
        revenue=("line_total", "sum"),
    ).reset_index()

    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    daily["day_name"] = pd.Categorical(daily["day_name"], categories=day_order, ordered=True)
    daily = daily.sort_values("day_name")

    return hourly, daily
