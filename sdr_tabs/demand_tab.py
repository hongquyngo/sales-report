import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO

from data_loader import load_outbound_demand_data, load_customer_forecast_data


def show_outbound_demand_tab():
    st.subheader("📤 Outbound Demand by Period")

    output_source = select_data_source()

    df_all = load_and_prepare_data(output_source)
    if df_all.empty:
        st.info("No outbound demand data available.")
        return

    filtered_df, start_date, end_date = apply_outbound_filters(df_all)
    show_outbound_summary(filtered_df)
    show_grouped_demand_summary(filtered_df, start_date, end_date)


def select_data_source():
    return st.radio(
        "Select Outbound Demand Source:",
        ["OC Only", "Forecast Only", "Both"],
        horizontal=True
    )


def load_and_prepare_data(source):
    df_oc, df_fc = pd.DataFrame(), pd.DataFrame()

    if source in ["OC Only", "Both"]:
        df_oc = load_outbound_demand_data()
        df_oc["source_type"] = "OC"

    if source in ["Forecast Only", "Both"]:
        df_fc = load_customer_forecast_data()
        df_fc["source_type"] = "Forecast"

    df_parts = []
    if not df_oc.empty:
        df_parts.append(standardize_df(df_oc, is_forecast=False))
    if not df_fc.empty:
        df_parts.append(standardize_df(df_fc, is_forecast=True))

    if not df_parts:
        return pd.DataFrame()

    return pd.concat(df_parts, ignore_index=True)


def standardize_df(df, is_forecast):
    df = df.copy()
    df['etd'] = pd.to_datetime(df['etd'])
    df['oc_date'] = pd.to_datetime(df.get('oc_date', pd.NaT))

    if is_forecast:
        df['demand_quantity'] = pd.to_numeric(df['selling_quantity'], errors='coerce').fillna(0)
        df['value_in_usd'] = pd.to_numeric(df.get('total_amount_usd', 0), errors='coerce').fillna(0)
    else:
        df['demand_quantity'] = pd.to_numeric(df['pending_delivery_quantity'], errors='coerce').fillna(0)
        df['value_in_usd'] = pd.to_numeric(df.get('outstanding_amount_usd', 0), errors='coerce').fillna(0)

    df['product_pn'] = df['product_pn'].astype(str)
    df['pt_code'] = df['pt_code'].astype(str)
    df['brand'] = df['brand'].astype(str)
    df['legal_entity'] = df['legal_entity'].astype(str)
    df['customer'] = df['customer'].astype(str)

    return df


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


def show_outbound_summary(filtered_df):
    st.markdown("### 🔍 Outbound Demand Details")

    total_unique_products = filtered_df["pt_code"].nunique()
    total_value_usd = filtered_df["value_in_usd"].sum()

    st.markdown(f"🔢 Total Unique Products: **{int(total_unique_products):,}**  💵 Total Value (USD): **${total_value_usd:,.2f}**")

    display_df = filtered_df[[
        "source_type", "product_pn", "brand", "pt_code", "etd", "demand_quantity",
        "value_in_usd", "customer", "legal_entity"
    ]].copy()

    display_df["demand_quantity"] = display_df["demand_quantity"].apply(lambda x: f"{x:,.0f}")
    display_df["value_in_usd"] = display_df["value_in_usd"].apply(lambda x: f"${x:,.2f}")

    st.dataframe(display_df, use_container_width=True)


