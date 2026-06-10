"""
Sentetik e-ticaret verisi üretim modülü.

Gerçekçi müşteri davranışları, sipariş kalıpları ve web etkileşimleri
oluşturarak 100.000+ satırlık veri seti üretir.

Tablolar:
    - customers (15.000)
    - products (800)
    - orders (55.000)
    - order_items (~120.000)
    - payments (55.000)
    - website_events (250.000)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from faker import Faker

from src.config import (
    MARKETING_CHANNELS,
    N_CUSTOMERS,
    N_ORDERS,
    N_PRODUCTS,
    N_WEBSITE_EVENTS,
    PRODUCT_CATEGORIES,
    PROCESSED_DATA_DIR,
    RANDOM_SEED,
    REGIONS,
)
from src.utils.logger import logger

fake = Faker("tr_TR")
Faker.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)


def _generate_customer_id() -> str:
    """Benzersiz müşteri UUID'si üretir."""
    return str(uuid.uuid4())


def generate_customers(n: int = N_CUSTOMERS) -> pd.DataFrame:
    """
    Müşteri tablosu oluşturur.

    Her müşteri için demografik bilgiler, bölge, kayıt kanalı ve
    segment bilgisi içerir.
    """
    logger.info("generating_customers", count=n)
    records = []
    cities = [(city, region) for region, cities in REGIONS.items() for city in cities]

    for i in range(n):
        city, region = cities[i % len(cities)]
        registration_date = fake.date_time_between(start_date="-3y", end_date="-30d")

        # Müşteri segmenti: kayıt tarihine göre ağırlıklı dağılım
        days_since_reg = (datetime.now() - registration_date).days
        if days_since_reg > 730:
            segment = np.random.choice(["VIP", "Sadık", "Normal"], p=[0.15, 0.45, 0.40])
        elif days_since_reg > 365:
            segment = np.random.choice(["Sadık", "Normal", "Yeni"], p=[0.30, 0.50, 0.20])
        else:
            segment = np.random.choice(["Normal", "Yeni", "Risk"], p=[0.40, 0.45, 0.15])

        records.append({
            "customer_id": _generate_customer_id(),
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "email": fake.unique.email(),
            "phone": fake.phone_number(),
            "city": city,
            "region": region,
            "registration_date": registration_date,
            "registration_channel": np.random.choice(MARKETING_CHANNELS),
            "customer_segment": segment,
            "is_active": np.random.random() > 0.08,  # %8 pasif müşteri
            "birth_year": np.random.randint(1965, 2005),
            "gender": np.random.choice(["E", "K", "Belirtilmemiş"], p=[0.48, 0.48, 0.04]),
        })

    df = pd.DataFrame(records)
    # Eksik veri simülasyonu (%2 email, %1 telefon)
    missing_email = df.sample(frac=0.02, random_state=RANDOM_SEED).index
    df.loc[missing_email, "email"] = None
    missing_phone = df.sample(frac=0.01, random_state=RANDOM_SEED + 1).index
    df.loc[missing_phone, "phone"] = None

    return df


def generate_products(n: int = N_PRODUCTS) -> pd.DataFrame:
    """Ürün kataloğu oluşturur - kategori, fiyat ve maliyet bilgileri."""
    logger.info("generating_products", count=n)
    records = []

    for i in range(n):
        category = PRODUCT_CATEGORIES[i % len(PRODUCT_CATEGORIES)]
        # Kategoriye göre fiyat aralığı
        price_ranges = {
            "Elektronik": (500, 25000),
            "Giyim": (50, 1500),
            "Ev & Yaşam": (30, 3000),
            "Kozmetik": (20, 800),
            "Spor": (100, 5000),
            "Kitap": (15, 200),
            "Oyuncak": (30, 1500),
            "Gıda": (10, 500),
            "Sağlık": (25, 1200),
            "Bahçe": (40, 2000),
        }
        low, high = price_ranges.get(category, (20, 1000))
        price = round(np.random.lognormal(np.log((low + high) / 2), 0.5), 2)
        price = max(low, min(high, price))
        cost = round(price * np.random.uniform(0.35, 0.75), 2)

        records.append({
            "product_id": f"PRD-{i + 1:05d}",
            "product_name": fake.catch_phrase()[:80],
            "category": category,
            "subcategory": f"{category} Alt-{np.random.randint(1, 6)}",
            "unit_price": price,
            "unit_cost": cost,
            "stock_quantity": np.random.randint(0, 500),
            "is_active": np.random.random() > 0.05,
            "created_at": fake.date_time_between(start_date="-2y", end_date="-1m"),
            "brand": fake.company()[:50],
        })

    return pd.DataFrame(records)


