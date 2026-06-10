"""
Churn Prediction modülü.

Random Forest ve XGBoost modellerini eğitir, karşılaştırır ve kaydeder.
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import cross_val_score, train_test_split
from xgboost import XGBClassifier

from src.config import MODELS_DIR, PROCESSED_DATA_DIR, RANDOM_SEED, REPORTS_DIR
from src.utils.logger import logger


def build_feature_matrix() -> tuple[pd.DataFrame, pd.Series, list[str], pd.Series]:
    """
    Churn modeli için feature matrix oluşturur.

    Veri sızıntısını önlemek için snapshot tarihi kullanılır:
    - Özellikler snapshot öncesi davranışlardan hesaplanır
    - Hedef: snapshot sonrası 90 günde sipariş vermeyen müşteriler
    """
    customers = pd.read_csv(PROCESSED_DATA_DIR / "customers.csv")
    orders = pd.read_csv(PROCESSED_DATA_DIR / "orders.csv", parse_dates=["order_date"])
    order_items = pd.read_csv(PROCESSED_DATA_DIR / "order_items.csv")

    completed = orders[orders["order_status"] == "completed"].copy()

    # Snapshot tarihi: son siparişten 90 gün önce
    max_date = completed["order_date"].max()
    snapshot_date = max_date - pd.Timedelta(days=90)

    # Snapshot öncesi siparişler (özellikler için)
    historical = completed[completed["order_date"] <= snapshot_date]
    # Snapshot sonrası siparişler (hedef için)
    future = completed[completed["order_date"] > snapshot_date]

    historical_merged = historical.merge(order_items, on="order_id")

    # Müşteri bazlı özellikler (sadece snapshot öncesi)
    features = historical_merged.groupby("customer_id").agg(
        total_orders=("order_id", "nunique"),
        total_spent=("line_total", "sum"),
        avg_order_value=("line_total", "mean"),
        total_items=("quantity", "sum"),
        avg_items_per_order=("quantity", "mean"),
        days_since_first_order=("order_date", lambda x: (snapshot_date - x.min()).days),
        days_since_last_order=("order_date", lambda x: (snapshot_date - x.max()).days),
    ).reset_index()

    channel_div = historical.groupby("customer_id")["order_channel"].nunique().reset_index()
    channel_div.columns = ["customer_id", "channel_diversity"]
    features = features.merge(channel_div, on="customer_id", how="left")

    discount_usage = historical.groupby("customer_id").agg(
        total_discount=("discount_amount", "sum"),
        orders_with_discount=("discount_amount", lambda x: (x > 0).sum()),
    ).reset_index()
    features = features.merge(discount_usage, on="customer_id", how="left")

    demo = customers[["customer_id", "birth_year", "gender", "registration_channel", "customer_segment"]]
    features = features.merge(demo, on="customer_id", how="right")

    # Churn hedefi: snapshot sonrası sipariş vermeyenler
    future_customers = set(future["customer_id"].unique())
    historical_customers = set(historical["customer_id"].unique())
    # Sadece snapshot öncesi en az 1 sipariş vermiş müşteriler
    eligible = historical_customers

    labels = customers[customers["customer_id"].isin(eligible)][["customer_id"]].copy()
    labels["is_churned"] = labels["customer_id"].apply(
        lambda cid: 0 if cid in future_customers else 1
    )

    features = features.merge(labels, on="customer_id", how="inner")

    numeric_cols = [
        "total_orders", "total_spent", "avg_order_value", "total_items",
        "avg_items_per_order", "channel_diversity", "total_discount",
        "orders_with_discount", "days_since_first_order", "days_since_last_order",
    ]
    for col in numeric_cols:
        if col in features.columns:
            features[col] = features[col].fillna(0)

    features["age"] = 2026 - features["birth_year"].fillna(1985)

    cat_cols = ["gender", "registration_channel", "customer_segment"]
    features_encoded = pd.get_dummies(features, columns=cat_cols, drop_first=True)

    target = features_encoded["is_churned"].astype(int)
    customer_ids = features_encoded["customer_id"]
    drop_cols = ["customer_id", "is_churned", "birth_year"]
    X = features_encoded.drop(columns=[c for c in drop_cols if c in features_encoded.columns])
    feature_names = X.columns.tolist()

    return X, target, feature_names, customer_ids


def train_models(
    X: pd.DataFrame,
    y: pd.Series,
) -> dict:
    """
    Random Forest ve XGBoost modellerini eğitir.

    Returns:
        Model sonuçları ve metrikleri içeren sözlük
    """
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_SEED, stratify=y,
    )

    models = {
        "random_forest": RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=RANDOM_SEED,
            n_jobs=-1,
            class_weight="balanced",
        ),
        "xgboost": XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=RANDOM_SEED,
            eval_metric="logloss",
        ),
    }

    results = {}

    for name, model in models.items():
        logger.info("training_model", model=name)
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test)[:, 1]

        metrics = {
            "accuracy": round(accuracy_score(y_test, y_pred), 4),
            "roc_auc": round(roc_auc_score(y_test, y_proba), 4),
            "classification_report": classification_report(y_test, y_pred, output_dict=True),
            "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        }

        # Feature importance
        if hasattr(model, "feature_importances_"):
            importance = dict(zip(X.columns, model.feature_importances_.tolist()))
            metrics["feature_importance"] = dict(
                sorted(importance.items(), key=lambda x: x[1], reverse=True)[:15]
            )

        # Cross-validation
        cv_scores = cross_val_score(model, X_train, y_train, cv=5, scoring="roc_auc")
        metrics["cv_roc_auc_mean"] = round(cv_scores.mean(), 4)
        metrics["cv_roc_auc_std"] = round(cv_scores.std(), 4)

        # Model kaydet
        model_path = MODELS_DIR / f"churn_{name}.joblib"
        joblib.dump(model, model_path)

        results[name] = {
            "model": model,
            "metrics": metrics,
            "y_test": y_test,
            "y_proba": y_proba,
        }

        logger.info("model_trained", model=name, roc_auc=metrics["roc_auc"])

    return results


def plot_feature_importance(results: dict, feature_names: list[str]) -> Path:
    """Feature importance grafiklerini oluşturur."""
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    for idx, (name, result) in enumerate(results.items()):
        importance = result["metrics"].get("feature_importance", {})
        if not importance:
            continue
        top_features = list(importance.items())[:10]
        features_list = [f[0][:25] for f in top_features]
        values = [f[1] for f in top_features]

        axes[idx].barh(features_list[::-1], values[::-1], color=["#2E86AB", "#A23B72"][idx])
        axes[idx].set_title(f"{name.replace('_', ' ').title()} - Feature Importance")
        axes[idx].set_xlabel("Importance")

    plt.tight_layout()
    output_path = REPORTS_DIR / "feature_importance.png"
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info("feature_importance_plot_saved", path=str(output_path))
    return output_path


def plot_roc_curves(results: dict) -> Path:
    """ROC eğrilerini karşılaştırmalı olarak çizer."""
    fig, ax = plt.subplots(figsize=(8, 6))

    colors = {"random_forest": "#2E86AB", "xgboost": "#A23B72"}
    for name, result in results.items():
        y_test = result["y_test"]
        y_proba = result["y_proba"]
        fpr, tpr, _ = roc_curve(y_test, y_proba)
        auc = result["metrics"]["roc_auc"]
        ax.plot(fpr, tpr, label=f"{name.replace('_', ' ').title()} (AUC={auc:.3f})", color=colors[name])

    ax.plot([0, 1], [0, 1], "k--", label="Random")
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title("Churn Prediction - ROC Curves")
    ax.legend()
    ax.grid(True, alpha=0.3)

    output_path = REPORTS_DIR / "roc_curves.png"
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    return output_path


def save_metrics_report(results: dict) -> Path:
    """Model metriklerini JSON olarak kaydeder."""
    report = {}
    for name, result in results.items():
        report[name] = {
            k: v for k, v in result["metrics"].items()
            if k != "classification_report" or isinstance(v, dict)
        }
        if "classification_report" in result["metrics"]:
            report[name]["classification_report"] = result["metrics"]["classification_report"]

    output_path = REPORTS_DIR / "churn_model_metrics.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    return output_path


def main() -> dict:
    """Churn prediction pipeline'ını çalıştırır."""
    logger.info("churn_prediction_started")

    X, y, feature_names, _ = build_feature_matrix()
    results = train_models(X, y)

    plot_feature_importance(results, feature_names)
    plot_roc_curves(results)
    save_metrics_report(results)

    # Churn skorlarını export et
    from src.ml.churn_scoring import export_churn_scores
    export_churn_scores()

    summary = {
        name: {"roc_auc": r["metrics"]["roc_auc"], "accuracy": r["metrics"]["accuracy"]}
        for name, r in results.items()
    }
    logger.info("churn_prediction_completed", summary=summary)
    return summary


if __name__ == "__main__":
    summary = main()
    print("\nChurn Model Sonuçları:")
    for model, metrics in summary.items():
        print(f"  {model}: ROC-AUC={metrics['roc_auc']}, Accuracy={metrics['accuracy']}")
