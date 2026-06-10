-- ============================================================
-- E-Ticaret Analytics - İleri Seviye SQL Sorguları (20+)
-- Window Functions, CTE, Cohort, RFM Analizi
-- ============================================================

-- ------------------------------------------------------------
-- SORGU 1: Aylık Satış Trendi (Window Function - Running Total)
-- ------------------------------------------------------------
-- Aylık gelir ve kümülatif toplam satış trendi
WITH monthly_sales AS (
    SELECT
        DATE_TRUNC('month', o.order_date) AS sales_month,
        SUM(oi.line_total) AS monthly_revenue,
        COUNT(DISTINCT o.order_id) AS order_count,
        COUNT(DISTINCT o.customer_id) AS unique_customers
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.order_status = 'completed'
    GROUP BY DATE_TRUNC('month', o.order_date)
)
SELECT
    sales_month,
    monthly_revenue,
    order_count,
    unique_customers,
    SUM(monthly_revenue) OVER (ORDER BY sales_month) AS cumulative_revenue,
    LAG(monthly_revenue) OVER (ORDER BY sales_month) AS prev_month_revenue,
    ROUND(
        (monthly_revenue - LAG(monthly_revenue) OVER (ORDER BY sales_month))
        / NULLIF(LAG(monthly_revenue) OVER (ORDER BY sales_month), 0) * 100, 2
    ) AS mom_growth_pct
FROM monthly_sales
ORDER BY sales_month;

-- ------------------------------------------------------------
-- SORGU 2: En Karlı Ürünler (CTE + Margin Hesaplama)
-- ------------------------------------------------------------
WITH product_metrics AS (
    SELECT
        p.product_id,
        p.product_name,
        p.category,
        p.unit_price,
        p.unit_cost,
        SUM(oi.quantity) AS total_quantity_sold,
        SUM(oi.line_total) AS total_revenue,
        SUM(oi.quantity * p.unit_cost) AS total_cost,
        SUM(oi.line_total) - SUM(oi.quantity * p.unit_cost) AS gross_profit
    FROM products p
    JOIN order_items oi ON p.product_id = oi.product_id
    JOIN orders o ON oi.order_id = o.order_id
    WHERE o.order_status = 'completed'
    GROUP BY p.product_id, p.product_name, p.category, p.unit_price, p.unit_cost
)
SELECT
    product_id,
    product_name,
    category,
    total_quantity_sold,
    total_revenue,
    gross_profit,
    ROUND(gross_profit / NULLIF(total_revenue, 0) * 100, 2) AS profit_margin_pct,
    RANK() OVER (ORDER BY gross_profit DESC) AS profit_rank
FROM product_metrics
ORDER BY gross_profit DESC
LIMIT 20;

-- ------------------------------------------------------------
-- SORGU 3: RFM Analizi (Recency, Frequency, Monetary)
-- ------------------------------------------------------------
WITH customer_rfm AS (
    SELECT
        c.customer_id,
        c.customer_segment,
        c.region,
        MAX(o.order_date) AS last_order_date,
        CURRENT_DATE - MAX(o.order_date::date) AS recency_days,
        COUNT(DISTINCT o.order_id) AS frequency,
        SUM(oi.line_total) AS monetary
    FROM customers c
    LEFT JOIN orders o ON c.customer_id = o.customer_id AND o.order_status = 'completed'
    LEFT JOIN order_items oi ON o.order_id = oi.order_id
    GROUP BY c.customer_id, c.customer_segment, c.region
),
rfm_scores AS (
    SELECT
        customer_id,
        customer_segment,
        region,
        recency_days,
        frequency,
        monetary,
        NTILE(5) OVER (ORDER BY recency_days ASC) AS r_score,
        NTILE(5) OVER (ORDER BY frequency DESC) AS f_score,
        NTILE(5) OVER (ORDER BY monetary DESC) AS m_score
    FROM customer_rfm
    WHERE frequency > 0
)
SELECT
    customer_id,
    region,
    recency_days,
    frequency,
    ROUND(monetary, 2) AS monetary,
    r_score,
    f_score,
    m_score,
    r_score + f_score + m_score AS rfm_total_score,
    CASE
        WHEN r_score >= 4 AND f_score >= 4 THEN 'Champions'
        WHEN r_score >= 3 AND f_score >= 3 THEN 'Loyal Customers'
        WHEN r_score >= 4 AND f_score <= 2 THEN 'New Customers'
        WHEN r_score <= 2 AND f_score >= 3 THEN 'At Risk'
        WHEN r_score <= 2 AND f_score <= 2 THEN 'Lost'
        ELSE 'Potential Loyalists'
    END AS rfm_segment