def generate_orders(
    customers: pd.DataFrame,
    n: int = N_ORDERS,
) -> pd.DataFrame:
    """
    Sipariş tablosu oluşturur.

    Müşteri segmentine göre sipariş sıklığı değişir:
    VIP müşteriler daha sık sipariş verir.
    """
    logger.info("generating_orders", count=n)
    records = []
    customer_ids = customers["customer_id"].tolist()
    customer_city = customers.set_index("customer_id")["city"].to_dict()
    customer_region = customers.set_index("customer_id")["region"].to_dict()
    segment_weights = customers.set_index("customer_id")["customer_segment"].map({
        "VIP": 5.0, "Sadık": 3.0, "Normal": 1.5, "Yeni": 1.0, "Risk": 0.3,
    }).fillna(1.0)
    weights = segment_weights.values / segment_weights.sum()

    for i in range(n):
        customer_id = np.random.choice(customer_ids, p=weights)
        order_date = fake.date_time_between(start_date="-2y", end_date="now")
        status = np.random.choice(
            ["completed", "cancelled", "returned", "pending"],
            p=[0.78, 0.08, 0.07, 0.07],
        )

        records.append({
            "order_id": f"ORD-{i + 1:06d}",
            "customer_id": customer_id,
            "order_date": order_date,
            "order_status": status,
            "shipping_city": customer_city[customer_id],
            "shipping_region": customer_region[customer_id],
            "order_channel": np.random.choice(["web", "mobile_app", "marketplace"], p=[0.55, 0.35, 0.10]),
            "discount_amount": round(np.random.exponential(15), 2) if np.random.random() > 0.6 else 0,
        })

    return pd.DataFrame(records)


def generate_order_items(
    orders: pd.DataFrame,
    products: pd.DataFrame,
) -> pd.DataFrame:
    """Sipariş kalemleri - her siparişe 1-5 ürün ekler."""
    logger.info("generating_order_items")
    records = []
    active_products = products[products["is_active"]]["product_id"].tolist()
    product_prices = products.set_index("product_id")["unit_price"].to_dict()

    for _, order in orders.iterrows():
        if order["order_status"] in ("cancelled",):
            continue
        n_items = np.random.choice([1, 2, 3, 4, 5], p=[0.35, 0.30, 0.20, 0.10, 0.05])
        selected_products = np.random.choice(active_products, size=n_items, replace=False)

        for product_id in selected_products:
            quantity = np.random.randint(1, 4)
            unit_price = product_prices[product_id]
            records.append({
                "order_item_id": str(uuid.uuid4()),
                "order_id": order["order_id"],
                "product_id": product_id,
                "quantity": quantity,
                "unit_price": unit_price,
                "line_total": round(unit_price * quantity, 2),
            })

    df = pd.DataFrame(records)
    logger.info("order_items_generated", count=len(df))
    return df


def generate_payments(orders: pd.DataFrame) -> pd.DataFrame:
    """Ödeme kayıtları - tamamlanan siparişler için."""
    logger.info("generating_payments")
    completed = orders[orders["order_status"] == "completed"]
    records = []

    for _, order in completed.iterrows():
        payment_method = np.random.choice(
            ["credit_card", "debit_card", "bank_transfer", "digital_wallet"],
            p=[0.50, 0.25, 0.15, 0.10],
        )
        records.append({
            "payment_id": str(uuid.uuid4()),
            "order_id": order["order_id"],
            "payment_date": order["order_date"] + timedelta(hours=np.random.randint(0, 24)),
            "payment_method": payment_method,
            "payment_status": np.random.choice(["success", "failed"], p=[0.95, 0.05]),
            "currency": "TRY",
        })

    return pd.DataFrame(records)


