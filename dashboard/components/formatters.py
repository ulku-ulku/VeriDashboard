"""Sayı ve para formatlama yardımcıları."""


def format_currency_short(value: float) -> str:
    """Büyük tutarları okunaklı kısaltır."""
    value = float(value or 0)
    if value >= 1_000_000_000:
        return f"₺{value / 1_000_000_000:.2f}B"
    if value >= 1_000_000:
        return f"₺{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"₺{value / 1_000:.0f}K"
    return f"₺{value:,.0f}"


def format_count_short(value) -> str:
    value = int(float(value or 0))
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 10_000:
        return f"{value / 1_000:.0f}K"
    return f"{value:,}"
