import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO

from data_loader import (
    load_inventory_data,
    load_pending_can_data,
    load_pending_po_data
)

def show_inbound_supply_tab():
    st.subheader("📥 Inbound Supply Capability")

    supply_source = select_supply_source()
    exclude_expired = st.checkbox("📅 Exclude expired inventory", value=True, key="supply_expired_checkbox")
    df_all = load_and_prepare_supply_data(supply_source, exclude_expired)

    if df_all.empty:
        st.info("No supply data available.")
        return

    filtered_df, start_date, end_date = apply_supply_filters(df_all)
    show_supply_detail_table(filtered_df)
    show_grouped_supply_summary(filtered_df, start_date, end_date)


def select_supply_source():
    return st.radio(
        "Select Supply Source:",
        ["Inventory Only", "Pending CAN Only", "Pending PO Only", "All"],
        horizontal=True,
        key="supply_source_radio"
    )


def load_and_prepare_supply_data(supply_source, exclude_expired=True):
    today = pd.to_datetime("today").normalize()
    df_parts = []

    if supply_source in ["Inventory Only", "All"]:
        inv_df = load_inventory_data()
        inv_df["source_type"] = "Inventory"
        inv_df["date_ref"] = today
        inv_df["quantity"] = pd.to_numeric(inv_df["remaining_quantity"], errors="coerce").fillna(0)
        inv_df["value_in_usd"] = pd.to_numeric(inv_df["inventory_value_usd"], errors="coerce").fillna(0)
        inv_df["legal_entity"] = inv_df["owning_company_name"]
        inv_df["expiry_date"] = pd.to_datetime(inv_df["expiry_date"], errors="coerce")
        if exclude_expired:
            inv_df = inv_df[(inv_df["expiry_date"].isna()) | (inv_df["expiry_date"] >= today)]
        df_parts.append(inv_df)

    if supply_source in ["Pending CAN Only", "All"]:
        can_df = load_pending_can_data()
        can_df["source_type"] = "Pending CAN"
        can_df["date_ref"] = pd.to_datetime(can_df["arrival_date"], errors="coerce")
        can_df["quantity"] = pd.to_numeric(can_df["pending_quantity"], errors="coerce").fillna(0)
        can_df["value_in_usd"] = pd.to_numeric(can_df["pending_value_usd"], errors="coerce").fillna(0)
        can_df["legal_entity"] = can_df["consignee"]
        df_parts.append(can_df)

    if supply_source in ["Pending PO Only", "All"]:
        po_df = load_pending_po_data()
        po_df["source_type"] = "Pending PO"
        po_df["date_ref"] = pd.to_datetime(po_df["cargo_ready_date"], errors="coerce")
        po_df["quantity"] = pd.to_numeric(po_df["pending_standard_arrival_quantity"], errors="coerce").fillna(0)
        po_df["value_in_usd"] = pd.to_numeric(po_df["outstanding_arrival_amount_usd"], errors="coerce").fillna(0)
        po_df["legal_entity"] = po_df["legal_entity"]
        df_parts.append(po_df)

    if not df_parts:
        return pd.DataFrame()

    def standardize(df):
        df["pt_code"] = df["pt_code"].astype(str)
        df["product_name"] = df.get("product_name", "").astype(str)
        df["brand"] = df.get("brand", "").astype(str)
        df["standard_uom"] = df.get("standard_uom", "")
        df["package_size"] = df.get("package_size", "")
        return df[[
            "source_type", "pt_code", "product_name", "brand", "package_size", "standard_uom",
            "legal_entity", "date_ref", "quantity", "value_in_usd"
        ]]


    return pd.concat([standardize(df) for df in df_parts], ignore_index=True)