def show_grouped_demand_summary(filtered_df, start_date, end_date):
    st.markdown("### 📦 Grouped Demand by Product (Pivot View)")
    st.markdown(f"📅 Showing demand from **{start_date}** to **{end_date}**")

    col_period, col_filter = st.columns(2)
    with col_period:
        period = st.selectbox("Group By Period", ["Daily", "Weekly", "Monthly"])
    with col_filter:
        show_only_nonzero = st.checkbox("Show only products with quantity > 0", value=True)

    df_summary = filtered_df.copy()

    if period == "Daily":
        df_summary["period"] = df_summary["etd"].dt.strftime("%Y-%m-%d")
    elif period == "Weekly":
        df_summary["year"] = df_summary["etd"].dt.isocalendar().year
        df_summary["week"] = df_summary["etd"].dt.isocalendar().week
        df_summary["period"] = df_summary["week"].apply(lambda w: f"Week {w:02}") + " - " + df_summary["year"].astype(str)
    else:
        df_summary["year_month"] = df_summary["etd"].dt.to_period("M")
        df_summary["period"] = df_summary["year_month"].dt.strftime("%b %Y")

    pivot_df = (
        df_summary
        .groupby(["product_pn", "pt_code", "period"])
        .agg(total_quantity=("demand_quantity", "sum"))
        .reset_index()
        .pivot(index=["product_pn", "pt_code"], columns="period", values="total_quantity")
        .fillna(0)
        .reset_index()
    )

    pivot_df = sort_period_columns(pivot_df, period)

    if show_only_nonzero:
        pivot_df = pivot_df[pivot_df.iloc[:, 2:].sum(axis=1) > 0]

    pivot_df.iloc[:, 2:] = pivot_df.iloc[:, 2:].applymap(lambda x: f"{x:,.0f}")
    st.dataframe(pivot_df, use_container_width=True)

    # === Totals ===
    df_grouped = df_summary.copy()
    df_grouped["demand_quantity"] = pd.to_numeric(df_grouped["demand_quantity"], errors='coerce').fillna(0)
    df_grouped["value_in_usd"] = pd.to_numeric(df_grouped["value_in_usd"], errors='coerce').fillna(0)

    pivot_qty = df_grouped.groupby("period").agg(total_quantity=("demand_quantity", "sum")).T
    pivot_val = df_grouped.groupby("period").agg(total_value_usd=("value_in_usd", "sum")).T

    pivot_qty.index = ["🔢 TOTAL QUANTITY"]
    pivot_val.index = ["💵 TOTAL VALUE (USD)"]

    pivot_final = pd.concat([pivot_qty, pivot_val])
    pivot_final = pivot_final.reset_index().rename(columns={"index": "Metric"})

    for col in pivot_final.columns[1:]:
        if "🔢 TOTAL QUANTITY" in pivot_final["Metric"].values:
            pivot_final.loc[pivot_final["Metric"] == "🔢 TOTAL QUANTITY", col] = (
                pivot_final.loc[pivot_final["Metric"] == "🔢 TOTAL QUANTITY", col]
                .astype(float)
                .map("{:,.0f}".format)
            )
        if "💵 TOTAL VALUE (USD)" in pivot_final["Metric"].values:
            pivot_final.loc[pivot_final["Metric"] == "💵 TOTAL VALUE (USD)", col] = (
                pivot_final.loc[pivot_final["Metric"] == "💵 TOTAL VALUE (USD)", col]
                .astype(float)
                .map("${:,.2f}".format)
            )


    pivot_final = sort_period_columns(pivot_final, period)

    st.markdown("🔢 Column Total (All Products)")
    st.dataframe(pivot_final, use_container_width=True)

    # === Export Excel ===
    excel_data = convert_df_to_excel(pivot_df)
    st.download_button(
        label="📤 Export to Excel",
        data=excel_data,
        file_name="grouped_outbound_demand.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )



def sort_period_columns(df, period_type):
    cols = df.columns[:2].tolist() if df.columns[0] != "Metric" else df.columns[:1].tolist()

    period_cols = df.columns[len(cols):]

    if period_type == "Weekly":
        sorted_periods = sorted(
            period_cols,
            key=lambda x: (
                int(x.split(" - ")[1]),           # year
                int(x.split(" - ")[0].split(" ")[1])  # week
            )
        )
    elif period_type == "Monthly":
        # Tên period dạng "Jan 2025", "Feb 2025", cần chuyển về datetime để sort
        sorted_periods = sorted(
            period_cols,
            key=lambda x: pd.to_datetime("01 " + x, format="%d %b %Y")
        )
    else:
        return df  # Daily không cần sắp xếp

    return df[cols + sorted_periods]


def convert_df_to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Grouped Demand")
    return output.getvalue()
