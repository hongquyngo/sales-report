import altair as alt
import pandas as pd
from constants import COLORS, CHART_WIDTH, CHART_HEIGHT, METRIC_LABELS, METRIC_ORDER, MONTH_ORDER, PIE_CHART_WIDTH, PIE_CHART_HEIGHT


def build_salesperson_top_customers_gp_chart(top_customers_df: pd.DataFrame, salesperson_name: str):
    """
    Build combined bar + line chart for top customers by gross profit (for a specific salesperson).

    Args:
        top_customers_df (DataFrame): Top customers data with GrossProfit, cumulative %, etc.
        salesperson_name (str): Salesperson name for chart title.

    Returns:
        Altair Chart
    """
    if top_customers_df.empty:
        return alt.Chart(pd.DataFrame({'note': ["No data available"]})).mark_text(
            text="No data available", size=20, color="red"
        ).properties(height=200)

    # Bar chart (Gross Profit)
    bar_chart = alt.Chart(top_customers_df).mark_bar().encode(
        x=alt.X("customer:N", sort="-y", title="Customer"),
        y=alt.Y("GrossProfit:Q", title="Gross Profit (USD)", axis=alt.Axis(format="~s")),
        color=alt.value(COLORS["gross_profit"]),
        tooltip=[
            alt.Tooltip("customer:N", title="Customer"),
            alt.Tooltip("GrossProfit:Q", title="Gross Profit", format=",.0f"),
            alt.Tooltip("GP_Percent:Q", title="GP %", format=".2f")
        ]
    ).properties(
        width=CHART_WIDTH,
        height=CHART_HEIGHT
    )

    # Line chart (Cumulative %)
    line_chart = alt.Chart(top_customers_df).mark_line(point=True, color=COLORS["gross_profit_percent"]).encode(
        x=alt.X("customer:N", sort="-y"),
        y=alt.Y("cumulative_percent:Q", title="Cumulative %", axis=alt.Axis(format=".0%")),
        tooltip=[
            alt.Tooltip("customer:N", title="Customer"),
            alt.Tooltip("cumulative_percent:Q", title="Cumulative %", format=".2%")
        ]
    )

    combined_chart = alt.layer(
        bar_chart,
        line_chart
    ).resolve_scale(
        y='independent'
    ).properties(
        title=f"🏆 Top 80% Customers by Gross Profit for {salesperson_name}"
    )

    return combined_chart


def build_salesperson_cumulative_chart(cumulative_df: pd.DataFrame, salesperson_name: str):
    """
    Build a Cumulative Revenue & GP Chart for the selected salesperson.
    """
    # Melt data to long format
    cumulative_melted = cumulative_df.melt(
        id_vars=["invoice_month"],
        value_vars=["Cumulative Revenue", "Cumulative Gross Profit"],
        var_name="Metric",
        value_name="Amount"
    )

    METRIC_ORDER = ["Cumulative Revenue", "Cumulative Gross Profit"]

    chart = alt.Chart(cumulative_melted).mark_line(point=True).encode(
        x=alt.X("invoice_month:N", title="Month", sort=MONTH_ORDER),
        y=alt.Y("Amount:Q", title="Cumulative Amount (USD)", axis=alt.Axis(format="~s")),
        color=alt.Color(
            "Metric:N",
            scale=alt.Scale(
                domain=METRIC_ORDER,
                range=[COLORS["revenue"], COLORS["gross_profit"]]
            ),
            legend=alt.Legend(title="Metric")
        ),
        tooltip=[
            alt.Tooltip("invoice_month:N", title="Month"),
            alt.Tooltip("Metric:N", title="Metric"),
            alt.Tooltip("Amount:Q", title="Amount", format=",.0f")
        ]
    ).properties(
        width=CHART_WIDTH,
        height=CHART_HEIGHT,
        title=f"📈 Cumulative Revenue & Gross Profit Chart for {salesperson_name}"
    )

    return chart


