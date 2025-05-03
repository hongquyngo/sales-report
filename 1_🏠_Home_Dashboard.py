import streamlit as st
import pandas as pd
from sqlalchemy import text
from db import get_db_engine
import altair as alt

# ===================
# Page Config
# ===================
st.set_page_config(page_title="🏠 YTD Summary", layout="wide")
st.title("📊 YTD Business Summary")
st.markdown("### Overview of year-to-date business performance")

# ===================
# Load Data Functions
# ===================
def load_invoiced_sales_data():
    engine = get_db_engine()
    query = """
        SELECT *
        FROM prostechvn.sales_invoice_full_looker_view
        WHERE DATE(inv_date) >= DATE_FORMAT(CURDATE(), '%Y-01-01')
          AND inv_date < DATE_ADD(DATE_FORMAT(CURDATE(), '%Y-%m-%d'), INTERVAL 1 DAY);
    """
    return pd.read_sql(text(query), engine)

def load_kpi_center_data():
    engine = get_db_engine()
    query = """
        SELECT *
        FROM prostechvn.sales_report_by_kpi_center_flat_looker_view
        WHERE DATE(inv_date) >= DATE_FORMAT(CURDATE(), '%Y-01-01')
          AND inv_date < DATE_ADD(DATE_FORMAT(CURDATE(), '%Y-%m-%d'), INTERVAL 1 DAY);
    """
    return pd.read_sql(text(query), engine)

# ===================
# Cache & Prep
# ===================
@st.cache_data(ttl=3600)
def get_summary_data():
    inv_df = load_invoiced_sales_data()
    kpi_df = load_kpi_center_data()
    return inv_df, kpi_df

inv_df, kpi_df = get_summary_data()

# ===================
# Sidebar Option
# ===================
st.sidebar.header("Display Options")
exclude_internal = st.sidebar.checkbox("🚫 Exclude INTERNAL Revenue (keep GP)", value=True)

# Always calculate total revenue from invoices
total_revenue = inv_df["calculated_invoiced_amount_usd"].sum()

# If checkbox ticked, subtract INTERNAL revenue (from KPI data)
if exclude_internal:
    internal_revenue = kpi_df[kpi_df["kpi_type"] == "INTERNAL"]["sales_by_kpi_center_usd"].sum()
    adjusted_revenue = total_revenue - internal_revenue
    display_revenue = max(adjusted_revenue, 0)  # ensure non-negative
else:
    display_revenue = total_revenue

# Calculate gross profit from invoice data
total_gp = inv_df["invoiced_gross_profit_usd"].sum()
gp_percent = round((total_gp / display_revenue) * 100, 2) if display_revenue else 0

# ===================
# Main KPI Section
# ===================
col1, col2, col3 = st.columns(3)
col1.metric("🧾 Total Revenue (YTD)", f"{display_revenue:,.0f} USD")
col2.metric("💰 Gross Profit (YTD)", f"{total_gp:,.0f} USD")
col3.metric("📈 Gross Profit %", f"{gp_percent}%")

st.markdown("---")

# ===================
# Monthly Revenue & GP Chart (Final Combined)
# ===================

# Month order
month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Prepare monthly summary from invoices
inv_df["invoice_month"] = pd.to_datetime(inv_df["inv_date"]).dt.strftime("%b")
monthly_summary = inv_df.groupby("invoice_month").agg({
    "calculated_invoiced_amount_usd": "sum",
    "invoiced_gross_profit_usd": "sum"
}).reindex(month_order).fillna(0).reset_index()

# Prepare INTERNAL revenue monthly
internal_monthly = kpi_df[kpi_df["kpi_type"] == "INTERNAL"].groupby("invoice_month").agg({
    "sales_by_kpi_center_usd": "sum"
}).reindex(month_order).fillna(0).reset_index()

