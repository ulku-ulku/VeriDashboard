"""
Müşteri analizi modülü.

RFM segmentasyonu, cohort analizi ve müşteri davranış metrikleri.
"""

import pandas as pd

from src.config import CHURN_DAYS_THRESHOLD, PROCESSED_DATA_DIR
from src.utils.logger import logger


def _load_table(name: str) -> pd.DataFrame:
    path = PROCESSED_DATA_DIR / f"{name}.csv"
    return pd.read_csv(path)


def get_rfm_analysis() -> pd.DataFrame:
    """
    RFM (Recency, Frequency, Monetary) analizi.

    Müşterileri davranışlarına göre segmentlere ayırır.
    """
    customers = _load_table("customers")
    orders = _load_table("orders")
    order_items = _load_table("order_items")

    completed = orders[orders["order_status"] == "completed"].copy()
    completed["order_date"] = pd.to_datetime(completed["order_date"])
    merged = completed.merge(order_items, on="order_id")

    today = pd.Timestamp.now()
    rfm = (
        merged.groupby("customer_id")
        .agg(
            last_order=("order_date", "max"),
            frequency=("order_id", "nunique"),
            monetary=("line_total", "sum"),
        )
        .reset_index()
    )
    rfm["recency_days"] = (today - rfm["last_order"]).dt.days

    # RFM skorları (1-5 quintile)
    rfm["r_score"] = pd.qcut(rfm["recency_days"], 5, labels=[5, 4, 3, 2, 1], duplicates="drop")
    rfm["f_score"] = pd.qcut(rfm["frequency"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5], duplicates="drop")
    rfm["m_score"] = pd.qcut(rfm["monetary"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5], duplicates="drop")

    rfm["r_score"] = rfm["r_score"].astype(int)
    rfm["f_score"] = rfm["f_score"].astype(int)
    rfm["m_score"] = rfm["m_score"].astype(int)
    rfm["rfm_total"] = rfm["r_score"] + rfm["f_score"] + rfm["m_score"]

    # Segment ataması
    def assign_segment(row):
        r, f = row["r_score"], row["f_score"]
        if r >= 4 and f >= 4:
            return "Champions"
        if r >= 3 and f >= 3:
            return "Loyal Customers"
        if r >= 4 and f <= 2:
            return "New Customers"
        if r <= 2 and f >= 3:
            return "At Risk"
        if r <= 2 and f <= 2:
            return "Lost"
        return "Potential Loyalists"

    rfm["rfm_segment"] = rfm.apply(assign_segment, axis=1)

    # Müşteri bilgilerini ekle
    rfm = rfm.merge(
        customers[["customer_id", "region", "customer_segment"]],
        on="customer_id",
    )

    logger.info("rfm_analysis_completed", customers=len(rfm))
    return rfm


def get_cohort_analysis() -> pd.DataFrame:
    """Aylık kayıt kohortları için retention analizi."""
    customers = _load_table("customers")
    orders = _load_table("orders")

    customers["registration_date"] = pd.to_datetime(customers["registration_date"])
    customers["cohort_month"] = customers["registration_date"].dt.to_period("M")

    completed = orders[orders["order_status"] == "completed"].copy()
    completed["order_date"] = pd.to_datetime(completed["order_date"])
    completed["order_month"] = completed["order_date"].dt.to_period("M")

    merged = completed.merge(customers[["customer_id", "cohort_month"]], on="customer_id")
    merged["period_number"] = (merged["order_month"] - merged["cohort_month"]).apply(lambda x: x.n)

    cohort_data = (
        merged.groupby(["cohort_month", "period_number"])
        .agg(active_customers=("customer_id", "nunique"))
        .reset_index()
    )

    cohort_sizes = customers.groupby("cohort_month")["customer_id"].nunique().reset_index()
    cohort_sizes.columns = ["cohort_month", "cohort_size"]

    cohort_data = cohort_data.merge(cohort_sizes, on="cohort_month")
    cohort_data["retention_rate"] = (
        cohort_data["active_customers"] / cohort_data["cohort_size"] * 100
    ).round(2)

    return cohort_data


def get_customer_segmentation() -> pd.DataFrame:
    """Demografik ve davranışsal müşteri segmentasyonu."""
    customers = _load_table("customers")
    orders = _load_table("orders")
    order_items = _load_table("order_items")

    completed = orders[orders["order_status"] == "completed"]
    merged = completed.merge(order_items, on="order_id")

    customer_stats = (
        merged.groupby("customer_id")
        .agg(total_spent=("line_total", "sum"), order_count=("order_id", "nunique"))
        .reset_index()
    )

    seg = customers.merge(customer_stats, on="customer_id", how="left")
    seg["total_spent"] = seg["total_spent"].fillna(0)
    seg["order_count"] = seg["order_count"].fillna(0)

    summary = (
        seg.groupby(["customer_segment", "region"])
        .agg(
            customer_count=("customer_id", "count"),
            avg_spent=("total_spent", "mean"),
            avg_orders=("order_count", "mean"),
        )
        .reset_index()
        .round(2)
    )
    return summary


def get_repeat_purchase_rate() -> dict:
    """Tekrar satın alma oranı metrikleri."""
    orders = _load_table("orders")
    completed = orders[orders["order_status"] == "completed"]
    order_counts = completed.groupby("customer_id")["order_id"].nunique()

    total = len(order_counts)
    one_time = (order_counts == 1).sum()
    repeat = (order_counts >= 2).sum()

    return {
        "total_customers_with_orders": total,
        "one_time_buyers": int(one_time),
        "repeat_buyers": int(repeat),
        "repeat_purchase_rate_pct": round(repeat / total * 100, 2) if total > 0 else 0,
    }


def get_churn_labels() -> pd.DataFrame:
    """
    Churn etiketleri oluşturur.

    Son CHURN_DAYS_THRESHOLD günde sipariş vermeyen müşteriler churn kabul edilir.
    """
    customers = _load_table("customers")
    orders = _load_table("orders")

    completed = orders[orders["order_status"] == "completed"].copy()
    completed["order_date"] = pd.to_datetime(completed["order_date"])

    today = pd.Timestamp.now()
    last_order = completed.groupby("customer_id")["order_date"].max().reset_index()
    last_order.columns = ["customer_id", "last_order_date"]

    labels = customers[["customer_id", "customer_segment", "region", "registration_channel"]].merge(
        last_order, on="customer_id", how="left"
    )
    labels["days_since_last_order"] = (
        today - labels["last_order_date"]
    ).dt.days.fillna(9999).astype(int)
    labels["is_churned"] = (labels["days_since_last_order"] > CHURN_DAYS_THRESHOLD).astype(int)

    return labels
