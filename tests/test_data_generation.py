"""
Veri üretimi unit testleri.
"""

import pandas as pd
import pytest

from src.config import RANDOM_SEED
from src.data_generation.generate_data import (
    generate_customers,
    generate_order_items,
    generate_orders,
    generate_products,
    generate_website_events,
)


@pytest.fixture
def sample_customers():
    return generate_customers(n=100)


@pytest.fixture
def sample_products():
    return generate_products(n=50)


class TestCustomerGeneration:
    def test_customer_count(self, sample_customers):
        assert len(sample_customers) == 100

    def test_required_columns(self, sample_customers):
        required = ["customer_id", "email", "region", "registration_date", "customer_segment"]
        for col in required:
            assert col in sample_customers.columns

    def test_unique_customer_ids(self, sample_customers):
        assert sample_customers["customer_id"].nunique() == 100

    def test_valid_regions(self, sample_customers):
        valid_regions = {
            "Marmara", "Ege", "Akdeniz", "İç Anadolu",
            "Karadeniz", "Doğu Anadolu", "Güneydoğu Anadolu",
        }
        assert sample_customers["region"].isin(valid_regions).all()


class TestProductGeneration:
    def test_product_count(self, sample_products):
        assert len(sample_products) == 50

    def test_positive_prices(self, sample_products):
        assert (sample_products["unit_price"] > 0).all()
        assert (sample_products["unit_cost"] > 0).all()

    def test_cost_less_than_price(self, sample_products):
        assert (sample_products["unit_cost"] <= sample_products["unit_price"]).all()


class TestOrderGeneration:
    def test_orders_reference_valid_customers(self, sample_customers):
        orders = generate_orders(sample_customers, n=200)
        valid_ids = set(sample_customers["customer_id"])
        assert orders["customer_id"].isin(valid_ids).all()

    def test_order_status_values(self, sample_customers):
        orders = generate_orders(sample_customers, n=200)
        valid_statuses = {"completed", "cancelled", "returned", "pending"}
        assert orders["order_status"].isin(valid_statuses).all()


class TestOrderItems:
    def test_items_have_positive_quantity(self, sample_customers, sample_products):
        orders = generate_orders(sample_customers, n=50)
        items = generate_order_items(orders, sample_products)
        if len(items) > 0:
            assert (items["quantity"] > 0).all()
            assert (items["line_total"] > 0).all()


class TestWebsiteEvents:
    def test_event_types(self, sample_customers, sample_products):
        events = generate_website_events(sample_customers, sample_products, n=500)
        valid_types = {"page_view", "product_view", "add_to_cart", "purchase", "search"}
        assert events["event_type"].isin(valid_types).all()

    def test_event_count(self, sample_customers, sample_products):
        events = generate_website_events(sample_customers, sample_products, n=500)
        assert len(events) == 500
