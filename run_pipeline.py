#!/usr/bin/env python
"""
Proje pipeline'ını sırayla çalıştıran ana script.

Kullanım:
    python run_pipeline.py              # Tam pipeline
    python run_pipeline.py --skip-ml      # ML olmadan
    python run_pipeline.py --dashboard    # Sadece dashboard
"""

import argparse
import subprocess
import sys


def run_step(name: str, command: list[str]) -> bool:
    """Pipeline adımını çalıştırır."""
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")
    result = subprocess.run(command, check=False)
    if result.returncode != 0:
        print(f"HATA: {name} başarısız (exit code: {result.returncode})")
        return False
    print(f"✓ {name} tamamlandı")
    return True


def main():
    parser = argparse.ArgumentParser(description="E-Ticaret Analytics Pipeline")
    parser.add_argument("--skip-ml", action="store_true", help="ML adımlarını atla")
    parser.add_argument("--skip-etl", action="store_true", help="ETL adımını atla")
    parser.add_argument("--dashboard", action="store_true", help="Sadece dashboard başlat")
    args = parser.parse_args()

    if args.dashboard:
        subprocess.run([sys.executable, "-m", "streamlit", "run", "dashboard/app.py"])
        return

    steps = [
        ("Veri Üretimi", [sys.executable, "-m", "src.data_generation.generate_data"]),
    ]

    if not args.skip_etl:
        steps.append(("ETL - PostgreSQL", [sys.executable, "-m", "src.etl.load_to_postgres"]))

    if not args.skip_ml:
        steps.extend([
            ("Churn Model Eğitimi", [sys.executable, "-m", "src.ml.churn_prediction"]),
            ("Churn Skorlama", [sys.executable, "-m", "src.ml.churn_scoring"]),
            ("Gelir Tahmini", [sys.executable, "-m", "src.forecasting.revenue_forecast"]),
        ])

    for name, cmd in steps:
        if not run_step(name, cmd):
            sys.exit(1)

    print(f"\n{'='*60}")
    print("  Pipeline tamamlandı!")
    print("  Dashboard: streamlit run dashboard/app.py")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