FROM rfm_scores
ORDER BY rfm_total_score DESC;

-- ------------------------------------------------------------
-- SORGU 4: Cohort Analizi (Aylık Kayıt Kohortları)
-- ------------------------------------------------------------
WITH customer_cohorts AS (
    SELECT
        customer_id,
        DATE_TRUNC('month', registration_date) AS cohort_month
    FROM customers
),
order_periods AS (
    SELECT
        o.customer_id,
        cc.cohort_month,
        DATE_TRUNC('month', o.order_date) AS order_month,
        SUM(oi.line_total) AS revenue
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    JOIN customer_cohorts cc ON o.customer_id = cc.customer_id
    WHERE o.order_status = 'completed'
    GROUP BY o.customer_id, cc.cohort_month, DATE_TRUNC('month', o.order_date)
),
cohort_size AS (
    SELECT cohort_month, COUNT(DISTINCT customer_id) AS cohort_customers
    FROM customer_cohorts
    GROUP BY cohort_month
)
SELECT
    op.cohort_month,
    cs.cohort_customers,
    EXTRACT(MONTH FROM AGE(op.order_month, op.cohort_month)) AS period_number,
    COUNT(DISTINCT op.customer_id) AS active_customers,
    ROUND(COUNT(DISTINCT op.customer_id)::numeric / cs.cohort_customers * 100, 2) AS retention_rate,
    ROUND(SUM(op.revenue), 2) AS cohort_revenue
FROM order_periods op
JOIN cohort_size cs ON op.cohort_month = cs.cohort_month
GROUP BY op.cohort_month, cs.cohort_customers, period_number
ORDER BY op.cohort_month, period_number;

-- ------------------------------------------------------------
-- SORGU 5: Ortalama Sepet Tutarı (AOV) - Bölgesel
-- ------------------------------------------------------------
SELECT
    o.shipping_region,
    COUNT(DISTINCT o.order_id) AS total_orders,
    ROUND(AVG(order_totals.total), 2) AS avg_order_value,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY order_totals.total), 2) AS median_order_value,
    ROUND(STDDEV(order_totals.total), 2) AS stddev_order_value
FROM orders o
JOIN (
    SELECT order_id, SUM(line_total) AS total
    FROM order_items
    GROUP BY order_id
) order_totals ON o.order_id = order_totals.order_id
WHERE o.order_status = 'completed'
GROUP BY o.shipping_region
ORDER BY avg_order_value DESC;

-- ------------------------------------------------------------
-- SORGU 6: Tekrar Satın Alma Oranı
-- ------------------------------------------------------------
WITH customer_order_counts AS (
    SELECT
        customer_id,
        COUNT(DISTINCT order_id) AS order_count
    FROM orders
    WHERE order_status = 'completed'
    GROUP BY customer_id
)
SELECT
    COUNT(*) AS total_customers_with_orders,
    SUM(CASE WHEN order_count = 1 THEN 1 ELSE 0 END) AS one_time_buyers,
    SUM(CASE WHEN order_count >= 2 THEN 1 ELSE 0 END) AS repeat_buyers,
    ROUND(
        SUM(CASE WHEN order_count >= 2 THEN 1 ELSE 0 END)::numeric
        / NULLIF(COUNT(*), 0) * 100, 2
    ) AS repeat_purchase_rate_pct
FROM customer_order_counts;

