from data_loader import load_outbound_demand_data
import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO


def show_outbound_demand_tab():
    st.subheader("📤 Outbound Demand by Period")

    df = load_outbound_demand_data()
    if df.empty:
        st.info("No outbound demand data available.")
        return

    df['etd'] = pd.to_datetime(df['etd'])
    df['oc_date'] = pd.to_datetime(df['oc_date'])

    # =========================
    # 🔍 Filter Controls
    # =========================
    filtered_df, start_date, end_date = apply_outbound_filters(df)

    # =========================
    # 📋 Outbound Demand Detail
    # =========================
    st.markdown("### 🔍 Outbound Demand Details")
    st.dataframe(filtered_df, use_container_width=True)

    # =========================
    # 📦 Grouped Demand by Product
    # =========================
    show_grouped_demand_summary(filtered_df, start_date, end_date)


def apply_outbound_filters(df):
    with st.expander("📎 Filters", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            selected_entity = st.multiselect("Legal Entity", df["legal_entity"].dropna().unique())
        with col2:
            selected_customer = st.multiselect("Customer", df["customer"].dropna().unique())
        with col3:
            selected_product = st.multiselect("PT Code", df["pt_code"].dropna().unique())

        col4, col5, col6 = st.columns(3)
        with col4:
            selected_brand = st.multiselect("Brand", df["brand"].dropna().unique())
        with col5:
            start_date = st.date_input("From Date (ETD)", df["etd"].min().date())
        with col6:
            end_date = st.date_input("To Date (ETD)", df["etd"].max().date())

    filtered_df = df.copy()
    if selected_entity:
        filtered_df = filtered_df[filtered_df["legal_entity"].isin(selected_entity)]
    if selected_customer:
        filtered_df = filtered_df[filtered_df["customer"].isin(selected_customer)]
    if selected_product:
        filtered_df = filtered_df[filtered_df["pt_code"].isin(selected_product)]
    if selected_brand:
        filtered_df = filtered_df[filtered_df["brand"].isin(selected_brand)]
    if start_date and end_date:
        filtered_df = filtered_df[
            (filtered_df["etd"].dt.date >= start_date) &
            (filtered_df["etd"].dt.date <= end_date)
        ]

    return filtered_df, start_date, end_date


def show_grouped_demand_summary(filtered_df, start_date, end_date):
    st.markdown("### 📦 Grouped Demand by Product (Pivot View)")

    st.markdown(f"📅 Showing demand from **{start_date}** to **{end_date}**")

    col_period, col_filter = st.columns(2)
    with col_period:
        period = st.selectbox("Group By Period", ["Daily", "Weekly", "Monthly"])
    with col_filter:
        show_only_nonzero = st.checkbox("Show only products with quantity > 0", value=True)

    df_summary = filtered_df.copy()

    # ==== Create Period Column ====
    if period == "Daily":
        df_summary["period"] = df_summary["etd"].dt.strftime("%Y-%m-%d")
    elif period == "Weekly":
        df_summary["year"] = df_summary["etd"].dt.isocalendar().year
        df_summary["week"] = df_summary["etd"].dt.isocalendar().week
        df_summary["period"] = df_summary["week"].apply(lambda w: f"Week {w:02}") + " - " + df_summary["year"].astype(str)
    else:  # Monthly
        df_summary["year_month"] = df_summary["etd"].dt.to_period("M")
        df_summary["period"] = df_summary["year_month"].dt.strftime("%b %Y")


    # ==== Pivot Table ====
    pivot_df = (
        df_summary
        .groupby(["product_pn", "pt_code", "period"])
        .agg(total_quantity=("selling_quantity", "sum"))
        .reset_index()
        .pivot(index=["product_pn", "pt_code"], columns="period", values="total_quantity")
        .fillna(0)
        .reset_index()
    )

    # ==== Sort Columns Chronologically ====
    if period == "Weekly":
        cols = pivot_df.columns[:2].tolist()
        sorted_periods = sorted(pivot_df.columns[2:], key=lambda x: (
            int(x.split(" - ")[1]),   # year
            int(x.split(" - ")[0].split(" ")[1])  # week number
        ))
        pivot_df = pivot_df[cols + sorted_periods]

    if period == "Monthly":
        cols = pivot_df.columns[:2].tolist()
        
        sorted_periods = (
            df_summary[["period", "year_month"]]
            .drop_duplicates()
            .sort_values("year_month")
            .set_index("period")
            .index.tolist()
        )
        
        pivot_df = pivot_df[cols + [p for p in sorted_periods if p in pivot_df.columns]]


    # ==== Filter Non-zero Rows ====
    if show_only_nonzero:
        pivot_df = pivot_df[pivot_df.iloc[:, 2:].sum(axis=1) > 0]

    # ==== Display ====
    st.dataframe(pivot_df, use_container_width=True)

    # ==== Export Excel ====
    def convert_df_to_excel(df):
        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Grouped Demand")
        return output.getvalue()

    excel_data = convert_df_to_excel(pivot_df)
    st.download_button(
        label="📤 Export to Excel",
        data=excel_data,
        file_name="grouped_outbound_demand.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