# Adjust revenue if checkbox ticked
if exclude_internal:
    monthly_summary["adjusted_revenue_usd"] = monthly_summary["calculated_invoiced_amount_usd"] - internal_monthly["sales_by_kpi_center_usd"]
    monthly_summary["adjusted_revenue_usd"] = monthly_summary["adjusted_revenue_usd"].apply(lambda x: max(x, 0))
else:
    monthly_summary["adjusted_revenue_usd"] = monthly_summary["calculated_invoiced_amount_usd"]

# Calculate monthly GP %
monthly_summary["gp_percent"] = monthly_summary.apply(
    lambda row: (row["invoiced_gross_profit_usd"] / row["adjusted_revenue_usd"] * 100) if row["adjusted_revenue_usd"] else 0,
    axis=1
)

# Prepare melted data for bars
monthly_melted = pd.melt(
    monthly_summary,
    id_vars=["invoice_month"],
    value_vars=["adjusted_revenue_usd", "invoiced_gross_profit_usd"],
    var_name="Metric",
    value_name="Amount"
)

# Rename metrics for display
metric_labels = {
    "adjusted_revenue_usd": "Revenue (USD)",
    "invoiced_gross_profit_usd": "Gross Profit (USD)"
}
monthly_melted["Metric"] = monthly_melted["Metric"].map(metric_labels)

# Explicitly set metric order
metric_order = ["Revenue (USD)", "Gross Profit (USD)"]
monthly_melted["Metric"] = pd.Categorical(
    monthly_melted["Metric"],
    categories=metric_order,
    ordered=True
)

# Custom color mapping
color_scale = alt.Scale(
    domain=["Revenue (USD)", "Gross Profit (USD)"],
    range=["#FFA500", "#1f77b4"]  # orange, blue
)

# Bar chart
bar_chart = alt.Chart(monthly_melted).mark_bar().encode(
    x=alt.X("invoice_month:N", title="Invoice Month", sort=month_order),
    y=alt.Y("Amount:Q", title="Amount (USD)", axis=alt.Axis(format="~s")),
    color=alt.Color("Metric:N", scale=color_scale),
    xOffset=alt.XOffset("Metric:N", sort=metric_order),
    tooltip=[
        alt.Tooltip("invoice_month:N", title="Month"),
        alt.Tooltip("Metric:N", title="Metric"),
        alt.Tooltip("Amount:Q", title="Amount", format=",.0f")
    ]
)

