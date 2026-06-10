"""KPI kart bileşenleri."""

import streamlit as st


def _format_currency_short(value) -> str:
    value = float(value or 0)
    if value >= 1_000_000_000:
        return f"₺{value / 1_000_000_000:.2f}B"
    if value >= 1_000_000:
        return f"₺{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"₺{value / 1_000:.0f}K"
    return f"₺{value:,.0f}"


def _format_count_short(value) -> str:
    value = int(float(value or 0))
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 10_000:
        return f"{value / 1_000:.0f}K"
    return f"{value:,}"


def render_executive_summary_panel(kpis, growth=None):
    """Executive Summary üst paneli."""
    with st.container(border=True):
        st.markdown("**Dönem Özeti**")
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            st.metric("Toplam Gelir", _format_currency_short(kpis.get("total_revenue", 0)))
        with c2:
            st.metric("Toplam Sipariş", _format_count_short(kpis.get("total_orders", 0)))
        with c3:
            st.metric("Müşteri", _format_count_short(kpis.get("total_customers", 0)))
        with c4:
            st.metric("Ort. Sepet", _format_currency_short(kpis.get("average_order_value", 0)))
        with c5:
            st.metric("Tekrar Alış", f"%{float(kpis.get('repeat_purchase_rate', 0)):.1f}")

        if growth:
            st.divider()
            st.caption(f"Son tam ay: {growth.get('comparison_label', '')}")
            g1, g2, g3, g4 = st.columns(4)
            with g1:
                st.metric(
                    "Son Ay Geliri",
                    _format_currency_short(growth.get("latest_month_revenue", 0)),
                    delta=f"{growth.get('mom_revenue_growth', 0):+.1f}% MoM",
                )
            with g2:
                st.metric(
                    "Son Ay Sipariş",
                    _format_count_short(growth.get("latest_month_orders", 0)),
                    delta=f"{growth.get('mom_order_growth', 0):+.1f}% MoM",
                )
            with g3:
                st.metric("MoM Gelir", f"%{growth.get('mom_revenue_growth', 0):.1f}")
            with g4:
                st.metric("YoY Gelir", f"%{growth.get('yoy_revenue_growth', 0):.1f}")


def render_kpi_row(kpis, growth=None):
    render_executive_summary_panel(kpis, growth)


def render_growth_cards(growth):
    pass


def render_insight_box(title, text):
    st.markdown(
        f'<div class="insight-box"><strong>{title}</strong><br>{text}</div>',
        unsafe_allow_html=True,
    )
