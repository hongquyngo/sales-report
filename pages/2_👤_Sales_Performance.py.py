import streamlit as st
from data_loader import load_sales_performance_data

from data_processing import (
    calculate_salesperson_overview_metrics,
    prepare_salesperson_monthly_summary_data,
    prepare_salesperson_cumulative_data,
    prepare_salesperson_top_customers_by_gp,
    prepare_salesperson_top_brands_by_gp
)

from chart_builder import (
    build_salesperson_monthly_chart,
    build_salesperson_cumulative_chart,
    build_salesperson_top_customers_gp_chart,
    build_salesperson_top_brands_gp_chart
)

st.set_page_config(page_title="Performance by Salesperson", layout="wide")
st.title("👔 YTD Sales Performance Summary")

# Load data
sales_report_by_salesperson_df, backlog_report_by_salesperson_df, kpi_by_salesperson_df = load_sales_performance_data()

# ========== Filter section (Main page) ==========
st.subheader("🔎 Filter Options")

# Get unique salesperson list
# sales_list = sorted(sales_report_by_salesperson_df['sales_name'].unique().tolist())
# Filter only ACTIVE sales employees, then get unique, sorted list of names
sales_list = (
    sales_report_by_salesperson_df[sales_report_by_salesperson_df["employment_status"] == "ACTIVE"]
    ["sales_name"]
    .dropna()
    .unique()
    .tolist()
)
sales_list = sorted(sales_list)


# Dropdown single-select (default to first person)
selected_sales = st.selectbox(
    "👤 Select a Salesperson:",
    options=sales_list,
    index=0
)

# Filter DataFrames based on selection
filtered_sales_report_df = sales_report_by_salesperson_df[
    sales_report_by_salesperson_df['sales_name'] == selected_sales
]

filtered_backlog_df = backlog_report_by_salesperson_df[
    backlog_report_by_salesperson_df['sales_name'] == selected_sales
]

filtered_kpi_df = kpi_by_salesperson_df[
    kpi_by_salesperson_df['employee_name'] == selected_sales
]

# ==================== Salesperson YTD Overview ====================
st.markdown("---")
st.markdown(f"### Overview of Year-to-Date Sales Performance for {selected_sales}")

# Calculate KPIs (now includes KPI %)
sales_kpis = calculate_salesperson_overview_metrics(
    filtered_sales_report_df,
    filtered_backlog_df,
    kpi_by_salesperson_df,
    selected_sales
)

# === Row 1: Customers, Invoices, Orders ===
row1, row2, row3 = st.columns(3)
row1.metric("👥 Total Customers (YTD)", f"{sales_kpis['total_customers']}")
row2.metric("🧾 Total Invoices (YTD)", f"{sales_kpis['total_invoices']}")
row3.metric("📦 Total Sales Orders Invoiced (YTD)", f"{sales_kpis['total_sales_orders_invoiced']}")

# === Row 2: Revenue + KPI, GP + KPI, GP % ===
row4, row5, row6 = st.columns(3)

# Revenue with KPI %
revenue_kpi_text = (
    f"{sales_kpis['display_revenue']:,.0f} USD"
    + (f"  ({sales_kpis['percent_revenue_kpi']}% KPI)" if sales_kpis['percent_revenue_kpi'] is not None else "")
)
row4.metric("📄 Total Revenue (YTD)", revenue_kpi_text)

# GP with KPI %
gp_kpi_text = (
    f"{sales_kpis['total_gp']:,.0f} USD"
    + (f"  ({sales_kpis['percent_gp_kpi']}% KPI)" if sales_kpis['percent_gp_kpi'] is not None else "")
)
row5.metric("💰 Gross Profit (YTD)", gp_kpi_text)

# GP %
row6.metric("📈 Gross Profit %", f"{sales_kpis['gp_percent']}%")

# === Row 3: Outstanding Revenue, Outstanding GP, Outstanding GP % ===
row7, row8, row9 = st.columns(3)
row7.metric("⏳ Outstanding Revenue (YTD)", f"{sales_kpis['display_outstanding']:,.0f} USD")
row8.metric("⏳ Outstanding Gross Profit (YTD)", f"{sales_kpis['outstanding_gp']:,.0f} USD")
row9.metric("⏳ Outstanding GP % (YTD)", f"{sales_kpis['outstanding_gp_percent']}%")


# ==================== Salesperson Monthly Revenue, GP, GP%, and Customer Count ====================
st.markdown("---")
st.subheader(f"📊 Monthly Revenue, Gross Profit, GP% & Customer Count Chart for {selected_sales}")


# Prepare monthly summary
monthly_sales_summary = prepare_salesperson_monthly_summary_data(filtered_sales_report_df)

# Build chart
monthly_chart = build_salesperson_monthly_chart(monthly_sales_summary, selected_sales)

# Display
st.altair_chart(monthly_chart, use_container_width=True)

# ==================== Cumulative Revenue & GP Chart ====================
st.markdown("---")

# Prepare data
salesperson_cumulative_df = prepare_salesperson_cumulative_data(monthly_sales_summary)

# Build chart
cumulative_chart = build_salesperson_cumulative_chart(salesperson_cumulative_df, selected_sales)

# Show chart
st.altair_chart(cumulative_chart, use_container_width=True)




# ==================== Top 80% Customers by GP ====================
st.markdown("---")
st.subheader(f"🏆 Top 80% Customers by Gross Profit for {selected_sales}")

# Prepare data
top_customers_df = prepare_salesperson_top_customers_by_gp(filtered_sales_report_df, top_percent=0.8)

# Build chart
top_customers_chart = build_salesperson_top_customers_gp_chart(top_customers_df, selected_sales)

# Show chart
st.altair_chart(top_customers_chart, use_container_width=True)



# =================== TOP BRANDS BY GP ======================
st.markdown("---")
st.subheader(f"🏆 Top 80% Brands by Gross Profit for {selected_sales}")

# Filter theo từng sales
salesperson_top_brands_df = prepare_salesperson_top_brands_by_gp(filtered_sales_report_df, top_percent=0.8)

# Vẽ biểu đồ
chart = build_salesperson_top_brands_gp_chart(salesperson_top_brands_df, selected_sales)
st.altair_chart(chart, use_container_width=True)


# ==================== Footer ====================
st.markdown("---")
st.caption("Generated by Prostech BI Dashboard | Powered by Prostech AI")