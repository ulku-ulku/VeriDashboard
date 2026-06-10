-- E-Ticaret Analytics Platform - Veritabanı Şeması
-- PostgreSQL 16+

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- CUSTOMERS: Müşteri master verisi
-- ============================================================
CREATE TABLE IF NOT EXISTS customers (
    customer_id         VARCHAR(36) PRIMARY KEY,
    first_name          VARCHAR(100),
    last_name           VARCHAR(100),
    email               VARCHAR(255),
    phone               VARCHAR(50),
    city                VARCHAR(100),
    region              VARCHAR(100),
    registration_date   TIMESTAMP,
    registration_channel VARCHAR(50),
    customer_segment    VARCHAR(50),
    is_active           BOOLEAN DEFAULT TRUE,
    birth_year          INTEGER,
    gender              VARCHAR(20),
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_customers_region ON customers(region);
CREATE INDEX IF NOT EXISTS idx_customers_segment ON customers(customer_segment);
CREATE INDEX IF NOT EXISTS idx_customers_registration ON customers(registration_date);

-- ============================================================
-- PRODUCTS: Ürün kataloğu
-- ============================================================
CREATE TABLE IF NOT EXISTS products (
    product_id      VARCHAR(20) PRIMARY KEY,
    product_name    VARCHAR(200),
    category        VARCHAR(100),
    subcategory     VARCHAR(100),
    unit_price      DECIMAL(12, 2),
    unit_cost       DECIMAL(12, 2),
    stock_quantity  INTEGER,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP,
    brand           VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);

-- ============================================================
-- ORDERS: Sipariş başlıkları
-- ============================================================
CREATE TABLE IF NOT EXISTS orders (
    order_id        VARCHAR(20) PRIMARY KEY,
    customer_id     VARCHAR(36) REFERENCES customers(customer_id),
    order_date      TIMESTAMP,
    order_status    VARCHAR(20),
    shipping_city   VARCHAR(100),
    shipping_region VARCHAR(100),
    order_channel   VARCHAR(50),
    discount_amount DECIMAL(10, 2) DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(order_date);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(order_status);
CREATE INDEX IF NOT EXISTS idx_orders_region ON orders(shipping_region);

-- ============================================================
-- ORDER_ITEMS: Sipariş kalemleri
-- ============================================================
CREATE TABLE IF NOT EXISTS order_items (
    order_item_id   VARCHAR(36) PRIMARY KEY,
    order_id        VARCHAR(20) REFERENCES orders(order_id),
    product_id      VARCHAR(20) REFERENCES products(product_id),
    quantity        INTEGER,
    unit_price      DECIMAL(12, 2),
    line_total      DECIMAL(12, 2)
);

CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product ON order_items(product_id);

-- ============================================================
-- PAYMENTS: Ödeme kayıtları
-- ============================================================
CREATE TABLE IF NOT EXISTS payments (
    payment_id      VARCHAR(36) PRIMARY KEY,
    order_id        VARCHAR(20) REFERENCES orders(order_id),
    payment_date    TIMESTAMP,
    payment_method  VARCHAR(50),
    payment_status  VARCHAR(20),
    currency        VARCHAR(3) DEFAULT 'TRY'
);

CREATE INDEX IF NOT EXISTS idx_payments_order ON payments(order_id);
CREATE INDEX IF NOT EXISTS idx_payments_date ON payments(payment_date);

-- ============================================================
-- WEBSITE_EVENTS: Web etkileşim olayları
-- ============================================================
CREATE TABLE IF NOT EXISTS website_events (
    event_id        VARCHAR(36) PRIMARY KEY,
    customer_id     VARCHAR(36) REFERENCES customers(customer_id),
    event_type      VARCHAR(50),
    event_timestamp TIMESTAMP,
    session_id      VARCHAR(20),
    channel         VARCHAR(50),
    device_type     VARCHAR(20),
    product_id      VARCHAR(20),
    page_url        VARCHAR(200)
);

CREATE INDEX IF NOT EXISTS idx_events_customer ON website_events(customer_id);
CREATE INDEX IF NOT EXISTS idx_events_type ON website_events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON website_events(event_timestamp);
CREATE INDEX IF NOT EXISTS idx_events_channel ON website_events(channel);

-- ============================================================
-- ANALYTICS VIEWS: Sık kullanılan analitik görünümler
-- ============================================================
CREATE OR REPLACE VIEW v_order_summary AS
SELECT
    o.order_id,
    o.customer_id,
    o.order_date,
    o.order_status,
    o.shipping_region,
    o.order_channel,
    o.discount_amount,
    SUM(oi.line_total) AS order_total,
    COUNT(oi.order_item_id) AS item_count
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.order_status = 'completed'
GROUP BY o.order_id, o.customer_id, o.order_date, o.order_status,
         o.shipping_region, o.order_channel, o.discount_amount;
