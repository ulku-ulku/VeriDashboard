"""Gelişmiş dashboard teması ve CSS."""

ADVANCED_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .main-header {
        font-size: 2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.25rem;
    }

    .sub-header {
        font-size: 0.95rem;
        color: #64748b;
        margin-bottom: 1.5rem;
    }

    .kpi-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.25rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        transition: transform 0.2s, box-shadow 0.2s;
    }

    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
    }

    .kpi-value {
        font-size: 1.65rem;
        font-weight: 700;
        color: #1e293b;
        line-height: 1.2;
        word-break: keep-all;
        white-space: nowrap;
    }

    .kpi-label {
        font-size: 0.75rem;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        font-weight: 600;
        margin-bottom: 6px;
    }

    .kpi-delta-positive { color: #10b981; font-size: 0.85rem; font-weight: 600; }
    .kpi-delta-negative { color: #ef4444; font-size: 0.85rem; font-weight: 600; }

    .insight-box {
        background: linear-gradient(135deg, #f0f4ff 0%, #faf5ff 100%);
        border-left: 4px solid #667eea;
        padding: 1rem 1.25rem;
        border-radius: 0 8px 8px 0;
        margin: 1rem 0;
    }

    .risk-critical { background: #fef2f2; color: #991b1b; padding: 2px 8px; border-radius: 4px; }
    .risk-high { background: #fff7ed; color: #c2410c; padding: 2px 8px; border-radius: 4px; }
    .risk-medium { background: #fefce8; color: #a16207; padding: 2px 8px; border-radius: 4px; }
    .risk-low { background: #f0fdf4; color: #166534; padding: 2px 8px; border-radius: 4px; }

    div[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e293b 0%, #334155 100%);
    }

    div[data-testid="stSidebar"] .stRadio label {
        color: #e2e8f0 !important;
    }

    .stMetric {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        border: 1px solid #e2e8f0;
    }
</style>
"""

REGION_COORDS = {
    "Marmara": [40.8, 29.0],
    "Ege": [38.4, 27.1],
    "Akdeniz": [36.9, 30.7],
    "İç Anadolu": [39.9, 32.8],
    "Karadeniz": [41.0, 36.0],
    "Doğu Anadolu": [39.9, 41.3],
    "Güneydoğu Anadolu": [37.1, 38.8],
}

RISK_COLORS = {
    "Kritik": "#ef4444",
    "Yüksek": "#f97316",
    "Orta": "#eab308",
    "Düşük": "#22c55e",
}