-- ------------------------------------------------------------
-- SORGU 7: Kanal Bazlı Dönüşüm Oranları
-- ------------------------------------------------------------
WITH funnel AS (
    SELECT
        channel,
        COUNT(DISTINCT CASE WHEN event_type = 'page_view' THEN session_id END) AS sessions,
        COUNT(DISTINCT CASE WHEN event_type = 'product_view' THEN session_id END) AS product_views,
        COUNT(DISTINCT CASE WHEN event_type = 'add_to_cart' THEN session_id END) AS add_to_carts,
        COUNT(DISTINCT CASE WHEN event_type = 'purchase' THEN session_id END) AS purchases
    FROM website_events
    GROUP BY channel
)
SELECT
    channel,
    sessions,
    product_views,
    add_to_carts,
    purchases,
    ROUND(product_views::numeric / NULLIF(sessions, 0) * 100, 2) AS view_rate_pct,
    ROUND(add_to_carts::numeric / NULLIF(product_views, 0) * 100, 2) AS cart_rate_pct,
    ROUND(purchases::numeric / NULLIF(sessions, 0) * 100, 2) AS conversion_rate_pct
FROM funnel
ORDER BY conversion_rate_pct DESC;

-- ------------------------------------------------------------
-- SORGU 8: Müşteri Yaşam Boyu Değeri (CLV)
-- ------------------------------------------------------------
WITH customer_clv AS (
    SELECT
        c.customer_id,
        c.customer_segment,
        c.region,
        COUNT(DISTINCT o.order_id) AS total_orders,
        SUM(oi.line_total) AS total_spent,
        MIN(o.order_date) AS first_order,
        MAX(o.order_date) AS last_order,
        EXTRACT(DAY FROM MAX(o.order_date) - MIN(o.order_date)) AS customer_lifetime_days
    FROM customers c
    JOIN orders o ON c.customer_id = o.customer_id
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.order_status = 'completed'
    GROUP BY c.customer_id, c.customer_segment, c.region
)
SELECT
    customer_segment,
    region,
    COUNT(*) AS customer_count,
    ROUND(AVG(total_spent), 2) AS avg_clv,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY total_spent), 2) AS median_clv,
    ROUND(AVG(total_orders), 2) AS avg_orders,
    ROUND(AVG(customer_lifetime_days), 0) AS avg_lifetime_days
FROM customer_clv
GROUP BY customer_segment, region
ORDER BY avg_clv DESC;

-- ------------------------------------------------------------
-- SORGU 9: Churn Risk Skorlaması (SQL Tabanlı)
-- ------------------------------------------------------------
WITH customer_activity AS (
    SELECT
        c.customer_id,
        c.customer_segment,
        c.registration_date,
        MAX(o.order_date) AS last_order_date,
        CURRENT_DATE - MAX(o.order_date::date) AS days_since_last_order,
        COUNT(DISTINCT o.order_id) AS total_orders,
        COALESCE(SUM(oi.line_total), 0) AS total_spent
    FROM customers c
    LEFT JOIN orders o ON c.customer_id = o.customer_id AND o.order_status = 'completed'
    LEFT JOIN order_items oi ON o.order_id = oi.order_id
    GROUP BY c.customer_id, c.customer_segment, c.registration_date
)
SELECT
    customer_id,
    customer_segment,
    days_since_last_order,
    total_orders,
    ROUND(total_spent, 2) AS total_spent,
    CASE WHEN days_since_last_order > 90 OR days_since_last_order IS NULL THEN 1 ELSE 0 END AS is_churned,
    CASE
        WHEN days_since_last_order IS NULL THEN 'Never Purchased'
        WHEN days_since_last_order > 180 THEN 'High Risk'
        WHEN days_since_last_order > 90 THEN 'Medium Risk'
        WHEN days_since_last_order > 30 THEN 'Low Risk'
        ELSE 'Active'
    END AS churn_risk_level
FROM customer_activity
ORDER BY days_since_last_order DESC NULLS FIRST;

-- ------------------------------------------------------------
-- SORGU 10: Ürün Kategori Performansı (YoY Karşılaştırma)
-- ------------------------------------------------------------
WITH category_monthly AS (
    SELECT
        p.category,
        DATE_TRUNC('month', o.order_date) AS sales_month,
        SUM(oi.line_total) AS revenue,
        SUM(oi.quantity) AS units_sold
    FROM products p
    JOIN order_items oi ON p.product_id = oi.product_id
    JOIN orders o ON oi.order_id = o.order_id
    WHERE o.order_status = 'completed'
    GROUP BY p.category, DATE_TRUNC('month', o.order_date)
)
SELECT
    category,
    sales_month,
    revenue,
    units_sold,
    LAG(revenue) OVER (PARTITION BY category ORDER BY sales_month) AS prev_month_revenue,
    ROUND(
        (revenue - LAG(revenue) OVER (PARTITION BY category ORDER BY sales_month))
        / NULLIF(LAG(revenue) OVER (PARTITION BY category ORDER BY sales_month), 0) * 100, 2
    ) AS mom_growth_pct,
    SUM(revenue) OVER (PARTITION BY category ORDER BY sales_month) AS cumulative_category_revenue
