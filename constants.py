# constants.py

# ======================
# Color Definitions (Centralize all chart colors here)
# ======================
COLORS = {
    "revenue": "#FFA500",              # orange
    "gross_profit": "#1f77b4",         # blue
    "gross_profit_percent": "#800080" , # purple
    "customer_count": "#27ae60"  # ✅ Add this line (green)
}

# ======================
# Month Order (for sorting consistently across all charts)
# ======================
MONTH_ORDER = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
]

# ======================
# Metric Display Names (for unified naming across charts)
# ======================
METRIC_LABELS = {
    "adjusted_revenue_usd": "Revenue (USD)",
    "invoiced_gross_profit_usd": "Gross Profit (USD)"
}

METRIC_ORDER = ["Revenue (USD)", "Gross Profit (USD)"]

# ======================
# Chart Size Settings (centralize all size configs)
# ======================
CHART_WIDTH = 700
CHART_HEIGHT = 400

PIE_CHART_WIDTH = 300
PIE_CHART_HEIGHT = 300