# Line chart for GP % (purple line)
line_chart = alt.Chart(monthly_summary).mark_line(
    point=True,
    color="#800080"  # purple
).encode(
    x=alt.X("invoice_month:N", sort=month_order),
    y=alt.Y(
        "gp_percent:Q",
        title="Gross Profit %",
        axis=alt.Axis(format=".1f", titleColor="#800080")
        # auto scale (no fixed domain)
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
    width=700,
    height=400,
    title="📅 Monthly Revenue, Gross Profit (Side by Side), and Gross Profit %"
)

st.altair_chart(combined_chart, use_container_width=True)


# ===================
# Cumulative Revenue & GP Line Chart
# ===================

# Prepare cumulative data
monthly_summary["cumulative_revenue"] = monthly_summary["adjusted_revenue_usd"].cumsum()
monthly_summary["cumulative_gp"] = monthly_summary["invoiced_gross_profit_usd"].cumsum()

# Melt into long format
cumulative_melted = pd.melt(
    monthly_summary,
    id_vars=["invoice_month"],
    value_vars=["cumulative_revenue", "cumulative_gp"],
    var_name="Metric",
    value_name="CumulativeAmount"
)

# Rename for display
cumulative_labels = {
    "cumulative_revenue": "Cumulative Revenue (USD)",
    "cumulative_gp": "Cumulative GP (USD)"
}
cumulative_melted["Metric"] = cumulative_melted["Metric"].map(cumulative_labels)

# Custom color mapping
cumulative_color_scale = alt.Scale(
    domain=["Cumulative Revenue (USD)", "Cumulative GP (USD)"],
    range=["#FFA500", "#1f77b4"]  # orange, blue
)

# Build cumulative line chart
cumulative_chart = alt.Chart(cumulative_melted).mark_line(point=True).encode(
    x=alt.X("invoice_month:N", title="Invoice Month", sort=month_order),
    y=alt.Y("CumulativeAmount:Q", title="Cumulative Amount (USD)", axis=alt.Axis(format="~s")),
    color=alt.Color("Metric:N", scale=cumulative_color_scale),
    tooltip=[
        alt.Tooltip("invoice_month:N", title="Month"),
        alt.Tooltip("Metric:N", title="Metric"),
        alt.Tooltip("CumulativeAmount:Q", title="Cumulative Amount", format=",.0f")
    ]
).properties(
    width=700,
    height=400,
    title="📈 Cumulative Revenue and GP Over Time"
)

st.altair_chart(cumulative_chart, use_container_width=True)



# ===================
# Pie Charts by KPI Center Groups (Adjusted by Tick/Untick)
# ===================
st.markdown("### 🥧 Revenue Breakdown by KPI Center")

# Base total revenue (after tick/untick)
total_invoice_revenue = inv_df["calculated_invoiced_amount_usd"].sum()
internal_sales = kpi_df[kpi_df["kpi_type"] == "INTERNAL"]["sales_by_kpi_center_usd"].sum()

if exclude_internal:
    total_revenue = total_invoice_revenue - internal_sales
else:
    total_revenue = total_invoice_revenue

# ===================
# KPI by Territory Breakdown (Corrected Logic)
# ===================


# ===================
# Pie Charts - KPI by Territory (Revenue + Gross Profit)
# ===================

st.subheader("🌍 KPI by Territory: Revenue & Gross Profit")

# ---------- Revenue Data ----------
territory_df = kpi_df[kpi_df["kpi_type"] == "TERRITORY"]
territory_sum = territory_df["sales_by_kpi_center_usd"].sum()
unmapped_revenue = max(total_revenue - territory_sum, 0)

territory_grouped = territory_df.groupby("kpi_center")["sales_by_kpi_center_usd"].sum()
territory_combined = pd.concat([
    territory_grouped, pd.Series({"Unmapped": unmapped_revenue})
]).reset_index()
territory_combined.columns = ["Center", "Revenue"]
territory_combined["Percent"] = (territory_combined["Revenue"] / territory_combined["Revenue"].sum()) * 100

# ---------- Gross Profit Data ----------
territory_gp_df = kpi_df[kpi_df["kpi_type"] == "TERRITORY"]
territory_gp_sum = territory_gp_df["gross_profit_by_kpi_center_usd"].sum()
total_gp_invoice = inv_df["invoiced_gross_profit_usd"].sum()
unmapped_gp = max(total_gp_invoice - territory_gp_sum, 0)

territory_gp_grouped = territory_gp_df.groupby("kpi_center")["gross_profit_by_kpi_center_usd"].sum()
territory_gp_combined = pd.concat([
    territory_gp_grouped, pd.Series({"Unmapped": unmapped_gp})
]).reset_index()
territory_gp_combined.columns = ["Center", "GrossProfit"]
territory_gp_combined["Percent"] = (territory_gp_combined["GrossProfit"] / territory_gp_combined["GrossProfit"].sum()) * 100

# ---------- Revenue Pie Chart ----------
revenue_pie_chart = alt.Chart(territory_combined).mark_arc().encode(
    theta=alt.Theta(field="Revenue", type="quantitative"),
    color=alt.Color(field="Center", type="nominal"),
    tooltip=[
        alt.Tooltip("Center:N", title="Territory"),
        alt.Tooltip("Revenue:Q", title="Revenue (USD)", format=",.0f"),
        alt.Tooltip("Percent:Q", title="Percentage", format=".2f")
    ]
).properties(
    width=300,
    height=300,
    title="🌍 Revenue Breakdown by Territory"
)

# ---------- Gross Profit Pie Chart ----------
gp_pie_chart = alt.Chart(territory_gp_combined).mark_arc().encode(
    theta=alt.Theta(field="GrossProfit", type="quantitative"),
    color=alt.Color(field="Center", type="nominal"),
    tooltip=[
        alt.Tooltip("Center:N", title="Territory"),
        alt.Tooltip("GrossProfit:Q", title="Gross Profit (USD)", format=",.0f"),
        alt.Tooltip("Percent:Q", title="Percentage", format=".2f")
    ]
).properties(
    width=300,
    height=300,
    title="🌍 Gross Profit Breakdown by Territory"
)

# ---------- Display Side by Side ----------
st.altair_chart(revenue_pie_chart | gp_pie_chart, use_container_width=True)


# ===================
# Bar Chart - KPI by Territory (Revenue + Gross Profit + GP %)
# ===================

# st.subheader("📊 KPI by Territory: Revenue, Gross Profit, and GP %")

# Combine Revenue + GP into one DataFrame
territory_combined_df = pd.merge(
    territory_combined, territory_gp_combined, on="Center", how="outer"
).fillna(0)

# Calculate GP %
territory_combined_df["GP_Percent"] = territory_combined_df.apply(
    lambda row: (row["GrossProfit"] / row["Revenue"] * 100) if row["Revenue"] else 0,
    axis=1
)

# Melt for bar chart (Revenue + GP)
territory_melted = pd.melt(
    territory_combined_df,
    id_vars=["Center"],
    value_vars=["Revenue", "GrossProfit"],
    var_name="Metric",
    value_name="Amount"
)

# Define metric order
metric_order = ["Revenue", "GrossProfit"]

# Custom color mapping
color_scale = alt.Scale(
    domain=["Revenue", "GrossProfit"],
    range=["#FFA500", "#1f77b4"]  # orange, blue
)

# Bar chart
territory_bar_chart = alt.Chart(territory_melted).mark_bar().encode(
    x=alt.X("Center:N", title="Territory", sort="-y"),
    y=alt.Y("Amount:Q", title="Amount (USD)", axis=alt.Axis(format="~s")),
    color=alt.Color("Metric:N", scale=color_scale, title="Metric"),
    xOffset=alt.XOffset("Metric:N", sort=metric_order),
    tooltip=[
        alt.Tooltip("Center:N", title="Territory"),
        alt.Tooltip("Metric:N", title="Metric"),
        alt.Tooltip("Amount:Q", title="Amount", format=",.0f")
    ]
)

# Line chart for GP %
gp_line_chart = alt.Chart(territory_combined_df).mark_line(
    point=True,
    color="#800080"  # purple
).encode(
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

# Combine bar + line chart
territory_combined_chart = alt.layer(
    territory_bar_chart,
    gp_line_chart
).resolve_scale(
    y='independent'
).properties(
    width=700,
    height=400,
    title="📊 Revenue, Gross Profit, and GP % by Territory"
)

st.altair_chart(territory_combined_chart, use_container_width=True)


# ===================
# Pie Charts - KPI by Vertical Market (Revenue + Gross Profit)
# ===================

st.subheader("🏭 KPI by Vertical Market: Revenue & Gross Profit")

# ---------- Revenue Data ----------
vertical_df = kpi_df[kpi_df["kpi_type"] == "VERTICAL"]
vertical_sum = vertical_df["sales_by_kpi_center_usd"].sum()

unmapped_revenue = max(total_revenue - vertical_sum, 0)

vertical_grouped = vertical_df.groupby("kpi_center")["sales_by_kpi_center_usd"].sum()
vertical_combined = pd.concat([
    vertical_grouped,
    pd.Series({"Other": unmapped_revenue})
]).reset_index()
vertical_combined.columns = ["Center", "Revenue"]
vertical_combined["Percent"] = (vertical_combined["Revenue"] / vertical_combined["Revenue"].sum()) * 100

# ---------- Gross Profit Data ----------
vertical_gp_df = kpi_df[kpi_df["kpi_type"] == "VERTICAL"]
vertical_gp_sum = vertical_gp_df["gross_profit_by_kpi_center_usd"].sum()

total_gp_invoice = inv_df["invoiced_gross_profit_usd"].sum()
unmapped_gp = max(total_gp_invoice - vertical_gp_sum, 0)

vertical_gp_grouped = vertical_gp_df.groupby("kpi_center")["gross_profit_by_kpi_center_usd"].sum()
vertical_gp_combined = pd.concat([
    vertical_gp_grouped,
    pd.Series({"Other": unmapped_gp})
]).reset_index()
vertical_gp_combined.columns = ["Center", "GrossProfit"]
vertical_gp_combined["Percent"] = (vertical_gp_combined["GrossProfit"] / vertical_gp_combined["GrossProfit"].sum()) * 100

# ---------- Revenue Pie Chart ----------
revenue_pie_chart_vertical = alt.Chart(vertical_combined).mark_arc().encode(
    theta=alt.Theta(field="Revenue", type="quantitative"),
    color=alt.Color(field="Center", type="nominal"),
    tooltip=[
        alt.Tooltip("Center:N", title="Vertical"),
        alt.Tooltip("Revenue:Q", title="Revenue (USD)", format=",.0f"),
        alt.Tooltip("Percent:Q", title="Percentage", format=".2f")
    ]
).properties(
    width=300,
    height=300,
    title="🏭 Revenue Breakdown by Vertical Market"
)

# ---------- Gross Profit Pie Chart ----------
gp_pie_chart_vertical = alt.Chart(vertical_gp_combined).mark_arc().encode(
    theta=alt.Theta(field="GrossProfit", type="quantitative"),
    color=alt.Color(field="Center", type="nominal"),
    tooltip=[
        alt.Tooltip("Center:N", title="Vertical"),
        alt.Tooltip("GrossProfit:Q", title="Gross Profit (USD)", format=",.0f"),
        alt.Tooltip("Percent:Q", title="Percentage", format=".2f")
    ]
).properties(
    width=300,
    height=300,
    title="🏭 Gross Profit Breakdown by Vertical Market"
)

# ---------- Display Side by Side ----------
st.altair_chart(revenue_pie_chart_vertical | gp_pie_chart_vertical, use_container_width=True)

# ===================
# Bar + Line Chart - KPI by Vertical Market (Revenue, GP, GP%)
# ===================

st.subheader("🏭 KPI by Vertical Market: Revenue, Gross Profit & GP%")

# ---------- Prepare Combined Data ----------
# Merge revenue and GP into one dataframe
vertical_combined_bars = pd.merge(
    vertical_combined,
    vertical_gp_combined,
    on="Center"
)

# Calculate GP%
vertical_combined_bars["GP_percent"] = vertical_combined_bars.apply(
    lambda row: (row["GrossProfit"] / row["Revenue"] * 100) if row["Revenue"] else 0,
    axis=1
)

# ---------- Melt for Bar Chart ----------
vertical_melted = pd.melt(
    vertical_combined_bars,
    id_vars=["Center"],
    value_vars=["Revenue", "GrossProfit"],
    var_name="Metric",
    value_name="Amount"
)

# Explicit metric order
metric_order = ["Revenue", "GrossProfit"]
vertical_melted["Metric"] = pd.Categorical(vertical_melted["Metric"], categories=metric_order, ordered=True)

# ---------- Bar Chart ----------
color_scale = alt.Scale(
    domain=["Revenue", "GrossProfit"],
    range=["#FFA500", "#1f77b4"]  # orange, blue
)

bar_chart = alt.Chart(vertical_melted).mark_bar().encode(
    x=alt.X("Center:N", title="Vertical Market", sort="-y"),
    y=alt.Y("Amount:Q", title="Amount (USD)", axis=alt.Axis(format="~s")),
    color=alt.Color("Metric:N", scale=color_scale, title="Metric"),
    xOffset=alt.XOffset("Metric:N", sort=metric_order),
    tooltip=[
        alt.Tooltip("Center:N", title="Vertical"),
        alt.Tooltip("Metric:N", title="Metric"),
        alt.Tooltip("Amount:Q", title="Amount", format=",.0f")
    ]
)

# ---------- Line Chart (GP%) ----------
line_chart = alt.Chart(vertical_combined_bars).mark_line(
    point=True,
    color="#800080"  # purple
).encode(
    x=alt.X("Center:N", sort="-y"),
    y=alt.Y(
        "GP_percent:Q",
        title="Gross Profit %",
        axis=alt.Axis(format=".1f", titleColor="#800080")
    ),
    tooltip=[
        alt.Tooltip("Center:N", title="Vertical"),
        alt.Tooltip("GP_percent:Q", title="Gross Profit %", format=".2f")
    ]
)

# ---------- Combine ----------
combined_chart = alt.layer(
    bar_chart,
    line_chart
).resolve_scale(
    y='independent'
).properties(
    width=700,
    height=400,
    title="🏭 Vertical Market Revenue, Gross Profit, and GP%"
)

# ---------- Display ----------
st.altair_chart(combined_chart, use_container_width=True)


# ===================
# Bar Chart - Top 80% Customers by Gross Profit
# ===================

st.subheader("🏆 Top 80% Customers by Gross Profit")

# Group gross profit by customer
customer_gp = inv_df.groupby("customer")["invoiced_gross_profit_usd"].sum().reset_index()
customer_gp = customer_gp.sort_values(by="invoiced_gross_profit_usd", ascending=False)

# Calculate cumulative % contribution
customer_gp["cumulative_gp"] = customer_gp["invoiced_gross_profit_usd"].cumsum()
total_gp = customer_gp["invoiced_gross_profit_usd"].sum()
customer_gp["cumulative_percent"] = customer_gp["cumulative_gp"] / total_gp

# Filter top 80% customers
top_80_customers = customer_gp[customer_gp["cumulative_percent"] <= 0.8]

# Prepare DataFrame for plotting
top_80_customers = top_80_customers.rename(columns={
    "customer": "Customer",
    "invoiced_gross_profit_usd": "GrossProfit"
})

# Add GP %
top_80_customers["GP_Percent"] = top_80_customers["GrossProfit"] / total_gp * 100

# Bar chart for Gross Profit
customer_bar_chart = alt.Chart(top_80_customers).mark_bar().encode(
    x=alt.X("Customer:N", sort="-y"),
    y=alt.Y("GrossProfit:Q", title="Gross Profit (USD)", axis=alt.Axis(format="~s")),
    color=alt.value("#1f77b4"),
    tooltip=[
        alt.Tooltip("Customer:N", title="Customer"),
        alt.Tooltip("GrossProfit:Q", title="Gross Profit", format=",.0f"),
        alt.Tooltip("GP_Percent:Q", title="GP %", format=".2f")
    ]
).properties(
    width=700,
    height=400,
    title="🏆 Top 80% Customers by Gross Profit"
)

# Optional: Line chart showing cumulative %
cumulative_line_chart = alt.Chart(top_80_customers).mark_line(
    point=True,
    color="#800080"
).encode(
    x=alt.X("Customer:N", sort="-y"),
    y=alt.Y("cumulative_percent:Q", title="Cumulative %", axis=alt.Axis(format=".0%")),
    tooltip=[
        alt.Tooltip("Customer:N", title="Customer"),
        alt.Tooltip("cumulative_percent:Q", title="Cumulative %", format=".2%")
    ]
)

# Combine bar + line chart
combined_customer_chart = alt.layer(
    customer_bar_chart,
    cumulative_line_chart
).resolve_scale(
    y='independent'
).properties(
    title="🏆 Top 80% Customers by Gross Profit (Bar + Cumulative Line)"
)

st.altair_chart(combined_customer_chart, use_container_width=True)
# ===================
# Footer
# ===================
st.markdown("---")
st.caption("Generated by Prostech BI Dashboard | Powered by Prostech AI")