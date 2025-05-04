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
    monthly_melted = pd.melt(
        monthly_summary_df,
        id_vars=["invoice_month"],
        value_vars=["adjusted_revenue_usd", "invoiced_gross_profit_usd"],
        var_name="Metric",
        value_name="Amount"
    )

    monthly_melted["Metric"] = monthly_melted["Metric"].map(METRIC_LABELS)

    monthly_melted["Metric"] = pd.Categorical(
        monthly_melted["Metric"],
        categories=METRIC_ORDER,
        ordered=True
    )

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


def build_dimension_pie_charts(summary_df: pd.DataFrame, dimension_name: str):
    """
    Build side-by-side pie charts for Revenue and Gross Profit by a given dimension (Territory or Vertical).

    Args:
        summary_df (DataFrame): Summary data.
        dimension_name (str): Dimension label for chart titles.

    Returns:
        Altair Chart: Combined side-by-side pie charts.
    """
    revenue_pie_chart = alt.Chart(summary_df).mark_arc().encode(
        theta=alt.Theta(field="Revenue", type="quantitative"),
        color=alt.Color(field="Center", type="nominal"),
        tooltip=[
            alt.Tooltip("Center:N", title=dimension_name),
            alt.Tooltip("Revenue:Q", title="Revenue (USD)", format=",.0f"),
            alt.Tooltip("Percent_Revenue:Q", title="Percentage", format=".2f")
        ]
    ).properties(
        width=PIE_CHART_WIDTH,
        height=PIE_CHART_HEIGHT,
        title=f"🌍 Revenue Breakdown by {dimension_name}"
    )

    gp_pie_chart = alt.Chart(summary_df).mark_arc().encode(
        theta=alt.Theta(field="GrossProfit", type="quantitative"),
        color=alt.Color(field="Center", type="nominal"),
        tooltip=[
            alt.Tooltip("Center:N", title=dimension_name),
            alt.Tooltip("GrossProfit:Q", title="Gross Profit (USD)", format=",.0f"),
            alt.Tooltip("Percent_GP:Q", title="Percentage", format=".2f")
        ]
    ).properties(
        width=PIE_CHART_WIDTH,
        height=PIE_CHART_HEIGHT,
        title=f"🌍 Gross Profit Breakdown by {dimension_name}"
    )

    return revenue_pie_chart | gp_pie_chart


def build_dimension_bar_chart(summary_df: pd.DataFrame, dimension_name: str):
    """
    Build bar + line chart for Revenue, Gross Profit, and GP% by a given dimension (Territory or Vertical).

    Args:
        summary_df (DataFrame): Summary data.
        dimension_name (str): Dimension label for chart titles.

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
        x=alt.X("Center:N", title=dimension_name, sort="-y"),
        y=alt.Y("Amount:Q", title="Amount (USD)", axis=alt.Axis(format="~s")),
        color=alt.Color("Metric:N", scale=color_scale, title="Metric"),
        xOffset=alt.XOffset("Metric:N", sort=METRIC_ORDER),
        tooltip=[
            alt.Tooltip("Center:N", title=dimension_name),
            alt.Tooltip("Metric:N", title="Metric"),
            alt.Tooltip("Amount:Q", title="Amount", format=",.0f")
        ]
    )

    line_chart = alt.Chart(summary_df).mark_line(point=True, color=COLORS["gross_profit_percent"]).encode(
        x=alt.X("Center:N", sort="-y"),
        y=alt.Y(
            "GP_Percent:Q",
            title="Gross Profit %",
            axis=alt.Axis(format=".1f", titleColor=COLORS["gross_profit_percent"])
        ),
        tooltip=[
            alt.Tooltip("Center:N", title=dimension_name),
            alt.Tooltip("GP_Percent:Q", title="Gross Profit %", format=".2f")
        ]
    )

    return alt.layer(bar_chart, line_chart).resolve_scale(y='independent').properties(
        width=CHART_WIDTH,
        height=CHART_HEIGHT,
        title=f"📊 Revenue, Gross Profit, and GP % by {dimension_name}"
    )
