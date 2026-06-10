"""
Analiz modülü unit testleri.
"""

import pandas as pd
import pytest


class TestSalesAnalysisImports:
    def test_module_imports(self):
        from src.analysis import sales_analysis
        assert hasattr(sales_analysis, "get_kpi_summary")
        assert hasattr(sales_analysis, "get_sales_trends")


class TestCustomerAnalysisImports:
    def test_module_imports(self):
        from src.analysis import customer_analysis
        assert hasattr(customer_analysis, "get_rfm_analysis")
        assert hasattr(customer_analysis, "get_churn_labels")


class TestKPIWithMockData:
    """CSV verisi ile KPI hesaplama testi."""

    def test_kpi_calculation(self, tmp_path, monkeypatch):
        # Geçici veri dosyaları oluştur
        customers = pd.DataFrame({
            "customer_id": ["c1", "c2"],
            "region": ["Marmara", "Ege"],
        })
        orders = pd.DataFrame({
            "order_id": ["o1", "o2"],
            "customer_id": ["c1", "c2"],
            "order_status": ["completed", "completed"],
            "order_date": ["2024-01-01", "2024-02-01"],
            "order_channel": ["web", "mobile_app"],
            "shipping_region": ["Marmara", "Ege"],
            "discount_amount": [0, 10],
        })
        order_items = pd.DataFrame({
            "order_id": ["o1", "o2"],
            "line_total": [100.0, 200.0],
            "quantity": [1, 2],
        })

        data_dir = tmp_path / "processed"
        data_dir.mkdir()
        customers.to_csv(data_dir / "customers.csv", index=False)
        orders.to_csv(data_dir / "orders.csv", index=False)
        order_items.to_csv(data_dir / "order_items.csv", index=False)

        monkeypatch.setattr("src.config.PROCESSED_DATA_DIR", data_dir)
        monkeypatch.setattr("src.analysis.sales_analysis.PROCESSED_DATA_DIR", data_dir)

        from src.analysis.sales_analysis import get_kpi_summary
        kpis = get_kpi_summary()

        assert kpis["total_revenue"] == 300.0
        assert kpis["total_orders"] == 2
        assert kpis["total_customers"] == 2
