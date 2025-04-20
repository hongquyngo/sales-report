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
# Load Data
# ===================
def load_order_data():
    engine = get_db_engine()
    query = """
        SELECT * FROM order_confirmation_full_looker_view
        WHERE invoiced_date >= DATE_FORMAT(CURDATE(), '%Y-01-01')
              AND invoiced_date <= CURDATE()
    """
    return pd.read_sql(text(query), engine)

def load_kpi_data():
    engine = get_db_engine()
    query = """
        SELECT * FROM sales_report_by_kpi_center_flat_looker_view
        WHERE inv_date >= DATE_FORMAT(CURDATE(), '%Y-01-01')
              AND inv_date <= CURDATE()
    """
    return pd.read_sql(text(query), engine)

# ===================
# Cache & Prep
# ===================
@st.cache_data(ttl=3600)
def get_summary_data():
    oc_df = load_order_data()
    kpi_df = load_kpi_data()
    return oc_df, kpi_df

oc_df, kpi_df = get_summary_data()

# ===================
# Sidebar Option
# ===================
st.sidebar.header("Display Options")
exclude_internal = st.sidebar.checkbox("🚫 Exclude INTERNAL Revenue (keep GP)", value=True)

if exclude_internal:
    revenue_df = kpi_df[kpi_df["kpi_type"] != "INTERNAL"].copy()
else:
    revenue_df = kpi_df.copy()

# ===================
# Main KPI Section
# ===================
total_revenue = revenue_df["sales_by_kpi_center_usd"].sum()
total_gp = kpi_df["gross_profit_by_kpi_center_usd"].sum()
gp_percent = round((total_gp / total_revenue) * 100, 2) if total_revenue else 0

col1, col2, col3 = st.columns(3)
col1.metric("🧾 Total Revenue (YTD)", f"{total_revenue:,.0f} USD")
col2.metric("💰 Gross Profit (YTD)", f"{total_gp:,.0f} USD")
col3.metric("📈 Gross Profit %", f"{gp_percent}%")

st.markdown("---")

# ===================
# Revenue by Month (Altair)
# ===================
import altair as alt

month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

monthly_df = revenue_df.groupby("invoice_month")["sales_by_kpi_center_usd"].sum().reset_index()
monthly_df["invoice_month"] = pd.Categorical(monthly_df["invoice_month"], categories=month_order, ordered=True)
monthly_df = monthly_df.sort_values("invoice_month")

chart = alt.Chart(monthly_df).mark_bar().encode(
    x=alt.X("invoice_month:N", title="Invoice Month", sort=month_order),
    y=alt.Y("sales_by_kpi_center_usd:Q", title="Revenue (USD)", axis=alt.Axis(format=",", titleFontSize=14)),
    tooltip=[
        alt.Tooltip("invoice_month:N", title="Month"),
        alt.Tooltip("sales_by_kpi_center_usd:Q", title="Revenue (USD)", format=",.0f")
    ]
).properties(
    title="📅 Monthly Revenue",
    width=800,
    height=400
).configure_title(fontSize=20, anchor="start")

st.altair_chart(chart, use_container_width=True)


# ===================
# KPI Center Breakdown theo từng loại KPI Type
# ===================
st.markdown("## 🌐 KPI Center Performance by Type")

# Hàm định dạng và tính GP %
def format_kpi_table(df):
    if df.empty:
        return pd.DataFrame(columns=["kpi_center", "sales_by_kpi_center_usd", "gross_profit_by_kpi_center_usd", "gp_percent"])
    df["sales_by_kpi_center_usd"] = df["sales_by_kpi_center_usd"].astype(float)
    df["gross_profit_by_kpi_center_usd"] = df["gross_profit_by_kpi_center_usd"].astype(float)
    df["gp_percent"] = (df["gross_profit_by_kpi_center_usd"] / df["sales_by_kpi_center_usd"]) * 100
    return df.style.format({
        "sales_by_kpi_center_usd": "{:,.0f}",
        "gross_profit_by_kpi_center_usd": "{:,.0f}",
        "gp_percent": "{:.2f}%"
    })

# Hàm xử lý từng loại KPI
def display_kpi_by_type(title, icon, kpi_type):
    st.markdown(f"### {icon} {title}")
    df = revenue_df[revenue_df["kpi_type"] == kpi_type]
    summary = df.groupby("kpi_center").agg({
        "sales_by_kpi_center_usd": "sum",
        "gross_profit_by_kpi_center_usd": "sum"
    }).reset_index()
    st.dataframe(format_kpi_table(summary), use_container_width=True)

# Gọi từng nhóm KPI
display_kpi_by_type("KPI by Territory", "🗺️", "TERRITORY")
display_kpi_by_type("KPI by Vertical Market", "🏭", "VERTICAL")
display_kpi_by_type("Internal Sales", "🔒", "INTERNAL")


# ===================
# Top 80% Customers by GP
# ===================
st.subheader("🌟 Top 80% Customers by Gross Profit")

# Tính tổng GP và sắp xếp
customer_gp = oc_df.groupby("customer").agg({
    "gross_profit_by_split_usd": "sum",
    "invoiced_amount_usd": "sum"
}).reset_index()

customer_gp["gross_profit_by_split_usd"] = customer_gp["gross_profit_by_split_usd"].astype(float)
customer_gp["invoiced_amount_usd"] = customer_gp["invoiced_amount_usd"].astype(float)
customer_gp["gp_percent"] = (customer_gp["gross_profit_by_split_usd"] / customer_gp["invoiced_amount_usd"]) * 100

# Sắp xếp theo GP
customer_gp = customer_gp.sort_values(by="gross_profit_by_split_usd", ascending=False)

# Tính % cộng dồn
customer_gp["cumulative_percent"] = customer_gp["gross_profit_by_split_usd"].cumsum() / customer_gp["gross_profit_by_split_usd"].sum() * 100

# Lọc top 80%
top_80_gp = customer_gp[customer_gp["cumulative_percent"] <= 80]

# Hiển thị
st.dataframe(top_80_gp.style.format({
    "gross_profit_by_split_usd": "{:,.0f}",
    "invoiced_amount_usd": "{:,.0f}",
    "gp_percent": "{:.2f}%",
    "cumulative_percent": "{:.2f}"
}), use_container_width=True)

# ===================
# Footer
# ===================
st.markdown("---")
st.caption("Generated by Prostech BI Dashboard | Powered by Streamlit")
