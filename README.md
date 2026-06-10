# E-Ticaret Müşteri Davranışı ve Gelir Tahmin Platformu

**v2.0 — Gelişmiş Analytics Pro**

Uçtan uca veri analizi, makine öğrenmesi ve tahminleme platformu.

## v2.0 Yenilikleri

| Özellik | Açıklama |
|---------|----------|
| **Global Filtreler** | Tarih, bölge, kanal, kategori filtreleri tüm sayfalara yansır |
| **MoM/YoY Büyüme** | Executive summary'de delta metrikleri ve otomatik insight |
| **CLV Analizi** | Bronze/Silver/Gold/Platinum tier segmentasyonu |
| **Müşteri Yolculuğu** | Dönüşüm hunisi + market basket (cross-sell) analizi |
| **Anomali Tespiti** | Z-score ile olağandışı satış günleri |
| **Churn Risk Listesi** | 12.000+ müşteri skorlanır, CSV export, risk filtreleme |
| **Cross-Validation** | Churn modellerinde 5-fold CV ROC-AUC |
| **Saatlik/Günlük Desen** | Satış zamanlaması analizi |
| **Gelişmiş UI** | Inter font, gradient tema, insight kutuları |

Bir e-ticaret şirketi aşağıdaki sorulara yanıt aramaktadır:

1. **Müşteri kaybı (churn):** Hangi müşteriler gelecek 90 gün içinde kaybedilebilir?
2. **Gelir projeksiyonu:** Önümüzdeki 6 ayda aylık satış ne olacak?
3. **Segmentasyon:** Müşteriler davranışlarına göre nasıl gruplanır (RFM)?
4. **Kanal verimliliği:** Hangi pazarlama kanalı en yüksek dönüşümü sağlıyor?
5. **Ürün karlılığı:** Hangi ürünler en yüksek brüt karı üretiyor?

Bu platform, sentetik veri üretiminden dashboard sunumuna kadar tüm analitik süreci otomatikleştirir.

---

## Mimari

```
┌─────────────────────────────────────────────────────────────────┐
│                     STREAMLIT DASHBOARD                          │
│  Executive Summary │ Sales │ Customer │ Churn │ Forecast │ Map  │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                      ANALYTICS LAYER (Python)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │   Analysis   │  │  ML Models   │  │    Forecasting        │  │
│  │  RFM/Cohort  │  │ RF + XGBoost │  │  Prophet + ARIMA      │  │
│  └──────────────┘  └──────────────┘  └───────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                       SQL LAYER (PostgreSQL)                     │
│  22 Analytics Queries │ Window Functions │ CTE │ Cohort │ RFM   │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                        ETL PIPELINE                              │
│  CSV Extract → Transform → Quality Checks → PostgreSQL Load   │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                     DATA GENERATION                              │
│  customers │ orders │ products │ order_items │ payments │ events│
│                    450.000+ satır sentetik veri                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Proje Yapısı

```
project/
├── data/
│   ├── raw/                  # Ham veri
│   └── processed/            # İşlenmiş CSV dosyaları
├── notebooks/
│   └── 01_eda_analysis.ipynb # Keşifsel veri analizi
├── sql/
│   ├── 01_schema.sql         # PostgreSQL şema
│   └── 02_analytics_queries.sql  # 22 ileri seviye sorgu
├── src/
│   ├── data_generation/      # Sentetik veri üretimi
│   ├── etl/                  # ETL pipeline
│   ├── analysis/             # Satış ve müşteri analizi
│   ├── ml/                   # Churn prediction
│   ├── forecasting/          # Gelir tahmini
│   ├── data_quality/         # Veri kalitesi kontrolleri
│   └── utils/                # DB, logging yardımcıları
├── dashboard/
│   ├── app.py                # Streamlit ana uygulama
│   └── data_loader.py        # Dashboard veri katmanı
├── models/                   # Eğitilmiş ML modelleri
├── reports/                  # Metrik raporları, grafikler
├── tests/                    # Unit testler
├── .github/workflows/        # CI/CD pipeline
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## Hızlı Başlangıç

### Gereksinimler

- Python 3.11+
- PostgreSQL 16+ (opsiyonel, CSV ile de çalışır)
- Docker & Docker Compose (opsiyonel)

### Kurulum

```bash
# Repoyu klonla
git clone <repo-url>
cd project

# Sanal ortam oluştur
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Bağımlılıkları yükle
pip install -r requirements.txt

# Ortam değişkenlerini ayarla
cp .env.example .env
```

### Veri Üretimi ve Pipeline

```bash
# 1. Sentetik veri üret (450.000+ satır)
python -m src.data_generation.generate_data

# 2. Churn modeli eğit
python -m src.ml.churn_prediction

# 3. Gelir tahmini
python -m src.forecasting.revenue_forecast

# 4. Dashboard'u başlat
streamlit run dashboard/app.py
```

### Docker ile Çalıştırma

```bash
docker-compose up --build
# Dashboard: http://localhost:8501
# PostgreSQL: localhost:5432
```

### PostgreSQL ETL (Opsiyonel)

```bash
# PostgreSQL'i başlat
docker-compose up postgres -d

# Veriyi yükle
python -m src.etl.load_to_postgres
```

---

## Dashboard Bölümleri

