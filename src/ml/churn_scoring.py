"""
Churn skorlama modülü.

Eğitilmiş model ile tüm müşterilere churn risk skoru atar ve CRM export üretir.
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd

from src.config import MODELS_DIR, PROCESSED_DATA_DIR, REPORTS_DIR
from src.ml.churn_prediction import build_feature_matrix
from src.utils.logger import logger


def score_all_customers(model_name: str = "random_forest") -> pd.DataFrame:
    """
    Tüm müşterilere churn olasılığı ve risk seviyesi atar.

    Returns:
        customer_id, churn_probability, risk_level, recommended_action
    """
    model_path = MODELS_DIR / f"churn_{model_name}.joblib"
    if not model_path.exists():
        logger.warning("churn_model_not_found", path=str(model_path))
        return pd.DataFrame()

    model = joblib.load(model_path)
    X, _, _, customer_ids = build_feature_matrix()
    proba = model.predict_proba(X)[:, 1]

    customers = pd.read_csv(PROCESSED_DATA_DIR / "customers.csv")

    scored = pd.DataFrame({
        "customer_id": customer_ids.values,
        "churn_probability": proba.round(4),
    })

    scored = scored.merge(
        customers[["customer_id", "first_name", "last_name", "email", "region", "customer_segment"]],
        on="customer_id",
        how="left",
    )

    scored["risk_level"] = pd.cut(
        scored["churn_probability"],
        bins=[0, 0.3, 0.6, 0.8, 1.0],
        labels=["Düşük", "Orta", "Yüksek", "Kritik"],
        include_lowest=True,
    )

    scored["recommended_action"] = scored["risk_level"].map({
        "Düşük": "Sadakat programına dahil et",
        "Orta": "Kişiselleştirilmiş e-posta gönder",
        "Yüksek": "Win-back kampanyası başlat",
        "Kritik": "Acil müşteri temsilcisi araması",
    })

    return scored.sort_values("churn_probability", ascending=False)


def export_churn_scores(model_name: str = "random_forest") -> Path:
    """Churn skorlarını CSV olarak kaydeder."""
    scored = score_all_customers(model_name)
    if scored.empty:
        return Path()

    output = REPORTS_DIR / "churn_scores.csv"
    scored.to_csv(output, index=False, encoding="utf-8")
    logger.info("churn_scores_exported", rows=len(scored), path=str(output))

    summary = {
        "total_scored": len(scored),
        "critical_count": int((scored["risk_level"] == "Kritik").sum()),
        "high_count": int((scored["risk_level"] == "Yüksek").sum()),
        "avg_churn_probability": round(float(scored["churn_probability"].mean()), 4),
    }
    with open(REPORTS_DIR / "churn_score_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    return output


def main() -> None:
    path = export_churn_scores()
    if path.exists():
        df = pd.read_csv(path)
        print(f"\nChurn skorları kaydedildi: {path}")
        print(f"  Toplam müşteri: {len(df):,}")
        print(f"  Kritik risk: {(df['risk_level'] == 'Kritik').sum():,}")
        print(f"  Yüksek risk: {(df['risk_level'] == 'Yüksek').sum():,}")


if __name__ == "__main__":
    main()
