"""Yeniden kullanılabilir Plotly grafik bileşenleri."""

import pandas as pd
import plotly.graph_objects as go

REGION_COLORS = {
    "Marmara": "#667eea",
    "Ege": "#8b5cf6",
    "Akdeniz": "#f59e0b",
    "İç Anadolu": "#10b981",
    "Karadeniz": "#3b82f6",
    "Doğu Anadolu": "#ef4444",
    "Güneydoğu Anadolu": "#ec4899",
}

CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color="#334155"),
    margin=dict(l=10, r=10, t=40, b=10),
)


from dashboard.components.formatters import format_currency_short


def _prep_regional(df: pd.DataFrame) -> pd.DataFrame:
    """Bölgesel veriyi sıralar ve pay hesaplar."""
    data = df.sort_values("total_revenue", ascending=True).copy()
    total = data["total_revenue"].sum()
    data["revenue_share"] = (data["total_revenue"] / total * 100).round(1) if total else 0
    data["revenue_label"] = data.apply(
        lambda r: f"₺{r['total_revenue']/1e6:.1f}M · %{r['revenue_share']:.1f}",
        axis=1,
    )
    data["color"] = data["shipping_region"].map(REGION_COLORS).fillna("#94a3b8")
    return data


def build_regional_donut(df: pd.DataFrame, title: str = "Bölgesel Gelir Dağılımı") -> go.Figure:
    """
    Executive Summary için donut grafik.
    Toplam gelir üst başlıkta; dilimlerde bölge + pay etiketi.
    """
    data = df.sort_values("total_revenue", ascending=False).copy()
    total = data["total_revenue"].sum()
    colors = [REGION_COLORS.get(r, "#94a3b8") for r in data["shipping_region"]]

    # Kısa bölge etiketleri (uzun isimler taşmasın)
    short_labels = {
        "Güneydoğu Anadolu": "Güneydoğu",
        "Doğu Anadolu": "Doğu Anad.",
        "İç Anadolu": "İç Anadolu",
    }
    display_labels = data["shipping_region"].replace(short_labels)

    fig = go.Figure()
    fig.add_trace(go.Pie(
        labels=display_labels,
        values=data["total_revenue"],
        hole=0.48,
        marker=dict(colors=colors, line=dict(color="white", width=2)),
        textinfo="label+percent",
        textposition="inside",
        insidetextorientation="radial",
        textfont=dict(size=12, color="white", family="Inter, sans-serif"),
        hovertemplate=(
            "<b>%{customdata}</b><br>"
            "Gelir: ₺%{value:,.0f}<br>"
            "Pay: %{percent}"
            "<extra></extra>"
        ),
        customdata=data["shipping_region"],
        pull=[0.02 if i == 0 else 0 for i in range(len(data))],
    ))

    fig.update_layout(
        title=dict(
            text=f"<b>{title}</b><br><span style='font-size:22px;color:#1e293b'>{format_currency_short(total)}</span>"
                 f"<br><span style='font-size:12px;color:#64748b'>7 bölge toplam gelir</span>",
            x=0.5,
            xanchor="center",
            font=dict(size=14, color="#64748b"),
        ),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.08,
            xanchor="center",
            x=0.5,
            font=dict(size=11),
            itemsizing="constant",
        ),
        height=430,
        margin=dict(l=10, r=10, t=90, b=60),
        **{k: v for k, v in CHART_LAYOUT.items() if k != "margin"},
    )
    return fig


def build_regional_ranked_bars(df: pd.DataFrame, title: str = "Bölge Performans Sıralaması") -> go.Figure:
    """
    Bölgesel Harita sayfası için yatay sıralı bar + AOV çizgisi.
    """
    data = _prep_regional(df)

    fig = go.Figure()

    # Gelir barları
    fig.add_trace(go.Bar(
        y=data["shipping_region"],
        x=data["total_revenue"],
        orientation="h",
        name="Gelir",
        marker=dict(
            color=data["color"],
            line=dict(width=0),
            cornerradius=6,
        ),
        text=data["revenue_label"],
        textposition="outside",
        textfont=dict(size=11, color="#475569"),
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Gelir: ₺%{x:,.0f}<br>"
            "Sipariş: %{customdata[0]:,}<br>"
            "Müşteri: %{customdata[1]:,}<br>"
            "AOV: ₺%{customdata[2]:,.0f}"
            "<extra></extra>"
        ),
        customdata=data[["total_orders", "unique_customers", "avg_order_value"]].values,
    ))

    # AOV referans çizgileri (nokta)
    max_rev = data["total_revenue"].max()
    fig.add_trace(go.Scatter(
        y=data["shipping_region"],
        x=data["avg_order_value"] * (max_rev / data["avg_order_value"].max()) * 0.85,
        mode="markers",
        name="AOV (ölçekli)",
        marker=dict(symbol="diamond", size=10, color="white", line=dict(width=2, color="#1e293b")),
        hovertemplate="<b>%{y}</b><br>AOV: ₺%{customdata:,.0f}<extra></extra>",
        customdata=data["avg_order_value"],
    ))

    fig.update_layout(
        title=dict(text=title, font=dict(size=15, color="#1e293b")),
        xaxis=dict(
            title="Gelir (TRY)",
            gridcolor="#f1f5f9",
            showgrid=True,
            zeroline=False,
            tickformat=",.0f",
        ),
        yaxis=dict(title="", gridcolor="rgba(0,0,0,0)"),
        barmode="overlay",
        height=max(380, len(data) * 52),
        showlegend=False,
        **CHART_LAYOUT,
    )
    return fig


def build_regional_treemap(df: pd.DataFrame, title: str = "Bölgesel Gelir Haritası") -> go.Figure:
    """Treemap alternatif görünüm."""
    data = df.copy()
    data["label"] = data.apply(
        lambda r: f"{r['shipping_region']}<br>₺{r['total_revenue']/1e6:.1f}M",
        axis=1,
    )
    colors = [REGION_COLORS.get(r, "#94a3b8") for r in data["shipping_region"]]

    fig = go.Figure(go.Treemap(
        labels=data["shipping_region"],
        parents=[""] * len(data),
        values=data["total_revenue"],
        text=data["label"],
        textinfo="label+text",
        marker=dict(colors=colors, line=dict(width=2, color="white")),
        hovertemplate="<b>%{label}</b><br>Gelir: ₺%{value:,.0f}<extra></extra>",
    ))

    fig.update_layout(
        title=dict(text=title, font=dict(size=15, color="#1e293b")),
        height=380,
        **CHART_LAYOUT,
    )
    return fig