def build_salesperson_monthly_chart(monthly_df: pd.DataFrame, salesperson_name: str):
    """
    Build the Monthly Revenue, Gross Profit, GP%, and Customer Count Chart for a salesperson.

    Args:
        monthly_df (DataFrame): Data prepared from prepare_salesperson_monthly_summary_data.
        salesperson_name (str): Name of the salesperson for the title.

    Returns:
        Altair Chart
    """
    # ✅ Melt data for bar chart (Revenue + GP)
    monthly_melted = pd.melt(
        monthly_df,
        id_vars=['invoice_month'],
        value_vars=['sales_by_split_usd', 'gross_profit_by_split_usd'],
        var_name='Metric',
        value_name='Amount'
    )

    metric_label_map = {
        "sales_by_split_usd": "Revenue (USD)",
        "gross_profit_by_split_usd": "Gross Profit (USD)"
    }
    monthly_melted["Metric"] = monthly_melted["Metric"].map(metric_label_map)
    monthly_melted = monthly_melted.dropna(subset=["Amount"])

    METRIC_ORDER = ["Revenue (USD)", "Gross Profit (USD)"]

    # ✅ Bar chart: Revenue + GP side by side
    bar_chart = alt.Chart(monthly_melted).mark_bar().encode(
        x=alt.X("invoice_month:N", title="Month", sort=MONTH_ORDER),
        y=alt.Y(
                "Amount:Q",
                # axis=alt.Axis(format="~s", title="Amount (USD)"),
                axis=None  # ✅ Tắt hoàn toàn trục Y phụ
                ),
        color=alt.Color(
            "Metric:N",
            scale=alt.Scale(
                domain=METRIC_ORDER,
                range=[COLORS["revenue"], COLORS["gross_profit"]]
            ),
            legend=alt.Legend(title="Metric (Bar + Line)", orient="bottom")
        ),
        xOffset=alt.XOffset("Metric:N", sort=METRIC_ORDER),
        tooltip=[
            alt.Tooltip("invoice_month:N", title="Month"),
            alt.Tooltip("Metric:N", title="Metric"),
            alt.Tooltip("Amount:Q", title="Amount", format=",.0f")
        ]
    )

    # ➕ Add value on top of bars
    bar_text = alt.Chart(monthly_melted).mark_text(
        align='center', baseline='bottom', dy=-2, size=11
    ).encode(
        x=alt.X("invoice_month:N", sort=MONTH_ORDER),
        y=alt.Y("Amount:Q"),
        text=alt.Text("Amount:Q", format=",.0f"),
        xOffset=alt.XOffset("Metric:N", sort=METRIC_ORDER)
    )


    # ✅ Prepare data for line chart (GP% + Customer Count)
    line_data = monthly_df.copy()
    line_data = line_data.melt(
        id_vars=["invoice_month"],
        value_vars=["gp_percent", "customer_count"],
        var_name="Metric",
        value_name="Value"
    )

    LINE_METRIC_ORDER = ["Gross Profit %", "Customer Count"]
    metric_label_map_line = {
        "gp_percent": "Gross Profit %",
        "customer_count": "Customer Count"
    }
    line_data["Metric"] = line_data["Metric"].map(metric_label_map_line)

    # ➕ Add formatted_value column to customize text
    line_data["formatted_value"] = line_data.apply(
        lambda row: f"{row['Value']:.1f}" if row["Metric"] == "Gross Profit %" else f"{row['Value']:.0f}",
        axis=1
    )

    # ✅ Line chart (separate legend)
    line_chart = alt.Chart(line_data).mark_line(point=True).encode(
        x=alt.X("invoice_month:N", sort=MONTH_ORDER),
        y=alt.Y("Value:Q", axis=alt.Axis(title=None)),
        color=alt.Color(
            "Metric:N",
            scale=alt.Scale(
                domain=LINE_METRIC_ORDER,
                range=[COLORS["gross_profit_percent"], COLORS["customer_count"]]
            ),
            legend=alt.Legend(title="Metric (Line)", orient="bottom")
        ),
        tooltip=[
            alt.Tooltip("invoice_month:N", title="Month"),
            alt.Tooltip("Metric:N", title="Metric"),
            alt.Tooltip("formatted_value:N", title="Value")
        ]
    )

    # ➕ Add value on top of lines
    line_text = alt.Chart(line_data).mark_text(
        align='center', baseline='bottom', dy=-8, size=11
    ).encode(
        x=alt.X("invoice_month:N", sort=MONTH_ORDER),
        y=alt.Y("Value:Q"),
        text=alt.Text("formatted_value:N"),
        color=alt.Color(
            "Metric:N",
            scale=alt.Scale(
                domain=LINE_METRIC_ORDER,
                range=[COLORS["gross_profit_percent"], COLORS["customer_count"]]
            ),
            legend=None  # No need legend here (already in line_chart)
        )
    )



    # ✅ Combine all charts
    chart = alt.layer(
        bar_chart,
        bar_text,
        line_chart,
        line_text
    ).resolve_scale(
        y='independent',
        color='independent'  # ✨ Giải quyết vấn đề màu sắc
    ).properties(
        width=CHART_WIDTH,
        height=CHART_HEIGHT,
        title=f"📊 Monthly Revenue, Gross Profit, GP% & Customer Count Chart for {salesperson_name}"
    )

    return chart



