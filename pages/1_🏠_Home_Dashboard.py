import streamlit as st
from data_loader import load_data
from data_processing import (
    calculate_overview_metrics,
    prepare_monthly_summary_data,
    prepare_dimension_summary_data,
    prepare_top_customers_by_gp,
    prepare_top_brands_by_gp
)
from chart_builder import (
    build_monthly_revenue_gp_chart,
    build_cumulative_revenue_gp_chart,
    build_dimension_pie_charts,
    build_dimension_bar_chart,
    build_top_customers_gp_chart,
    build_top_brands_gp_chart
)

st.set_page_config(page_title="Prostech YTD Performance", layout="wide")
st.title("📊 YTD Business Summary")

# Sidebar Option
st.sidebar.header("Display Options")
exclude_internal = st.sidebar.checkbox("🚫 Exclude INTERNAL Revenue (keep GP)", value=True)

# Load Data
inv_df, inv_by_kpi_center_df, backlog_df, backlog_by_kpi_center_df = load_data()

# ==================== Overview Section ====================
st.markdown("---")
st.markdown(f"### Overview of Year-to-Date Business Performance ({'Excl. Internal' if exclude_internal else 'Incl. Internal'})")

kpis = calculate_overview_metrics(
    inv_df,
    inv_by_kpi_center_df,
    backlog_df,
    backlog_by_kpi_center_df,
    exclude_internal
)

row1, row2, row3 = st.columns(3)
row1.metric("👥 Total Customers (YTD)", f"{kpis['total_customers']}")
row2.metric("🧾 Total Invoices (YTD)", f"{kpis['total_invoices']}")
row3.metric("📦 Total Sales Orders Invoiced (YTD)", f"{kpis['total_sales_orders_invoiced']}")

row4, row5, row6 = st.columns(3)
row4.metric("📄 Total Revenue (YTD)", f"{kpis['display_revenue']:,.0f} USD")
row5.metric("💰 Gross Profit (YTD)", f"{kpis['total_gp']:,.0f} USD")
row6.metric("📈 Gross Profit %", f"{kpis['gp_percent']}%")

row7, row8, row9 = st.columns(3)
row7.metric("⏳ Outstanding Revenue (YTD)", f"{kpis['display_outstanding']:,.0f} USD")
row8.metric("⏳ Outstanding Gross Profit (YTD)", f"{kpis['outstanding_gp']:,.0f} USD")
row9.metric("⏳ Outstanding GP % (YTD)", f"{kpis['outstanding_gp_percent']}%")


# ==================== Monthly Revenue & GP Chart ====================
st.markdown("---")
st.subheader("📊 Monthly Revenue, Gross Profit, and GP% Chart")

monthly_summary = prepare_monthly_summary_data(inv_df, inv_by_kpi_center_df, exclude_internal)
monthly_chart = build_monthly_revenue_gp_chart(monthly_summary, exclude_internal)
st.altair_chart(monthly_chart, use_container_width=True)

# ==================== Cumulative Revenue & GP Chart ====================
st.markdown("---")

cumulative_chart = build_cumulative_revenue_gp_chart(monthly_summary, exclude_internal)
st.altair_chart(cumulative_chart, use_container_width=True)

# ==================== Territory KPI Section ====================
st.markdown("---")
st.subheader("🌍 KPI by Territory: Revenue & Gross Profit")

territory_summary = prepare_dimension_summary_data(
    inv_df,
    inv_by_kpi_center_df,
    dimension_type="TERRITORY",
    exclude_internal=exclude_internal
)

territory_pie_charts = build_dimension_pie_charts(territory_summary,exclude_internal, dimension_name="Territory")
st.altair_chart(territory_pie_charts, use_container_width=True)

territory_bar_chart = build_dimension_bar_chart(territory_summary, exclude_internal, dimension_name="Territory")
st.altair_chart(territory_bar_chart, use_container_width=True)

# ==================== Vertical KPI Section ====================
st.markdown("---")
st.subheader("🏭 KPI by Vertical: Revenue & Gross Profit")

vertical_summary = prepare_dimension_summary_data(
    inv_df,
    inv_by_kpi_center_df,
    dimension_type="VERTICAL",
    exclude_internal=exclude_internal
)

vertical_pie_charts = build_dimension_pie_charts(vertical_summary,exclude_internal, dimension_name="Vertical")
st.altair_chart(vertical_pie_charts, use_container_width=True)

vertical_bar_chart = build_dimension_bar_chart(vertical_summary,exclude_internal, dimension_name="Vertical")
st.altair_chart(vertical_bar_chart, use_container_width=True)


# ==================== Top 80% Customers by GP ====================
st.markdown("---")
st.subheader("🏆 Top 80% Customers by Gross Profit")

# Prepare data
top_customers_df = prepare_top_customers_by_gp(inv_df, top_percent=0.8)

# Build chart
top_customers_chart = build_top_customers_gp_chart(top_customers_df, exclude_internal)
st.altair_chart(top_customers_chart, use_container_width=True)


# ==================== Top 80% Brands by Gross Profit ====================
st.markdown("---")
st.subheader("🏆 Top 80% Brands by Gross Profit")

# Prepare data
top_brands_df = prepare_top_brands_by_gp(inv_df, top_percent=0.8)

# Build chart
top_brands_chart = build_top_brands_gp_chart(top_brands_df,  exclude_internal)

# Display chart
st.altair_chart(top_brands_chart, use_container_width=True)


# ==================== Footer ====================
st.markdown("---")
st.caption("Generated by Prostech BI Dashboard | Powered by Prostech AI")
