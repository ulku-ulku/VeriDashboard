# Veri Sözlüğü (Data Dictionary)

## customers

| Sütun | Tip | Açıklama | Örnek |
|-------|-----|----------|-------|
| customer_id | VARCHAR(36) | Benzersiz müşteri UUID | `a1b2c3d4-...` |
| first_name | VARCHAR(100) | Müşteri adı | Ahmet |
| last_name | VARCHAR(100) | Müşteri soyadı | Yılmaz |
| email | VARCHAR(255) | E-posta adresi | ahmet@email.com |
| phone | VARCHAR(50) | Telefon numarası | +90 532 xxx |
| city | VARCHAR(100) | Şehir | İstanbul |
| region | VARCHAR(100) | Coğrafi bölge | Marmara |
| registration_date | TIMESTAMP | Kayıt tarihi | 2023-05-15 |
| registration_channel | VARCHAR(50) | Edinme kanalı | organic, paid_search |
| customer_segment | VARCHAR(50) | Müşteri segmenti | VIP, Sadık, Normal, Yeni, Risk |
| is_active | BOOLEAN | Aktif müşteri mi | true/false |
| birth_year | INTEGER | Doğum yılı | 1990 |
| gender | VARCHAR(20) | Cinsiyet | E, K, Belirtilmemiş |

## products

| Sütun | Tip | Açıklama | Örnek |
|-------|-----|----------|-------|
| product_id | VARCHAR(20) | Ürün kodu | PRD-00001 |
| product_name | VARCHAR(200) | Ürün adı | Kablosuz Kulaklık |
| category | VARCHAR(100) | Ana kategori | Elektronik |
| subcategory | VARCHAR(100) | Alt kategori | Elektronik Alt-1 |
| unit_price | DECIMAL(12,2) | Satış fiyatı (TRY) | 599.99 |
| unit_cost | DECIMAL(12,2) | Maliyet (TRY) | 350.00 |
| stock_quantity | INTEGER | Stok miktarı | 150 |
| is_active | BOOLEAN | Satışta mı | true |
| created_at | TIMESTAMP | Oluşturulma tarihi | 2024-01-10 |
| brand | VARCHAR(100) | Marka | TechBrand |

## orders

| Sütun | Tip | Açıklama | Örnek |
|-------|-----|----------|-------|
| order_id | VARCHAR(20) | Sipariş numarası | ORD-000001 |
| customer_id | VARCHAR(36) | Müşteri FK | UUID |
| order_date | TIMESTAMP | Sipariş tarihi | 2024-06-15 |
| order_status | VARCHAR(20) | Durum | completed, cancelled, returned, pending |
| shipping_city | VARCHAR(100) | Teslimat şehri | Ankara |
| shipping_region | VARCHAR(100) | Teslimat bölgesi | İç Anadolu |
| order_channel | VARCHAR(50) | Sipariş kanalı | web, mobile_app, marketplace |
| discount_amount | DECIMAL(10,2) | İndirim tutarı | 25.00 |

## order_items

| Sütun | Tip | Açıklama | Örnek |
|-------|-----|----------|-------|
| order_item_id | VARCHAR(36) | Kalem UUID | UUID |
| order_id | VARCHAR(20) | Sipariş FK | ORD-000001 |
| product_id | VARCHAR(20) | Ürün FK | PRD-00001 |
| quantity | INTEGER | Adet | 2 |
| unit_price | DECIMAL(12,2) | Birim fiyat | 599.99 |
| line_total | DECIMAL(12,2) | Satır toplamı | 1199.98 |

## payments

| Sütun | Tip | Açıklama | Örnek |
|-------|-----|----------|-------|
| payment_id | VARCHAR(36) | Ödeme UUID | UUID |
| order_id | VARCHAR(20) | Sipariş FK | ORD-000001 |
| payment_date | TIMESTAMP | Ödeme tarihi | 2024-06-15 |
| payment_method | VARCHAR(50) | Ödeme yöntemi | credit_card, debit_card |
| payment_status | VARCHAR(20) | Durum | success, failed |
| currency | VARCHAR(3) | Para birimi | TRY |

## website_events

| Sütun | Tip | Açıklama | Örnek |
|-------|-----|----------|-------|
| event_id | VARCHAR(36) | Olay UUID | UUID |
| customer_id | VARCHAR(36) | Müşteri FK | UUID |
| event_type | VARCHAR(50) | Olay tipi | page_view, product_view, add_to_cart, purchase |
| event_timestamp | TIMESTAMP | Olay zamanı | 2024-06-15 14:30:00 |
| session_id | VARCHAR(20) | Oturum ID | abc12345 |
| channel | VARCHAR(50) | Trafik kanalı | organic, social_media |
| device_type | VARCHAR(20) | Cihaz | desktop, mobile, tablet |
| product_id | VARCHAR(20) | Ürün FK (opsiyonel) | PRD-00001 |
| page_url | VARCHAR(200) | Sayfa URL | /products |

## Türetilmiş Metrikler

| Metrik | Formül | Açıklama |
|--------|--------|----------|
| AOV | Toplam Gelir / Sipariş Sayısı | Ortalama sepet tutarı |
| CLV | Müşteri bazlı toplam harcama | Customer Lifetime Value |
| Churn | Son 90 günde sipariş yok | Müşteri kaybı |
| RFM Score | Recency + Frequency + Monetary quintile | Davranış skoru |
| Conversion Rate | Purchases / Sessions × 100 | Dönüşüm oranı |
| Repeat Rate | 2+ sipariş veren / toplam müşteri | Tekrar alış oranı |