| Bölüm | İçerik |
|-------|--------|
| **Executive Summary** | KPI kartları, satış trendi, bölgesel dağılım |
| **Satış Analizi** | Aylık trend, ürün performansı, kanal dönüşümü |
| **Müşteri Analizi** | RFM segmentasyonu, cohort retention, demografi |
| **Churn Tahmini** | RF vs XGBoost karşılaştırma, ROC-AUC, feature importance |
| **Gelir Tahmini** | Prophet vs ARIMA, 6 aylık projeksiyon |
| **Ürün Performansı** | Kategori analizi, karlılık scatter plot |
| **Bölgesel Harita** | Türkiye haritası üzerinde bölgesel performans |
| **Veri Kalitesi** | Eksik veri, aykırı değer, doğrulama raporu |

---

## SQL Analitik Sorguları (22 Adet)

| # | Sorgu | Teknik |
|---|-------|--------|
| 1 | Aylık satış trendi | Window Function, Running Total |
| 2 | En karlı ürünler | CTE, RANK |
| 3 | RFM analizi | NTILE, Window Function |
| 4 | Cohort analizi | CTE, Retention Rate |
| 5 | AOV bölgesel | PERCENTILE_CONT |
| 6 | Tekrar satın alma oranı | Aggregation |
| 7 | Kanal dönüşüm oranları | Funnel CTE |
| 8 | CLV analizi | CTE, Aggregation |
| 9 | Churn risk skorlaması | CASE, Window |
| 10 | Kategori YoY performans | LAG, Window |
| 11 | Ödeme yöntemi analizi | Window Share |
| 12 | Sipariş kanalı performansı | RANK |
| 13 | Demografik segmentasyon | JOIN, Aggregation |
| 14 | Haftalık satış deseni | EXTRACT DOW |
| 15 | Cross-sell analizi | Self JOIN |
| 16 | İade/iptal oranı | Conditional Aggregation |
| 17 | Müşteri edinme maliyeti | Conversion CTE |
| 18 | Stok devir hızı | Aggregation |
| 19 | Session depth analizi | Window, Aggregation |
| 20 | Moving average tahmin | ROWS BETWEEN |
| 21 | Pareto analizi (80/20) | Cumulative Window |
| 22 | Sipariş aralığı analizi | LAG |

---

## Makine Öğrenmesi

### Churn Prediction

- **Hedef:** Son 90 günde sipariş vermeyen müşterileri tahmin et
- **Modeller:** Random Forest, XGBoost
- **Metrikler:** ROC-AUC, Accuracy, Confusion Matrix
- **Özellikler:** Recency, frequency, monetary, kanal çeşitliliği, demografik

### Gelir Tahmini

- **Hedef:** 6 aylık aylık satış projeksiyonu
- **Modeller:** Prophet (mevsimsellik), ARIMA(1,1,1)
- **Metrikler:** MAPE, RMSE
- **Güven aralığı:** %95 prediction interval

---

## Veri Kalitesi

| Kontrol | Açıklama |
|---------|----------|
| Eksik veri analizi | Sütun bazlı null oranı |
| Aykırı değer (IQR) | Q1-1.5×IQR, Q3+1.5×IQR |
| Benzersizlik | Primary key tekrar kontrolü |
| İş kuralları | Fiyat > Maliyet, geçerli status değerleri |
| Pozitif değer | Miktar, fiyat negatif olamaz |

---

## Testler

```bash
# Tüm testleri çalıştır
pytest tests/ -v

# Coverage raporu
pytest tests/ --cov=src --cov-report=term-missing
```

---

## Sonuçlar ve Öneriler

### Temel Bulgular (Sentetik Veri)

1. **Churn Oranı:** Müşterilerin ~%35-45'i 90 gün inaktif; XGBoost ROC-AUC > 0.85
2. **RFM Segmentleri:** Champions ve At Risk segmentleri aksiyon gerektirir
3. **Kanal Verimliliği:** Email ve referral en yüksek dönüşüm oranına sahip
4. **Bölgesel:** Marmara ve İç Anadolu en yüksek gelir payına sahip
5. **Ürün:** Elektronik kategorisi en yüksek gelir, Kitap en yüksek marj

### İş Önerileri

| Öncelik | Aksiyon | Beklenen Etki |
|---------|---------|---------------|
| Yüksek | At Risk segmentine win-back kampanyası | Churn %10 azalma |
| Yüksek | VIP müşterilere kişiselleştirilmiş teklifler | CLV %15 artış |
| Orta | Düşük dönüşümlü kanallara bütçe optimizasyonu | CAC %20 azalma |
| Orta | Cross-sell önerileri (Pareto top ürünler) | AOV %8 artış |
| Düşük | Güneydoğu bölgesine lojistik yatırım | Bölgesel büyüme |

---

## Teknoloji Stack

| Katman | Teknoloji |
|--------|-----------|
| Veri Üretimi | Python, Faker, NumPy |
| Veritabanı | PostgreSQL 16 |
| ETL | Pandas, SQLAlchemy |
| Analiz | Pandas, SQL |
| ML | Scikit-learn, XGBoost |
| Tahminleme | Prophet, Statsmodels (ARIMA) |
| Dashboard | Streamlit, Plotly, Folium |
| DevOps | Docker, GitHub Actions |
| Logging | Structlog |
| Test | Pytest |

---

## Lisans

MIT License

## Katkı

Pull request'ler memnuniyetle karşılanır. Büyük değişiklikler için önce issue açınız.
#   V e r i D a s h b o a r d  
 #   V e r i D a s h b o a r d 1  
 #   V e r i D a s h b o a r d  
 #   V e r i D a s h b o a r d  
 