FROM category_monthly
ORDER BY category, sales_month;

-- ------------------------------------------------------------
-- SORGU 11: Ödeme Yöntemi Analizi
-- ------------------------------------------------------------
SELECT
    p.payment_method,
    COUNT(*) AS transaction_count,
    ROUND(COUNT(*)::numeric / SUM(COUNT(*)) OVER () * 100, 2) AS pct_of_total,
    SUM(CASE WHEN p.payment_status = 'success' THEN 1 ELSE 0 END) AS successful,
    ROUND(
        SUM(CASE WHEN p.payment_status = 'success' THEN 1 ELSE 0 END)::numeric
        / NULLIF(COUNT(*), 0) * 100, 2
    ) AS success_rate_pct
FROM payments p
GROUP BY p.payment_method
ORDER BY transaction_count DESC;

-- ------------------------------------------------------------
-- SORGU 12: Sipariş Kanalı Performansı
-- ------------------------------------------------------------
WITH channel_metrics AS (
    SELECT
        o.order_channel,
        COUNT(DISTINCT o.order_id) AS orders,
        SUM(oi.line_total) AS revenue,
        AVG(oi.line_total) AS avg_item_value
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.order_status = 'completed'
    GROUP BY o.order_channel
)
SELECT
    order_channel,
    orders,
    ROUND(revenue, 2) AS revenue,
    ROUND(revenue / NULLIF(orders, 0), 2) AS revenue_per_order,
    ROUND(orders::numeric / SUM(orders) OVER () * 100, 2) AS order_share_pct,
    RANK() OVER (ORDER BY revenue DESC) AS channel_rank
FROM channel_metrics;

-- ------------------------------------------------------------
-- SORGU 13: Müşteri Segmentasyonu - Demografik
-- ------------------------------------------------------------
SELECT
    c.gender,
    c.customer_segment,
    COUNT(DISTINCT c.customer_id) AS customer_count,
    ROUND(AVG(EXTRACT(YEAR FROM CURRENT_DATE) - c.birth_year), 1) AS avg_age,
    ROUND(AVG(customer_stats.total_spent), 2) AS avg_spent,
    ROUND(AVG(customer_stats.order_count), 2) AS avg_orders
FROM customers c
LEFT JOIN (
    SELECT
        o.customer_id,
        COUNT(DISTINCT o.order_id) AS order_count,
        SUM(oi.line_total) AS total_spent
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.order_status = 'completed'
    GROUP BY o.customer_id
) customer_stats ON c.customer_id = customer_stats.customer_id
GROUP BY c.gender, c.customer_segment
ORDER BY avg_spent DESC NULLS LAST;

-- ------------------------------------------------------------
-- SORGU 14: Haftalık Satış Deseni (Seasonality)
-- ------------------------------------------------------------
SELECT
    EXTRACT(DOW FROM o.order_date) AS day_of_week,
    TO_CHAR(o.order_date, 'Day') AS day_name,
    COUNT(DISTINCT o.order_id) AS order_count,
    ROUND(SUM(oi.line_total), 2) AS total_revenue,
    ROUND(AVG(order_totals.total), 2) AS avg_order_value
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
JOIN (
    SELECT order_id, SUM(line_total) AS total FROM order_items GROUP BY order_id
) order_totals ON o.order_id = order_totals.order_id
WHERE o.order_status = 'completed'
GROUP BY EXTRACT(DOW FROM o.order_date), TO_CHAR(o.order_date, 'Day')
ORDER BY day_of_week;

