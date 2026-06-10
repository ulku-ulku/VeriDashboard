"""
E-Ticaret Analytics Platform v2.0
Gelişmiş Streamlit Dashboard — filtreler, CLV, yolculuk hunisi, churn skorlama
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.components.charts import build_regional_ranked_bars, build_regional_treemap
from dashboard.components.filters import render_filter_badge, render_sidebar_filters
from dashboard.components.theme import ADVANCED_CSS, REGION_COORDS, RISK_COLORS
from dashboard.data_loader import (
    check_data_availability,
    filter_cache_key,
    get_data_quality_summary,
    load_anomalies,
    load_basket_analysis,
    load_channel_conversion,
    load_churn_metrics,
    load_churn_scores,
    load_clv_analysis,
    load_cohort_analysis,
    load_csv,
    load_forecast_metrics,
    load_growth_metrics,
    load_hourly_patterns,
    load_journey_funnel,
    load_kpi_summary,
    load_payment_analysis,
    load_regional_performance,
    load_rfm_analysis,
    load_sales_trends,
    load_top_products,
    serialize_filters,
)
from src.config import REPORTS_DIR

# ── Sayfa yapılandırması ──────────────────────────────────────
st.set_page_config(
    page_title="E-Ticaret Analytics Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(ADVANCED_CSS, unsafe_allow_html=True)


# ── KPI panel (app.py icinde — import sorunlarini onler) ─────
def _fmt_currency(value) -> str:
    value = float(value or 0)
    if value >= 1_000_000_000:
        return f"₺{value / 1_000_000_000:.2f}B"
    if value >= 1_000_000:
        return f"₺{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"₺{value / 1_000:.0f}K"
    return f"₺{value:,.0f}"


def _fmt_count(value) -> str:
    value = int(float(value or 0))
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 10_000:
        return f"{value / 1_000:.0f}K"
    return f"{value:,}"


def render_executive_summary_panel(kpis, growth=None):
    with st.container(border=True):
        st.markdown("**Dönem Özeti**")
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            st.metric("Toplam Gelir", _fmt_currency(kpis.get("total_revenue", 0)))
        with c2:
            st.metric("Toplam Sipariş", _fmt_count(kpis.get("total_orders", 0)))
        with c3:
            st.metric("Müşteri", _fmt_count(kpis.get("total_customers", 0)))
        with c4:
            st.metric("Ort. Sepet", _fmt_currency(kpis.get("average_order_value", 0)))
        with c5:
            st.metric("Tekrar Alış", f"%{float(kpis.get('repeat_purchase_rate', 0)):.1f}")

        if growth:
            st.divider()
            st.caption(f"Son tam ay: {growth.get('comparison_label', '')}")
            g1, g2, g3, g4 = st.columns(4)
            with g1:
                st.metric(
                    "Son Ay Geliri",
                    _fmt_currency(growth.get("latest_month_revenue", 0)),
                    delta=f"{growth.get('mom_revenue_growth', 0):+.1f}% MoM",
                )
            with g2:
                st.metric(
                    "Son Ay Sipariş",
                    _fmt_count(growth.get("latest_month_orders", 0)),
                    delta=f"{growth.get('mom_order_growth', 0):+.1f}% MoM",
                )
            with g3:
                st.metric("MoM Gelir", f"%{growth.get('mom_revenue_growth', 0):.1f}")
            with g4:
                st.metric("YoY Gelir", f"%{growth.get('yoy_revenue_growth', 0):.1f}")


def render_insight_box(title, text):
    st.markdown(
        f'<div class="insight-box"><strong>{title}</strong><br>{text}</div>',
        unsafe_allow_html=True,
    )


def _fk(filters) -> tuple[str, str]:
    """Cache key + serialized filters."""
    fj = serialize_filters(filters)
    return filter_cache_key(filters), fj


# ── SAYFA: Executive Summary ─────────────────────────────────
def page_executive_summary(filters):
    st.markdown('<p class="main-header">Executive Summary</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Gerçek zamanlı KPI ve büyüme metrikleri</p>', unsafe_allow_html=True)
    render_filter_badge(filters)

    key, fj = _fk(filters)
    kpis = load_kpi_summary(key, fj)
    growth = load_growth_metrics(key, fj)

    render_executive_summary_panel(kpis, growth)

    mom = growth.get("mom_revenue_growth", 0)
    comp = growth.get("comparison_label", "")
    if mom > 5:
        render_insight_box("📈 Pozitif Trend", f"{comp}: gelir %{mom:.1f} arttı.")
    elif mom < -10:
        render_insight_box("📉 Dikkat", f"{comp}: gelir %{abs(mom):.1f} düştü.")

    trends = load_sales_trends(key, fj)
    regional = load_regional_performance(key, fj)

    if not trends.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=trends["sales_month"], y=trends["revenue"],
            mode="lines+markers", name="Gelir", line=dict(color="#667eea", width=3),
            fill="tozeroy", fillcolor="rgba(102,126,234,0.1)",
        ))
        if "gross_profit" in trends.columns:
            fig.add_trace(go.Scatter(
                x=trends["sales_month"], y=trends["gross_profit"],
                mode="lines", name="Brüt Kar", line=dict(color="#10b981", dash="dot"),
            ))
        fig.update_layout(
            title="Aylık Gelir & Kar Trendi",
            hovermode="x unified",
            height=380,
            yaxis=dict(tickformat=".2s", title="TRY"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
            margin=dict(l=40, r=20, t=60, b=40),
        )
        st.plotly_chart(fig, use_container_width=True)

    if not regional.empty:
        st.plotly_chart(
            build_regional_ranked_bars(regional, title="Bölgesel Gelir Dağılımı"),
            use_container_width=True,
        )


# ── SAYFA: Satış Analizi ─────────────────────────────────────
def page_sales_analysis(filters):
    st.markdown('<p class="main-header">Satış Analizi</p>', unsafe_allow_html=True)
    render_filter_badge(filters)
    key, fj = _fk(filters)

    tab1, tab2, tab3, tab4 = st.tabs(["Trend", "Ürünler", "Kanal Dönüşümü", "Ödeme"])

    with tab1:
        trends = load_sales_trends(key, fj)
        if not trends.empty:
            fig = go.Figure()
            fig.add_trace(go.Bar(x=trends["sales_month"], y=trends["order_count"], name="Sipariş", marker_color="#764ba2"))
            fig.add_trace(go.Scatter(x=trends["sales_month"], y=trends["revenue"], name="Gelir", yaxis="y2", mode="lines+markers", line=dict(color="#667eea")))
            fig.update_layout(
                title="Aylık Sipariş & Gelir", yaxis=dict(title="Sipariş"),
                yaxis2=dict(title="Gelir (TRY)", overlaying="y", side="right"), height=420,
            )
            st.plotly_chart(fig, use_container_width=True)

        hourly, daily = load_hourly_patterns(key, fj)
        if hourly is not None and not hourly.empty:
            c1, c2 = st.columns(2)
            with c1:
                fig_h = px.area(hourly, x="hour", y="revenue", title="Saatlik Satış Deseni", color_discrete_sequence=["#667eea"])
                st.plotly_chart(fig_h, use_container_width=True)
            with c2:
                fig_d = px.bar(daily, x="day_name", y="revenue", title="Günlük Satış Deseni", color="revenue", color_continuous_scale="Blues")
                st.plotly_chart(fig_d, use_container_width=True)

    with tab2:
        top = load_top_products(key, fj, 15)
        if not top.empty:
            fig = px.bar(top.head(10), x="gross_profit", y="product_name", orientation="h",
                         color="category", title="En Karlı 10 Ürün")
            fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=450)
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(top, use_container_width=True, hide_index=True)

    with tab3:
        conv = load_channel_conversion(key, fj)
        if not conv.empty:
            st.dataframe(conv, use_container_width=True, hide_index=True)
            fig2 = px.bar(conv, x="channel", y="conversion_rate_pct", color="conversion_rate_pct",
                          title="Kanal Dönüşüm Oranı (%)", color_continuous_scale="Greens")
            st.plotly_chart(fig2, use_container_width=True)
            fig3 = px.funnel(conv, x="sessions", y="channel", title="Oturum Hunisi")
            st.plotly_chart(fig3, use_container_width=True)

    with tab4:
        payments = load_payment_analysis(key, fj)
        if not payments.empty:
            c1, c2 = st.columns(2)
            with c1:
                fig = px.pie(payments, values="total_volume", names="payment_method", title="Ödeme Hacmi Dağılımı", hole=0.4)
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                fig2 = px.bar(payments, x="payment_method", y="success_rate", title="Başarı Oranı (%)", color="success_rate", color_continuous_scale="RdYlGn")
                st.plotly_chart(fig2, use_container_width=True)


# ── SAYFA: Müşteri Analizi ───────────────────────────────────
def page_customer_analysis(filters):
    st.markdown('<p class="main-header">Müşteri Analizi</p>', unsafe_allow_html=True)
    key, fj = _fk(filters)

    tab1, tab2, tab3 = st.tabs(["RFM", "Cohort", "CLV"])

    with tab1:
        rfm = load_rfm_analysis()
        if not rfm.empty:
            c1, c2 = st.columns(2)
            with c1:
                seg = rfm["rfm_segment"].value_counts().reset_index()
                seg.columns = ["Segment", "Sayı"]
                fig = px.treemap(seg, path=["Segment"], values="Sayı", color="Sayı", color_continuous_scale="Viridis", title="RFM Segmentleri")
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                fig2 = px.scatter(rfm, x="recency_days", y="monetary", color="rfm_segment", size="frequency",
                                  hover_data=["customer_id"], title="RFM Haritası")
                st.plotly_chart(fig2, use_container_width=True)

    with tab2:
        cohort = load_cohort_analysis()
        if not cohort.empty:
            cohort["cohort_month"] = cohort["cohort_month"].astype(str)
            pivot = cohort.pivot_table(index="cohort_month", columns="period_number", values="retention_rate", aggfunc="first")
            fig = px.imshow(pivot.values, x=pivot.columns.astype(str), y=pivot.index,
                            color_continuous_scale="RdYlGn", title="Cohort Retention (%)", aspect="auto")
            st.plotly_chart(fig, use_container_width=True)

    with tab3:
        clv = load_clv_analysis(key, fj)
        if not clv.empty:
            c1, c2 = st.columns(2)
            with c1:
                tier_rev = clv.groupby("clv_tier")["total_spent"].sum().reset_index()
                fig = px.funnel(tier_rev, x="total_spent", y="clv_tier", title="CLV Tier Gelir Hunisi")
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                fig2 = px.box(clv, x="clv_tier", y="total_spent", color="clv_tier", title="Tier Bazlı Harcama Dağılımı")
                st.plotly_chart(fig2, use_container_width=True)
            st.dataframe(clv.nlargest(20, "total_spent"), use_container_width=True, hide_index=True)


# ── SAYFA: Müşteri Yolculuğu ─────────────────────────────────
def page_customer_journey(filters):
    st.markdown('<p class="main-header">Müşteri Yolculuğu</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Dönüşüm hunisi ve sepet analizi</p>', unsafe_allow_html=True)
    render_filter_badge(filters)
    key, fj = _fk(filters)

    funnel = load_journey_funnel(key, fj)
    if not funnel.empty:
        fig = go.Figure(go.Funnel(
            y=funnel["stage"], x=funnel["sessions"],
            textinfo="value+percent initial+percent previous",
            marker=dict(color=["#667eea", "#764ba2", "#a855f7", "#10b981"]),
        ))
        fig.update_layout(title="Dönüşüm Hunisi", height=450)
        st.plotly_chart(fig, use_container_width=True)

        c1, c2 = st.columns(2)
        with c1:
            st.dataframe(funnel, use_container_width=True, hide_index=True)
        with c2:
            fig2 = px.bar(funnel, x="stage", y="conversion_from_top", title="Toplam Dönüşüm (%)", color="conversion_from_top", color_continuous_scale="Blues")
            st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Market Basket — Birlikte Satın Alınan Ürünler")
    basket = load_basket_analysis(key, fj)
    if not basket.empty:
        st.dataframe(basket, use_container_width=True, hide_index=True)
    else:
        st.info("Sepet analizi için yeterli veri yok.")


# ── SAYFA: Gelişmiş Analitik ─────────────────────────────────
def page_advanced_analytics(filters):
    st.markdown('<p class="main-header">Gelişmiş Analitik</p>', unsafe_allow_html=True)
    render_filter_badge(filters)
    key, fj = _fk(filters)

    tab1, tab2 = st.tabs(["Anomali Tespiti", "Büyüme Analizi"])

    with tab1:
        anomalies = load_anomalies(key, fj)
        if not anomalies.empty:
            render_insight_box("⚠️ Anomali Tespit Edildi", f"{len(anomalies)} günde olağandışı satış aktivitesi bulundu.")
            st.dataframe(anomalies, use_container_width=True, hide_index=True)

            merged = load_sales_trends(key, fj)
            if not merged.empty:
                fig = px.line(merged, x="sales_month", y="revenue", title="Aylık Gelir Trendi", markers=True)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.success("Seçilen dönemde anomali tespit edilmedi.")

    with tab2:
        growth = load_growth_metrics(key, fj)
        if growth:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("MoM Gelir", f"%{growth.get('mom_revenue_growth', 0):.1f}")
            c2.metric("MoM Sipariş", f"%{growth.get('mom_order_growth', 0):.1f}")
            c3.metric("YoY Gelir", f"%{growth.get('yoy_revenue_growth', 0):.1f}")
            c4.metric("Son Ay Gelir", f"₺{growth.get('latest_month_revenue', 0):,.0f}")


# ── SAYFA: Churn Tahmini ─────────────────────────────────────
def page_churn_prediction():
    st.markdown('<p class="main-header">Churn Tahmini</p>', unsafe_allow_html=True)

    metrics = load_churn_metrics()
    scores = load_churn_scores()

    if not metrics:
        st.warning("Model henüz eğitilmedi.")
        if st.button("Modeli Eğit + Skorla"):
            with st.spinner("Eğitiliyor..."):
                from src.ml.churn_prediction import main as train
                from src.ml.churn_scoring import export_churn_scores
                train()
                export_churn_scores()
                st.cache_data.clear()
                st.rerun()
        return

    c1, c2 = st.columns(2)
    for idx, (name, m) in enumerate(metrics.items()):
        with c1 if idx == 0 else c2:
            st.subheader(name.replace("_", " ").title())
            st.metric("ROC-AUC", f"{m.get('roc_auc', 0):.4f}")
            st.metric("Accuracy", f"{m.get('accuracy', 0):.4f}")
            if "cv_roc_auc_mean" in m:
                st.metric("CV ROC-AUC", f"{m['cv_roc_auc_mean']:.4f} ± {m.get('cv_roc_auc_std', 0):.4f}")
            if "feature_importance" in m:
                fi_df = pd.DataFrame(list(m["feature_importance"].items()), columns=["Feature", "Importance"])
                fig = px.bar(fi_df.head(10), x="Importance", y="Feature", orientation="h", title="Feature Importance")
                fig.update_layout(yaxis={"categoryorder": "total ascending"})
                st.plotly_chart(fig, use_container_width=True)

    roc_path = REPORTS_DIR / "roc_curves.png"
    if roc_path.exists():
        st.image(str(roc_path), use_container_width=True)

    st.divider()
    st.subheader("Müşteri Risk Listesi")

    if scores.empty:
        if st.button("Müşterileri Skorla"):
            with st.spinner("Skorlanıyor..."):
                from src.ml.churn_scoring import export_churn_scores
                export_churn_scores()
                st.cache_data.clear()
                st.rerun()
    else:
        risk_filter = st.multiselect("Risk Seviyesi", ["Kritik", "Yüksek", "Orta", "Düşük"], default=["Kritik", "Yüksek"])
        filtered = scores[scores["risk_level"].isin(risk_filter)] if risk_filter else scores

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Kritik", f"{(scores['risk_level'] == 'Kritik').sum():,}")
        c2.metric("Yüksek", f"{(scores['risk_level'] == 'Yüksek').sum():,}")
        c3.metric("Orta", f"{(scores['risk_level'] == 'Orta').sum():,}")
        c4.metric("Ort. Olasılık", f"{scores['churn_probability'].mean():.2%}")

        fig = px.histogram(scores, x="churn_probability", color="risk_level", title="Churn Olasılık Dağılımı",
                           color_discrete_map=RISK_COLORS, nbins=40)
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(filtered.head(100), use_container_width=True, hide_index=True)
        st.download_button(
            "CSV İndir",
            filtered.to_csv(index=False).encode("utf-8"),
            "churn_risk_listesi.csv",
            "text/csv",
        )


# ── SAYFA: Gelir Tahmini ─────────────────────────────────────
def page_revenue_forecast():
    st.markdown('<p class="main-header">Gelir Tahmini</p>', unsafe_allow_html=True)
    forecast = load_forecast_metrics()

    if not forecast:
        st.warning("Tahmin modeli henüz eğitilmedi.")
        if st.button("Tahmin Modelini Eğit"):
            with st.spinner("Eğitiliyor..."):
                from src.forecasting.revenue_forecast import main
                main()
                st.rerun()
        return

    c1, c2 = st.columns(2)
    for idx, (name, data) in enumerate(forecast.items()):
        with c1 if idx == 0 else c2:
            st.subheader(name.upper())
            m = data.get("metrics", {})
            st.metric("MAPE", f"%{m.get('mape', 0):.2f}")
            st.metric("RMSE", f"₺{m.get('rmse', 0):,.0f}")
            fc = data.get("forecast", [])
            if fc:
                fc_df = pd.DataFrame(fc)
                fig = px.line(fc_df, x="date", y="predicted_revenue", title=f"{name.upper()} — 6 Aylık Tahmin", markers=True)
                if "lower_bound" in fc_df.columns:
                    fig.add_traces([
                        go.Scatter(x=fc_df["date"], y=fc_df["upper_bound"], mode="lines", line=dict(width=0), showlegend=False),
                        go.Scatter(x=fc_df["date"], y=fc_df["lower_bound"], fill="tonexty", mode="lines", line=dict(width=0), name="Güven Aralığı"),
                    ])
                st.plotly_chart(fig, use_container_width=True)

    img = REPORTS_DIR / "revenue_forecast.png"
    if img.exists():
        st.image(str(img), use_container_width=True)


# ── SAYFA: Ürün Performansı ──────────────────────────────────
def page_product_performance(filters):
    st.markdown('<p class="main-header">Ürün Performansı</p>', unsafe_allow_html=True)
    render_filter_badge(filters)
    key, fj = _fk(filters)
    top = load_top_products(key, fj, 30)

    if top.empty:
        st.warning("Veri bulunamadı.")
        return

    c1, c2 = st.columns(2)
    with c1:
        cat = top.groupby("category").agg(revenue=("total_revenue", "sum"), profit=("gross_profit", "sum")).reset_index()
        fig = px.sunburst(cat, path=["category"], values="revenue", color="profit", title="Kategori Gelir & Kar")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig2 = px.scatter(top, x="total_revenue", y="gross_profit", size="total_quantity", color="category",
                          hover_data=["product_name"], title="Gelir vs Kar")
        st.plotly_chart(fig2, use_container_width=True)
    st.dataframe(top, use_container_width=True, hide_index=True)


# ── SAYFA: Bölgesel Harita ───────────────────────────────────
def page_regional_map(filters):
    st.markdown('<p class="main-header">Bölgesel Performans</p>', unsafe_allow_html=True)
    key, fj = _fk(filters)
    regional = load_regional_performance(key, fj)

    if regional.empty:
        st.warning("Veri bulunamadı.")
        return

    import folium
    from streamlit_folium import st_folium

    m = folium.Map(location=[39.0, 35.0], zoom_start=6, tiles="CartoDB positron")
    max_rev = regional["total_revenue"].max()
    for _, row in regional.iterrows():
        coords = REGION_COORDS.get(row["shipping_region"], [39.0, 35.0])
        folium.CircleMarker(
            location=coords, radius=max(10, row["total_revenue"] / max_rev * 50),
            popup=f"<b>{row['shipping_region']}</b><br>Gelir: ₺{row['total_revenue']:,.0f}<br>AOV: ₺{row['avg_order_value']:,.0f}",
            color="#667eea", fill=True, fill_color="#764ba2", fill_opacity=0.7,
        ).add_to(m)
    st_folium(m, width=900, height=500)

    st.divider()
    tab_bars, tab_treemap = st.tabs(["Sıralama", "Treemap"])
    with tab_bars:
        st.plotly_chart(
            build_regional_ranked_bars(regional, title="Bölge Performans Sıralaması"),
            use_container_width=True,
        )
    with tab_treemap:
        st.plotly_chart(
            build_regional_treemap(regional, title="Bölgesel Gelir Haritası"),
            use_container_width=True,
        )


# ── SAYFA: Veri Kalitesi ─────────────────────────────────────
def page_data_quality():
    st.markdown('<p class="main-header">Veri Kalitesi</p>', unsafe_allow_html=True)
    quality = get_data_quality_summary()
    if not quality:
        st.warning("Veri bulunamadı.")
        return

    qdf = pd.DataFrame({
        k: {kk: vv for kk, vv in v.items() if kk not in ("missing_details", "validation_details")}
        for k, v in quality.items()
    }).T.reset_index()
    qdf.columns = ["Tablo", "Satır", "Eksik Sütun", "Aykırı Değer", "Doğrulama Hatası", "Durum"]
    qdf["Durum"] = qdf["Durum"].map({True: "✅ Geçti", False: "❌ Hata"})

    passed = qdf["Durum"].str.contains("Geçti").sum()
    st.metric("Kalite Skoru", f"{passed}/{len(qdf)} tablo geçti")
    st.dataframe(qdf, use_container_width=True, hide_index=True)

    for table, info in quality.items():
        if info.get("validation_details"):
            with st.expander(f"⚠️ {table} — doğrulama detayları"):
                for err in info["validation_details"]:
                    st.write(f"- {err}")


# ── ANA UYGULAMA ─────────────────────────────────────────────
def main():
    st.sidebar.markdown("## 📊 Analytics Pro")
    st.sidebar.caption("v2.0 — Gelişmiş Platform")

    if not check_data_availability():
        st.error("Veri bulunamadı. `python -m src.data_generation.generate_data` çalıştırın.")
        if st.sidebar.button("Veri Üret"):
            with st.spinner("Üretiliyor..."):
                from src.data_generation.generate_data import main as gen
                gen()
                st.cache_data.clear()
                st.rerun()
        return

    filters = render_sidebar_filters()
    st.sidebar.markdown("---")

    pages = {
        "🏠 Executive Summary": lambda: page_executive_summary(filters),
        "💰 Satış Analizi": lambda: page_sales_analysis(filters),
        "👥 Müşteri Analizi": lambda: page_customer_analysis(filters),
        "🛤️ Müşteri Yolculuğu": lambda: page_customer_journey(filters),
        "🔬 Gelişmiş Analitik": lambda: page_advanced_analytics(filters),
        "⚠️ Churn Tahmini": page_churn_prediction,
        "📈 Gelir Tahmini": page_revenue_forecast,
        "📦 Ürün Performansı": lambda: page_product_performance(filters),
        "🗺️ Bölgesel Harita": lambda: page_regional_map(filters),
        "🔍 Veri Kalitesi": page_data_quality,
    }

    selection = st.sidebar.radio("Navigasyon", list(pages.keys()), label_visibility="collapsed")
    pages[selection]()


if __name__ == "__main__":
    main()