def generate_website_events(
    customers: pd.DataFrame,
    products: pd.DataFrame,
    n: int = N_WEBSITE_EVENTS,
) -> pd.DataFrame:
    """
    Web sitesi etkileşim olayları.

    Dönüşüm hunisi analizi için: page_view, product_view, add_to_cart, purchase
    """
    logger.info("generating_website_events", count=n)
    customer_ids = customers["customer_id"].tolist()
    product_ids = products["product_id"].tolist()
    event_types = np.array(["page_view", "product_view", "add_to_cart", "purchase", "search"])
    event_weights = np.array([0.40, 0.30, 0.15, 0.05, 0.10])
    channels = np.array(MARKETING_CHANNELS)
    devices = np.array(["desktop", "mobile", "tablet"])
    device_weights = np.array([0.40, 0.50, 0.10])
    pages = np.array(["home", "products", "cart", "checkout", "account"])

    chosen_events = np.random.choice(event_types, size=n, p=event_weights)
    chosen_customers = np.random.choice(customer_ids, size=n)
    chosen_channels = np.random.choice(channels, size=n)
    chosen_devices = np.random.choice(devices, size=n, p=device_weights)
    chosen_pages = np.random.choice(pages, size=n)
    chosen_products = np.random.choice(product_ids, size=n)

    # Tarihler - vektörize
    base_date = np.datetime64("now") - np.timedelta64(365, "D")
    random_days = np.random.randint(0, 365, size=n)
    random_seconds = np.random.randint(0, 86400, size=n)
    timestamps = base_date + random_days.astype("timedelta64[D]") + random_seconds.astype("timedelta64[s]")

    product_event_mask = np.isin(chosen_events, ["product_view", "add_to_cart", "purchase"])

    df = pd.DataFrame({
        "event_id": [str(uuid.uuid4()) for _ in range(n)],
        "customer_id": chosen_customers,
        "event_type": chosen_events,
        "event_timestamp": timestamps,
        "session_id": [str(uuid.uuid4())[:8] for _ in range(n)],
        "channel": chosen_channels,
        "device_type": chosen_devices,
        "product_id": np.where(product_event_mask, chosen_products, None),
        "page_url": [f"/{p}" for p in chosen_pages],
    })

    return df


def save_all_dataframes(dataframes: dict[str, pd.DataFrame]) -> dict[str, int]:
    """Tüm DataFrame'leri CSV olarak kaydeder."""
    row_counts = {}
    for name, df in dataframes.items():
        filepath = PROCESSED_DATA_DIR / f"{name}.csv"
        df.to_csv(filepath, index=False, encoding="utf-8")
        row_counts[name] = len(df)
        logger.info("data_saved", table=name, rows=len(df), path=str(filepath))
    return row_counts


def main() -> dict[str, int]:
    """Ana veri üretim pipeline'ı."""
    logger.info("data_generation_started")

    customers = generate_customers()
    products = generate_products()
    orders = generate_orders(customers)
    order_items = generate_order_items(orders, products)
    payments = generate_payments(orders)
    website_events = generate_website_events(customers, products)

    dataframes = {
        "customers": customers,
        "products": products,
        "orders": orders,
        "order_items": order_items,
        "payments": payments,
        "website_events": website_events,
    }

    row_counts = save_all_dataframes(dataframes)
    total_rows = sum(row_counts.values())
    logger.info("data_generation_completed", total_rows=total_rows, breakdown=row_counts)

    return row_counts


if __name__ == "__main__":
    counts = main()
    print(f"\nVeri üretimi tamamlandı. Toplam satır: {sum(counts.values()):,}")
    for table, count in counts.items():
        print(f"  {table}: {count:,}")