-- ------------------------------------------------------------
-- SORGU 15: Cross-Sell Analizi (Birlikte Satın Alınan Ürünler)
-- ------------------------------------------------------------
WITH product_pairs AS (
    SELECT
        oi1.product_id AS product_a,
        oi2.product_id AS product_b,
        COUNT(DISTINCT oi1.order_id) AS co_occurrence
    FROM order_items oi1
    JOIN order_items oi2 ON oi1.order_id = oi2.order_id AND oi1.product_id < oi2.product_id
    JOIN orders o ON oi1.order_id = o.order_id
    WHERE o.order_status = 'completed'
    GROUP BY oi1.product_id, oi2.product_id
    HAVING COUNT(DISTINCT oi1.order_id) >= 5
)
SELECT
    pa.product_name AS product_a_name,
    pa.category AS product_a_category,
    pb.product_name AS product_b_name,
    pb.category AS product_b_category,
    pp.co_occurrence,
    RANK() OVER (ORDER BY pp.co_occurrence DESC) AS pair_rank
FROM product_pairs pp
JOIN products pa ON pp.product_a = pa.product_id
JOIN products pb ON pp.product_b = pb.product_id
ORDER BY co_occurrence DESC
LIMIT 20;

-- ------------------------------------------------------------
-- SORGU 16: İade/İptal Oranı Analizi
-- ------------------------------------------------------------
SELECT
    DATE_TRUNC('month', order_date) AS order_month,
    COUNT(*) AS total_orders,
    SUM(CASE WHEN order_status = 'completed' THEN 1 ELSE 0 END) AS completed,
    SUM(CASE WHEN order_status = 'cancelled' THEN 1 ELSE 0 END) AS cancelled,
    SUM(CASE WHEN order_status = 'returned' THEN 1 ELSE 0 END) AS returned,
    ROUND(
        SUM(CASE WHEN order_status IN ('cancelled', 'returned') THEN 1 ELSE 0 END)::numeric
        / NULLIF(COUNT(*), 0) * 100, 2
    ) AS churn_order_rate_pct
FROM orders
GROUP BY DATE_TRUNC('month', order_date)
ORDER BY order_month;

-- ------------------------------------------------------------
-- SORGU 17: Müşteri Edinme Maliyeti Simülasyonu (Kanal Bazlı)
-- ------------------------------------------------------------
WITH channel_acquisition AS (
    SELECT
        registration_channel,
        COUNT(DISTINCT customer_id) AS new_customers,
        COUNT(DISTINCT CASE WHEN order_count > 0 THEN customer_id END) AS converted_customers
    FROM (
        SELECT
            c.customer_id,
            c.registration_channel,
            COUNT(DISTINCT o.order_id) AS order_count
        FROM customers c
        LEFT JOIN orders o ON c.customer_id = o.customer_id AND o.order_status = 'completed'
        GROUP BY c.customer_id, c.registration_channel
    ) sub
    GROUP BY registration_channel
)
SELECT
    registration_channel,
    new_customers,
    converted_customers,
    ROUND(converted_customers::numeric / NULLIF(new_customers, 0) * 100, 2) AS conversion_rate_pct,
    RANK() OVER (ORDER BY converted_customers::numeric / NULLIF(new_customers, 0) DESC) AS channel_efficiency_rank
FROM channel_acquisition
ORDER BY conversion_rate_pct DESC;

-- ------------------------------------------------------------
-- SORGU 18: Stok Devir Hızı
-- ------------------------------------------------------------
SELECT
    p.category,
    COUNT(DISTINCT p.product_id) AS product_count,
    SUM(p.stock_quantity) AS total_stock,
    SUM(oi.quantity) AS total_sold,
    ROUND(SUM(oi.quantity)::numeric / NULLIF(SUM(p.stock_quantity), 0), 2) AS turnover_ratio,
    ROUND(AVG(p.stock_quantity), 0) AS avg_stock_per_product
FROM products p
LEFT JOIN order_items oi ON p.product_id = oi.product_id
LEFT JOIN orders o ON oi.order_id = o.order_id AND o.order_status = 'completed'
GROUP BY p.category
ORDER BY turnover_ratio DESC NULLS LAST;

