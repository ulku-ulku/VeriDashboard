"""
Merkezi yapılandırma modülü.
Tüm ortam değişkenleri ve sabitler burada tanımlanır.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Proje kök dizini
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# .env dosyasını yükle
load_dotenv(PROJECT_ROOT / ".env")

# Veritabanı ayarları
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "database": os.getenv("DB_NAME", "ecommerce_analytics"),
    "user": os.getenv("DB_USER", "analytics_user"),
    "password": os.getenv("DB_PASSWORD", "analytics_pass"),
}

# SQLAlchemy bağlantı URL'si
DATABASE_URL = (
    f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
    f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
)

# Dizin yolları
DATA_DIR = Path(os.getenv("DATA_DIR", PROJECT_ROOT / "data"))
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
MODELS_DIR = Path(os.getenv("MODELS_DIR", PROJECT_ROOT / "models"))
LOGS_DIR = PROJECT_ROOT / "logs"
REPORTS_DIR = PROJECT_ROOT / "reports"
SQL_DIR = PROJECT_ROOT / "sql"

# Uygulama sabitleri
RANDOM_SEED = int(os.getenv("RANDOM_SEED", "42"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Veri üretim parametreleri
N_CUSTOMERS = 15_000
N_PRODUCTS = 800
N_ORDERS = 55_000
N_WEBSITE_EVENTS = 250_000

# Churn tanımı: son 90 günde sipariş vermeyen müşteri
CHURN_DAYS_THRESHOLD = 90

# Türkiye şehirleri ve bölgeleri
REGIONS = {
    "Marmara": ["İstanbul", "Bursa", "Kocaeli", "Tekirdağ", "Sakarya"],
    "Ege": ["İzmir", "Aydın", "Manisa", "Muğla", "Denizli"],
    "Akdeniz": ["Antalya", "Adana", "Mersin", "Hatay", "Isparta"],
    "İç Anadolu": ["Ankara", "Konya", "Kayseri", "Eskişehir", "Sivas"],
    "Karadeniz": ["Samsun", "Trabzon", "Ordu", "Rize", "Zonguldak"],
    "Doğu Anadolu": ["Erzurum", "Van", "Malatya", "Elazığ", "Ağrı"],
    "Güneydoğu Anadolu": ["Gaziantep", "Şanlıurfa", "Diyarbakır", "Mardin", "Batman"],
}

# Pazarlama kanalları
MARKETING_CHANNELS = ["organic", "paid_search", "social_media", "email", "referral", "direct"]

# Ürün kategorileri
PRODUCT_CATEGORIES = [
    "Elektronik", "Giyim", "Ev & Yaşam", "Kozmetik", "Spor",
    "Kitap", "Oyuncak", "Gıda", "Sağlık", "Bahçe",
]

# Dizinleri oluştur
for directory in [RAW_DATA_DIR, PROCESSED_DATA_DIR, MODELS_DIR, LOGS_DIR, REPORTS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
