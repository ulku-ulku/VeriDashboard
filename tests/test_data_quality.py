"""
Veri kalitesi unit testleri.
"""

import pandas as pd
import pytest

from src.data_quality.quality_checks import (
    analyze_missing_data,
    detect_outliers_iqr,
    run_all_quality_checks,
    validate_business_rules,
)


@pytest.fixture
def sample_orders():
    return pd.DataFrame({
        "order_id": ["ORD-001", "ORD-002", "ORD-003"],
        "customer_id": ["c1", "c2", "c3"],
        "order_date": pd.to_datetime(["2024-01-01", "2024-02-01", "2024-03-01"]),
        "order_status": ["completed", "cancelled", "invalid_status"],
    })


@pytest.fixture
def sample_products():
    return pd.DataFrame({
        "product_id": ["P1", "P2"],
        "unit_price": [100.0, 200.0],
        "unit_cost": [50.0, 250.0],  # P2: maliyet > fiyat
    })


class TestMissingDataAnalysis:
    def test_no_missing(self):
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        result = analyze_missing_data(df)
        assert result == {}

    def test_with_missing(self):
        df = pd.DataFrame({"a": [1, None, 3], "b": [4, 5, None]})
        result = analyze_missing_data(df)
        assert "a" in result
        assert "b" in result
        assert result["a"]["count"] == 1


class TestOutlierDetection:
    def test_detects_outliers(self):
        df = pd.DataFrame({"value": [1, 2, 3, 4, 5, 100]})
        result = detect_outliers_iqr(df, ["value"])
        assert "value" in result
        assert result["value"]["count"] >= 1

    def test_no_outliers(self):
        df = pd.DataFrame({"value": [10, 11, 12, 13, 14]})
        result = detect_outliers_iqr(df, ["value"])
        assert result == {}


class TestBusinessRules:
    def test_invalid_order_status(self, sample_orders):
        errors = validate_business_rules(sample_orders, "orders")
        assert any("Geçersiz değer" in e for e in errors)

    def test_cost_greater_than_price(self, sample_products):
        errors = validate_business_rules(sample_products, "products")
        assert any("Maliyet > Fiyat" in e for e in errors)


class TestQualityReport:
    def test_report_structure(self, sample_orders):
        report = run_all_quality_checks(sample_orders, "orders")
        assert report.table_name == "orders"
        assert report.total_rows == 3
        assert isinstance(report.passed, bool)