-- ------------------------------------------------------------
-- SORGU 19: Session Depth Analizi (Web Analytics)
-- ------------------------------------------------------------
WITH session_stats AS (
    SELECT
        session_id,
        channel,
        device_type,
        COUNT(*) AS events_per_session,
        COUNT(DISTINCT event_type) AS unique_event_types,
        MIN(event_timestamp) AS session_start,
        MAX(event_timestamp) AS session_end,
        EXTRACT(EPOCH FROM MAX(event_timestamp) - MIN(event_timestamp)) AS session_duration_sec
    FROM website_events
    GROUP BY session_id, channel, device_type
)
SELECT
    channel,
    device_type,
    COUNT(*) AS session_count,
    ROUND(AVG(events_per_session), 2) AS avg_events,
    ROUND(AVG(session_duration_sec), 0) AS avg_duration_sec,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY events_per_session), 0) AS median_events
FROM session_stats
GROUP BY channel, device_type
ORDER BY session_count DESC;

-- ------------------------------------------------------------
-- SORGU 20: Moving Average Satış Tahmini (SQL)
-- ------------------------------------------------------------
WITH daily_revenue AS (
    SELECT
        DATE_TRUNC('day', o.order_date) AS sales_date,
        SUM(oi.line_total) AS daily_revenue
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.order_status = 'completed'
    GROUP BY DATE_TRUNC('day', o.order_date)
)
SELECT
    sales_date,
    daily_revenue,
    ROUND(AVG(daily_revenue) OVER (
        ORDER BY sales_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ), 2) AS ma_7_day,
    ROUND(AVG(daily_revenue) OVER (
        ORDER BY sales_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    ), 2) AS ma_30_day,
    ROUND(
        AVG(daily_revenue) OVER (ORDER BY sales_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)
        - AVG(daily_revenue) OVER (ORDER BY sales_date ROWS BETWEEN 13 PRECEDING AND 7 PRECEDING),
        2
    ) AS ma_7_trend
FROM daily_revenue
ORDER BY sales_date;

-- ------------------------------------------------------------
-- SORGU 21: Pareto Analizi (80/20 Kuralı)
-- ------------------------------------------------------------
WITH product_revenue AS (
    SELECT
        p.product_id,
        p.product_name,
        p.category,
        SUM(oi.line_total) AS revenue
    FROM products p
    JOIN order_items oi ON p.product_id = oi.product_id
    JOIN orders o ON oi.order_id = o.order_id
    WHERE o.order_status = 'completed'
    GROUP BY p.product_id, p.product_name, p.category
),
ranked AS (
    SELECT
        *,
        SUM(revenue) OVER () AS total_revenue,
        SUM(revenue) OVER (ORDER BY revenue DESC) AS cumulative_revenue,
        ROW_NUMBER() OVER (ORDER BY revenue DESC) AS product_rank
    FROM product_revenue
)
SELECT
    product_id,
    product_name,
    category,
    ROUND(revenue, 2) AS revenue,
    product_rank,
    ROUND(cumulative_revenue / NULLIF(total_revenue, 0) * 100, 2) AS cumulative_pct,
    CASE
        WHEN cumulative_revenue / NULLIF(total_revenue, 0) <= 0.80 THEN 'Top 80%'
        ELSE 'Bottom 20%'
    END AS pareto_group
FROM ranked
ORDER BY product_rank
LIMIT 50;

-- ------------------------------------------------------------
-- SORGU 22: Müşteri Sipariş Aralığı Analizi
-- ------------------------------------------------------------
WITH order_gaps AS (
    SELECT
        customer_id,
        order_date,
        order_date - LAG(order_date) OVER (PARTITION BY customer_id ORDER BY order_date) AS days_between_orders
    FROM orders
    WHERE order_status = 'completed'
)
SELECT
    CASE
        WHEN days_between_orders IS NULL THEN 'First Order'
        WHEN days_between_orders <= 7 THEN 'Within 1 Week'
        WHEN days_between_orders <= 30 THEN 'Within 1 Month'
        WHEN days_between_orders <= 90 THEN 'Within 3 Months'
        ELSE 'Over 3 Months'
    END AS order_gap_bucket,
    COUNT(*) AS occurrence_count,
    ROUND(AVG(EXTRACT(DAY FROM days_between_orders)), 1) AS avg_days
FROM order_gaps
GROUP BY 1
ORDER BY occurrence_count DESC;
