import altair as alt
import pandas as pd
from constants import COLORS, CHART_WIDTH, CHART_HEIGHT, METRIC_LABELS, METRIC_ORDER, MONTH_ORDER, PIE_CHART_WIDTH, PIE_CHART_HEIGHT

def build_monthly_revenue_gp_chart(monthly_summary_df: pd.DataFrame, exclude_internal: bool):
    """
    Build combined bar + line chart for monthly revenue and gross profit.

    Args:
        monthly_summary_df (DataFrame): Pre-processed monthly summary.
        exclude_internal (bool): Whether INTERNAL sales were excluded (for title).

    Returns:
        Altair chart.
    """

    # Melt into long format for bars
    monthly_melted = pd.melt(
        monthly_summary_df,
        id_vars=["invoice_month"],
        value_vars=["adjusted_revenue_usd", "invoiced_gross_profit_usd"],
        var_name="Metric",
        value_name="Amount"
    )

    # Rename metrics
    monthly_melted["Metric"] = monthly_melted["Metric"].map(METRIC_LABELS)

    # Ensure correct order
    monthly_melted["Metric"] = pd.Categorical(
        monthly_melted["Metric"],
        categories=METRIC_ORDER,
        ordered=True
    )


    # Bar chart
    bar_chart = alt.Chart(monthly_melted).mark_bar().encode(
        x=alt.X("invoice_month:N", title="Invoice Month", sort=MONTH_ORDER),
        y=alt.Y("Amount:Q", title="Amount (USD)", axis=alt.Axis(format="~s")),
        color=alt.Color("Metric:N", scale=alt.Scale(
            domain=METRIC_ORDER,
            range=[COLORS["revenue"], COLORS["gross_profit"]]
        )),
        xOffset=alt.XOffset("Metric:N", sort=METRIC_ORDER),
        tooltip=[
            alt.Tooltip("invoice_month:N", title="Month"),
            alt.Tooltip("Metric:N", title="Metric"),
            alt.Tooltip("Amount:Q", title="Amount", format=",.0f")
        ]
    )

    # Line chart for GP %
    line_chart = alt.Chart(monthly_summary_df).mark_line(
        point=True,
        color=COLORS["gross_profit_percent"]
    ).encode(
        x=alt.X("invoice_month:N", sort=MONTH_ORDER),
        y=alt.Y(
            "gp_percent:Q",
            title="Gross Profit %",
            axis=alt.Axis(format=".1f", titleColor=COLORS["gross_profit_percent"])
        ),
        tooltip=[
            alt.Tooltip("invoice_month:N", title="Month"),
            alt.Tooltip("gp_percent:Q", title="Gross Profit %", format=".2f")
        ]
    )

    # Combine
    combined_chart = alt.layer(
        bar_chart,
        line_chart
    ).resolve_scale(
        y='independent'
    ).properties(
        width=CHART_WIDTH,
        height=CHART_HEIGHT,
        title=f"📅 Monthly Revenue, Gross Profit, and GP% ({'Excl. Internal' if exclude_internal else 'Incl. Internal'})"
    )

    return combined_chart


def build_territory_pie_charts(summary_df: pd.DataFrame):
    """
    Build side-by-side pie charts for Revenue and Gross Profit by Territory.

    Args:
        summary_df (DataFrame): Territory summary data.

    Returns:
        Altair Chart: Combined side-by-side pie charts.
    """
    # Revenue Pie
    revenue_pie_chart = alt.Chart(summary_df).mark_arc().encode(
        theta=alt.Theta(field="Revenue", type="quantitative"),
        color=alt.Color(field="Center", type="nominal"),
        tooltip=[
            alt.Tooltip("Center:N", title="Territory"),
            alt.Tooltip("Revenue:Q", title="Revenue (USD)", format=",.0f"),
            alt.Tooltip("Percent_x:Q", title="Percentage", format=".2f")
        ]
    ).properties(
        width=PIE_CHART_WIDTH,
        height=PIE_CHART_HEIGHT,
        title="🌍 Revenue Breakdown by Territory"
    )

    # Gross Profit Pie
    gp_pie_chart = alt.Chart(summary_df).mark_arc().encode(
        theta=alt.Theta(field="GrossProfit", type="quantitative"),
        color=alt.Color(field="Center", type="nominal"),
        tooltip=[
            alt.Tooltip("Center:N", title="Territory"),
            alt.Tooltip("GrossProfit:Q", title="Gross Profit (USD)", format=",.0f"),
            alt.Tooltip("Percent_y:Q", title="Percentage", format=".2f")
        ]
    ).properties(
        width=PIE_CHART_WIDTH,
        height=PIE_CHART_HEIGHT,
        title="🌍 Gross Profit Breakdown by Territory"
    )

    return revenue_pie_chart | gp_pie_chart


def build_territory_bar_chart(summary_df: pd.DataFrame):
    """
    Build bar + line chart for Revenue, Gross Profit, and GP% by Territory.

    Args:
        summary_df (DataFrame): Territory summary data.

    Returns:
        Altair Chart
    """
    melted = pd.melt(
        summary_df,
        id_vars=["Center"],
        value_vars=["Revenue", "GrossProfit"],
        var_name="Metric",
        value_name="Amount"
    )

    color_scale = alt.Scale(
        domain=["Revenue", "GrossProfit"],
        range=[COLORS["revenue"], COLORS["gross_profit"]]
    )

    bar_chart = alt.Chart(melted).mark_bar().encode(
        x=alt.X("Center:N", title="Territory", sort="-y"),
        y=alt.Y("Amount:Q", title="Amount (USD)", axis=alt.Axis(format="~s")),
        color=alt.Color("Metric:N", scale=color_scale, title="Metric"),
        xOffset=alt.XOffset("Metric:N"),
        tooltip=[
            alt.Tooltip("Center:N", title="Territory"),
            alt.Tooltip("Metric:N", title="Metric"),
            alt.Tooltip("Amount:Q", title="Amount", format=",.0f")
        ]
    )

    line_chart = alt.Chart(summary_df).mark_line(point=True, color="#800080").encode(
        x=alt.X("Center:N", sort="-y"),
        y=alt.Y(
            "GP_Percent:Q",
            title="Gross Profit %",
            axis=alt.Axis(format=".1f", titleColor="#800080")
        ),
        tooltip=[
            alt.Tooltip("Center:N", title="Territory"),
            alt.Tooltip("GP_Percent:Q", title="Gross Profit %", format=".2f")
        ]
    )

    return alt.layer(bar_chart, line_chart).resolve_scale(y='independent').properties(
        width=CHART_WIDTH,
        height=CHART_HEIGHT,
        title="📊 Revenue, Gross Profit, and GP % by Territory"
    )