def build_sales_overview_bar_chart(summary_df):
    """
    Build bar chart for sales and GP by salesperson.

    Args:
        summary_df: DataFrame with performance data.

    Returns:
        Altair Chart
    """
    melted = pd.melt(
        summary_df,
        id_vars=['sales_name'],
        value_vars=['sales_by_split_usd', 'gross_profit_by_split_usd'],
        var_name='Metric',
        value_name='Amount'
    )

    color_scale = alt.Scale(
        domain=['sales_by_split_usd', 'gross_profit_by_split_usd'],
        range=[COLORS['revenue'], COLORS['gross_profit']]
    )

    bar_chart = alt.Chart(melted).mark_bar().encode(
        x=alt.X('sales_name:N', title='Salesperson', sort='-y'),
        y=alt.Y('Amount:Q', title='Amount (USD)', axis=alt.Axis(format='~s')),
        color=alt.Color('Metric:N', scale=color_scale, title='Metric'),
        tooltip=[
            alt.Tooltip('sales_name:N', title='Salesperson'),
            alt.Tooltip('Metric:N', title='Metric'),
            alt.Tooltip('Amount:Q', title='Amount', format=',.0f')
        ]
    ).properties(
        width=CHART_WIDTH,
        height=CHART_HEIGHT,
        title='💼 Sales & Gross Profit by Salesperson'
    )
    return bar_chart


#############
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

    combined_chart = alt.layer(bar_chart, line_chart).resolve_scale(
        y='independent'
    ).properties(
        width=CHART_WIDTH,
        height=CHART_HEIGHT,
        title=f"📅 Monthly Revenue, Gross Profit, and GP% ({'Excl. Internal' if exclude_internal else 'Incl. Internal'})"
    )

    return combined_chart


def build_cumulative_revenue_gp_chart(monthly_summary_df: pd.DataFrame,  exclude_internal: bool):
    """
    Build cumulative revenue and gross profit line chart.

    Args:
        monthly_summary_df (DataFrame): Pre-processed monthly summary.

    Returns:
        Altair chart.
    """
    cumulative_melted = pd.melt(
        monthly_summary_df,
        id_vars=["invoice_month"],
        value_vars=["cumulative_revenue", "cumulative_gp"],
        var_name="Metric",
        value_name="CumulativeAmount"
    )

    cumulative_labels = {
        "cumulative_revenue": "Cumulative Revenue (USD)",
        "cumulative_gp": "Cumulative GP (USD)"
    }

    cumulative_melted["Metric"] = cumulative_melted["Metric"].map(cumulative_labels)

    cumulative_color_scale = alt.Scale(
        domain=list(cumulative_labels.values()),
        range=[COLORS["revenue"], COLORS["gross_profit"]]
    )

    cumulative_chart = alt.Chart(cumulative_melted).mark_line(point=True).encode(
        x=alt.X("invoice_month:N", title="Invoice Month", sort=MONTH_ORDER),
        y=alt.Y("CumulativeAmount:Q", title="Cumulative Amount (USD)", axis=alt.Axis(format="~s")),
        color=alt.Color("Metric:N", scale=cumulative_color_scale),
        tooltip=[
            alt.Tooltip("invoice_month:N", title="Month"),
            alt.Tooltip("Metric:N", title="Metric"),
            alt.Tooltip("CumulativeAmount:Q", title="Cumulative Amount", format=",.0f")
        ]
    ).properties(
        width=CHART_WIDTH,
        height=CHART_HEIGHT,
        title=f"📈 Cumulative Revenue and GP Over Time ({'Excl. Internal' if exclude_internal else 'Incl. Internal'})"
    )

    return cumulative_chart


