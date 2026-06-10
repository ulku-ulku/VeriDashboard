"""
Gelir tahminleme modülü.

Prophet ve ARIMA modelleri ile aylık satış projeksiyonu üretir.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from prophet import Prophet
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import adfuller

from src.analysis.sales_analysis import get_sales_trends
from src.config import MODELS_DIR, REPORTS_DIR
from src.utils.logger import logger

warnings.filterwarnings("ignore")


def prepare_time_series() -> pd.DataFrame:
    """
    Aylık satış verisini zaman serisi formatına dönüştürür.

    Prophet için 'ds' ve 'y' sütunları gerekir.
    """
    trends = get_sales_trends()
    ts = trends[["sales_month", "revenue"]].copy()
    ts.columns = ["ds", "y"]
    ts["ds"] = pd.to_datetime(ts["ds"])
    ts = ts.sort_values("ds").reset_index(drop=True)
    return ts


def train_prophet_model(ts: pd.DataFrame, periods: int = 6) -> dict:
    """
    Facebook Prophet ile aylık satış tahmini.

    Mevsimsellik ve trend bileşenlerini otomatik yakalar.
    """
    logger.info("prophet_training_started")

    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=False,
        daily_seasonality=False,
        changepoint_prior_scale=0.05,
    )
    model.fit(ts)

    future = model.make_future_dataframe(periods=periods, freq="MS")
    forecast = model.predict(future)

    # Gelecek tahminleri
    future_forecast = forecast[forecast["ds"] > ts["ds"].max()][
        ["ds", "yhat", "yhat_lower", "yhat_upper"]
    ].copy()
    future_forecast.columns = ["date", "predicted_revenue", "lower_bound", "upper_bound"]

    # In-sample metrikleri
    in_sample = forecast[forecast["ds"] <= ts["ds"].max()].merge(ts, on="ds")
    mape = ((in_sample["y"] - in_sample["yhat"]).abs() / in_sample["y"]).mean() * 100
    rmse = ((in_sample["y"] - in_sample["yhat"]) ** 2).mean() ** 0.5

    # Model kaydet
    import joblib
    joblib.dump(model, MODELS_DIR / "prophet_model.joblib")

    logger.info("prophet_training_completed", mape=round(mape, 2), rmse=round(rmse, 2))

    return {
        "model": model,
        "forecast": forecast,
        "future_forecast": future_forecast,
        "metrics": {"mape": round(mape, 2), "rmse": round(rmse, 2)},
    }


def train_arima_model(ts: pd.DataFrame, periods: int = 6) -> dict:
    """
    ARIMA modeli ile aylık satış tahmini.

    ADF testi ile durağanlık kontrolü yapılır.
    """
    logger.info("arima_training_started")

    # Durağanlık testi
    adf_result = adfuller(ts["y"].dropna())
    logger.info("adf_test", statistic=round(adf_result[0], 4), p_value=round(adf_result[1], 4))

    # ARIMA(1,1,1) - basit ve etkili model
    model = ARIMA(ts["y"], order=(1, 1, 1))
    fitted = model.fit()

    # In-sample tahmin
    in_sample_pred = fitted.fittedvalues
    mape = ((ts["y"].iloc[1:] - in_sample_pred.iloc[1:]).abs() / ts["y"].iloc[1:]).mean() * 100
    rmse = ((ts["y"].iloc[1:] - in_sample_pred.iloc[1:]) ** 2).mean() ** 0.5

    # Gelecek tahmin
    future_pred = fitted.forecast(steps=periods)
    future_dates = pd.date_range(
        start=ts["ds"].max() + pd.DateOffset(months=1),
        periods=periods,
        freq="MS",
    )

    future_forecast = pd.DataFrame({
        "date": future_dates,
        "predicted_revenue": future_pred.values,
    })

    # Güven aralığı
    forecast_result = fitted.get_forecast(steps=periods)
    conf_int = forecast_result.conf_int()
    future_forecast["lower_bound"] = conf_int.iloc[:, 0].values
    future_forecast["upper_bound"] = conf_int.iloc[:, 1].values

    import joblib
    joblib.dump(fitted, MODELS_DIR / "arima_model.joblib")

    logger.info("arima_training_completed", mape=round(mape, 2), rmse=round(rmse, 2))

    return {
        "model": fitted,
        "future_forecast": future_forecast,
        "metrics": {"mape": round(mape, 2), "rmse": round(rmse, 2)},
        "aic": round(fitted.aic, 2),
    }


def plot_forecast_comparison(
    ts: pd.DataFrame,
    prophet_result: dict,
    arima_result: dict,
) -> Path:
    """Prophet ve ARIMA tahminlerini karşılaştırmalı grafik."""
    fig, ax = plt.subplots(figsize=(14, 6))

    # Gerçekleşen satışlar
    ax.plot(ts["ds"], ts["y"], "o-", label="Gerçekleşen", color="#333", linewidth=2)

    # Prophet tahmin
    prophet_future = prophet_result["future_forecast"]
    ax.plot(
        prophet_future["date"], prophet_future["predicted_revenue"],
        "s--", label=f"Prophet (MAPE={prophet_result['metrics']['mape']}%)",
        color="#2E86AB",
    )
    ax.fill_between(
        prophet_future["date"],
        prophet_future["lower_bound"],
        prophet_future["upper_bound"],
        alpha=0.15, color="#2E86AB",
    )

    # ARIMA tahmin
    arima_future = arima_result["future_forecast"]
    ax.plot(
        arima_future["date"], arima_future["predicted_revenue"],
        "^--", label=f"ARIMA (MAPE={arima_result['metrics']['mape']}%)",
        color="#A23B72",
    )
    ax.fill_between(
        arima_future["date"],
        arima_future["lower_bound"],
        arima_future["upper_bound"],
        alpha=0.15, color="#A23B72",
    )

    ax.set_xlabel("Tarih")
    ax.set_ylabel("Gelir (TRY)")
    ax.set_title("Aylık Satış Tahmini - Prophet vs ARIMA")
    ax.legend()
    ax.grid(True, alpha=0.3)

    output_path = REPORTS_DIR / "revenue_forecast.png"
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    return output_path


def save_forecast_report(prophet_result: dict, arima_result: dict) -> Path:
    """Tahmin sonuçlarını JSON olarak kaydeder."""
    report = {
        "prophet": {
            "metrics": prophet_result["metrics"],
            "forecast": prophet_result["future_forecast"].to_dict(orient="records"),
        },
        "arima": {
            "metrics": arima_result["metrics"],
            "aic": arima_result.get("aic"),
            "forecast": arima_result["future_forecast"].to_dict(orient="records"),
        },
    }

    # Datetime serialization
    for model_data in report.values():
        for record in model_data.get("forecast", []):
            if "date" in record:
                record["date"] = str(record["date"])

    output_path = REPORTS_DIR / "forecast_metrics.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    return output_path


def main() -> dict:
    """Gelir tahminleme pipeline'ını çalıştırır."""
    logger.info("revenue_forecast_started")

    ts = prepare_time_series()
    prophet_result = train_prophet_model(ts)
    arima_result = train_arima_model(ts)

    plot_forecast_comparison(ts, prophet_result, arima_result)
    save_forecast_report(prophet_result, arima_result)

    summary = {
        "prophet": prophet_result["metrics"],
        "arima": arima_result["metrics"],
    }
    logger.info("revenue_forecast_completed", summary=summary)
    return summary


if __name__ == "__main__":
    summary = main()
    print("\nGelir Tahmin Sonuçları:")
    for model, metrics in summary.items():
        print(f"  {model}: MAPE={metrics['mape']}%, RMSE={metrics['rmse']}")