def apply_supply_filters(df):

    with st.expander("📎 Filters", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            selected_entity = st.multiselect("Legal Entity", df["legal_entity"].dropna().unique(), key="supply_legal_entity")
        with col2:
            selected_brand = st.multiselect("Brand", df["brand"].dropna().unique(), key="supply_brand")
        with col3:
            selected_pt = st.multiselect("PT Code", df["pt_code"].dropna().unique(), key="supply_pt_code")

        col4, col5 = st.columns(2)
        with col4:
            start_date = st.date_input("From Date (Reference)", df["date_ref"].min().date(), key="supply_start_date")
        with col5:
            end_date = st.date_input("To Date (Reference)", df["date_ref"].max().date(), key="supply_end_date")

    filtered_df = df.copy()
    if selected_entity:
        filtered_df = filtered_df[filtered_df["legal_entity"].isin(selected_entity)]
    if selected_brand:
        filtered_df = filtered_df[filtered_df["brand"].isin(selected_brand)]
    if selected_pt:
        filtered_df = filtered_df[filtered_df["pt_code"].isin(selected_pt)]

    filtered_df = filtered_df[
        (filtered_df["date_ref"].dt.date >= start_date) &
        (filtered_df["date_ref"].dt.date <= end_date)
    ]

    return filtered_df, start_date, end_date

def show_supply_detail_table(df):
    st.markdown("### 📄 Supply Capability Detail")

    total_unique_products = df["pt_code"].nunique()
    total_value_usd = df["value_in_usd"].sum()

    st.markdown(f"🔢 Total Unique Products: **{int(total_unique_products):,}**  💵 Total Value (USD): **${total_value_usd:,.2f}**")

    df_disp = df.copy()
    df_disp["quantity"] = df_disp["quantity"].apply(lambda x: f"{x:,.0f}")
    df_disp["value_in_usd"] = df_disp["value_in_usd"].apply(lambda x: f"${x:,.2f}")
    df_disp["date_ref"] = pd.to_datetime(df_disp["date_ref"], errors="coerce").dt.strftime("%Y-%m-%d")

    st.dataframe(df_disp[[
        "source_type", "pt_code", "product_name", "brand", "package_size", "standard_uom",
        "legal_entity", "date_ref", "quantity", "value_in_usd"
    ]], use_container_width=True)



def show_grouped_supply_summary(df, start_date, end_date):
    st.markdown("### 📊 Grouped Supply by Period")
    st.markdown(f"📅 From **{start_date}** to **{end_date}**")

    col1, col2 = st.columns(2)
    with col1:
        period = st.selectbox("Group by Period", ["Daily", "Weekly", "Monthly"])
    with col2:
        show_only_nonzero = st.checkbox("Show only products with quantity > 0", value=True, key="supply_show_nonzero")

    df_summary = df.copy()

    if period == "Daily":
        df_summary["period"] = df_summary["date_ref"].dt.strftime("%Y-%m-%d")
    elif period == "Weekly":
        df_summary["year"] = df_summary["date_ref"].dt.isocalendar().year
        df_summary["week"] = df_summary["date_ref"].dt.isocalendar().week
        df_summary["period"] = df_summary["week"].apply(lambda w: f"Week {w:02}") + " - " + df_summary["year"].astype(str)
    else:
        df_summary["year_month"] = df_summary["date_ref"].dt.to_period("M")
        df_summary["period"] = df_summary["year_month"].dt.strftime("%b %Y")

    pivot_df = (
        df_summary
        .groupby(["product_name", "pt_code", "period"])
        .agg(total_quantity=("quantity", "sum"))
        .reset_index()
        .pivot(index=["product_name", "pt_code"], columns="period", values="total_quantity")
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
    df_grouped["quantity"] = pd.to_numeric(df_grouped["quantity"], errors="coerce").fillna(0)
    df_grouped["value_in_usd"] = pd.to_numeric(df_grouped["value_in_usd"], errors="coerce").fillna(0)

    pivot_qty = df_grouped.groupby("period").agg(total_quantity=("quantity", "sum")).T
    pivot_val = df_grouped.groupby("period").agg(total_value_usd=("value_in_usd", "sum")).T

    pivot_qty.index = ["🔢 TOTAL QUANTITY"]
    pivot_val.index = ["💰 TOTAL VALUE (USD)"]

    pivot_final = pd.concat([pivot_qty, pivot_val])
    pivot_final = pivot_final.reset_index().rename(columns={"index": "Metric"})

    for col in pivot_final.columns[1:]:
        if "🔢 TOTAL QUANTITY" in pivot_final["Metric"].values:
            pivot_final.loc[pivot_final["Metric"] == "🔢 TOTAL QUANTITY", col] = (
                pivot_final.loc[pivot_final["Metric"] == "🔢 TOTAL QUANTITY", col]
                .astype(float).map("{:,.0f}".format)
            )
        if "💰 TOTAL VALUE (USD)" in pivot_final["Metric"].values:
            pivot_final.loc[pivot_final["Metric"] == "💰 TOTAL VALUE (USD)", col] = (
                pivot_final.loc[pivot_final["Metric"] == "💰 TOTAL VALUE (USD)", col]
                .astype(float).map("${:,.2f}".format)
            )


    pivot_final = sort_period_columns(pivot_final, period)

    st.markdown("🔢 Column Total (All Products)")
    st.dataframe(pivot_final, use_container_width=True)

    export_data = convert_df_to_excel(pivot_df)
    st.download_button(
        label="📤 Export Grouped Supply to Excel",
        data=export_data,
        file_name="grouped_supply_by_period.xlsx",
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
        df.to_excel(writer, index=False, sheet_name="Grouped Supply")
    return output.getvalue()