def build_dimension_pie_charts(summary_df: pd.DataFrame, exclude_internal: bool, dimension_name: str):
    """
    Build side-by-side pie charts for Revenue and Gross Profit by a given dimension.

    Args:
        summary_df (DataFrame): Prepared summary data.
        dimension_name (str): Dimension label (e.g., 'Territory', 'Vertical').

    Returns:
        Altair Chart
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
        title=f"🌍 Gross Profit Breakdown by {dimension_name}({'Excl. Internal' if exclude_internal else 'Incl. Internal'})"
    )

    return revenue_pie_chart | gp_pie_chart


def build_dimension_bar_chart(summary_df: pd.DataFrame, exclude_internal: bool, dimension_name: str):
    """
    Build combined bar + line chart for Revenue, Gross Profit, and GP% by dimension.

    Args:
        summary_df (DataFrame): Prepared summary data.
        dimension_name (str): Dimension label (e.g., 'Territory', 'Vertical').

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
        title=f"📊 Revenue, Gross Profit, and GP% by {dimension_name} ({'Excl. Internal' if exclude_internal else 'Incl. Internal'})"
    )



def build_top_customers_gp_chart(top_customers_df: pd.DataFrame, exclude_internal: bool):
    """
    Build combined bar + line chart for top customers by gross profit.

    Args:
        top_customers_df (DataFrame): Top customers data with GrossProfit, cumulative %, etc.

    Returns:
        Altair Chart
    """
    # Bar chart (Gross Profit)
    bar_chart = alt.Chart(top_customers_df).mark_bar().encode(
        x=alt.X("Customer:N", sort="-y"),
        y=alt.Y("GrossProfit:Q", title="Gross Profit (USD)", axis=alt.Axis(format="~s")),
        color=alt.value(COLORS["gross_profit"]),
        tooltip=[
            alt.Tooltip("Customer:N", title="Customer"),
            alt.Tooltip("GrossProfit:Q", title="Gross Profit", format=",.0f"),
            alt.Tooltip("GP_Percent:Q", title="GP %", format=".2f")
        ]
    ).properties(
        width=CHART_WIDTH,
        height=CHART_HEIGHT
    )

    # Line chart (Cumulative %)
    line_chart = alt.Chart(top_customers_df).mark_line(point=True, color=COLORS["gross_profit_percent"]).encode(
        x=alt.X("Customer:N", sort="-y"),
        y=alt.Y("cumulative_percent:Q", title="Cumulative %", axis=alt.Axis(format=".0%")),
        tooltip=[
            alt.Tooltip("Customer:N", title="Customer"),
            alt.Tooltip("cumulative_percent:Q", title="Cumulative %", format=".2%")
        ]
    )

    # Combine
    combined_chart = alt.layer(
        bar_chart,
        line_chart
    ).resolve_scale(
        y='independent'
    ).properties(
        title=f"🏆 Top 80% Customers by Gross Profit (Bar + Cumulative Line) ({'Excl. Internal' if exclude_internal else 'Incl. Internal'})"
    )

    return combined_chart