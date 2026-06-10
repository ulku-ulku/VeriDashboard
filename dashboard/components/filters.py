"""Global dashboard filtreleri."""

import streamlit as st
import pandas as pd

from src.utils.data_access import DataFilters, get_date_bounds, get_filter_options


def init_session_state():
    """Session state varsayılanlarını ayarlar."""
    if "filters" not in st.session_state:
        min_date, max_date = get_date_bounds()
        st.session_state.filters = DataFilters(
            date_start=min_date,
            date_end=max_date,
        )


def render_sidebar_filters() -> DataFilters:
    """
    Sidebar'da global filtre panelini render eder.

    Returns:
        Aktif DataFilters nesnesi
    """
    init_session_state()
    options = get_filter_options()
    min_date, max_date = get_date_bounds()

    st.sidebar.markdown("### 🔎 Filtreler")

    col1, col2 = st.sidebar.columns(2)
    with col1:
        date_start = st.date_input(
            "Başlangıç",
            value=st.session_state.filters.date_start.date() if st.session_state.filters.date_start else min_date.date(),
            min_value=min_date.date(),
            max_value=max_date.date(),
        )
    with col2:
        date_end = st.date_input(
            "Bitiş",
            value=st.session_state.filters.date_end.date() if st.session_state.filters.date_end else max_date.date(),
            min_value=min_date.date(),
            max_value=max_date.date(),
        )

    regions = st.sidebar.multiselect("Bölge", options=options["regions"], default=[])
    channels = st.sidebar.multiselect("Sipariş Kanalı", options=options["channels"], default=[])
    categories = st.sidebar.multiselect("Ürün Kategorisi", options=options["categories"], default=[])

    if st.sidebar.button("Filtreleri Sıfırla", use_container_width=True):
        st.session_state.filters = DataFilters(date_start=min_date, date_end=max_date)
        st.rerun()

    filters = DataFilters(
        date_start=pd.Timestamp(date_start),
        date_end=pd.Timestamp(date_end) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1),
        regions=regions,
        channels=channels,
        categories=categories,
    )
    st.session_state.filters = filters
    return filters


def render_filter_badge(filters: DataFilters):
    """Aktif filtreleri badge olarak gösterir."""
    badges = []
    if filters.date_start and filters.date_end:
        badges.append(f"📅 {filters.date_start.strftime('%d.%m.%Y')} - {filters.date_end.strftime('%d.%m.%Y')}")
    if filters.regions:
        badges.append(f"🗺️ {len(filters.regions)} bölge")
    if filters.channels:
        badges.append(f"📱 {len(filters.channels)} kanal")
    if filters.categories:
        badges.append(f"📦 {len(filters.categories)} kategori")

    if badges:
        st.caption(" | ".join(badges))
