import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime


# =========================
# 📊 Main GAP Calculation with Carry-Forward Logic
# =========================
# def calculate_gap_with_carry_forward(df_demand, df_supply, period_type="Weekly"):
#     df_d = df_demand.copy()
#     df_s = df_supply.copy()

#     df_d["period"] = convert_to_period(df_d["etd"], period_type)
#     df_s["period"] = convert_to_period(df_s["date_ref"], period_type)

#     demand_grouped = df_d.groupby(["pt_code", "product_name", "package_size", "standard_uom", "period"]).agg(
#         total_demand_qty=("demand_quantity", "sum")
#     ).reset_index()

#     supply_grouped = df_s.groupby(["pt_code", "product_name", "package_size", "standard_uom", "period"]).agg(
#         total_supply_qty=("quantity", "sum")
#     ).reset_index()

#     all_periods = sorted(set(demand_grouped["period"]).union(set(supply_grouped["period"])))

#     all_keys = pd.concat([
#         demand_grouped[["pt_code", "product_name", "package_size", "standard_uom"]],
#         supply_grouped[["pt_code", "product_name", "package_size", "standard_uom"]]
#     ]).drop_duplicates()

#     results = []
#     for _, row in all_keys.iterrows():
#         pt_code = row["pt_code"]
#         product_name = row["product_name"]
#         package_size = row["package_size"]
#         uom = row["standard_uom"]
#         carry_forward_qty = 0

#         for period in all_periods:
#             demand = demand_grouped[(demand_grouped["pt_code"] == pt_code) & (demand_grouped["period"] == period)]["total_demand_qty"].sum()
#             supply = supply_grouped[(supply_grouped["pt_code"] == pt_code) & (supply_grouped["period"] == period)]["total_supply_qty"].sum()

#             total_available = carry_forward_qty + supply
#             gap = total_available - demand
#             fulfill_rate = (total_available / demand * 100) if demand > 0 else 100
#             status = "✅ Fullfilled" if gap >= 0 else "❌ Shortage"

#             results.append({
#                 "pt_code": pt_code,
#                 "product_name": product_name,
#                 "package_size": package_size,
#                 "standard_uom": uom,
#                 "period": period,
#                 "begin_inventory": carry_forward_qty,
#                 "supply_in_period": supply,
#                 "total_available": total_available,
#                 "total_demand_qty": demand,
#                 "gap_quantity": gap,
#                 "fulfillment_rate_percent": fulfill_rate,
#                 "fulfillment_status": status,
#             })

#             carry_forward_qty = max(0, gap)

#     return pd.DataFrame(results)


def calculate_gap_with_carry_forward(df_demand, df_supply, period_type="Weekly"):
    df_d = df_demand.copy()
    df_s = df_supply.copy()

    # Convert period
    df_d["period"] = convert_to_period(df_d["etd"], period_type)
    df_s["period"] = convert_to_period(df_s["date_ref"], period_type)

    # Group demand and supply
    demand_grouped = df_d.groupby(["pt_code", "product_name", "package_size", "standard_uom", "period"]).agg(
        total_demand_qty=("demand_quantity", "sum")
    ).reset_index()

    supply_grouped = df_s.groupby(["pt_code", "product_name", "package_size", "standard_uom", "period"]).agg(
        total_supply_qty=("quantity", "sum")
    ).reset_index()

    # Sort periods by actual datetime (fix carry-forward order)
    all_periods_raw = list(set(demand_grouped["period"]).union(set(supply_grouped["period"])))
    all_periods = sorted(all_periods_raw, key=lambda x: get_period_datetime(x, period_type))

    # Get all unique products
    all_keys = pd.concat([
        demand_grouped[["pt_code", "product_name", "package_size", "standard_uom"]],
        supply_grouped[["pt_code", "product_name", "package_size", "standard_uom"]]
    ]).drop_duplicates()

    results = []
    for _, row in all_keys.iterrows():
        pt_code = row["pt_code"]
        product_name = row["product_name"]
        package_size = row["package_size"]
        uom = row["standard_uom"]
        carry_forward_qty = 0

        for period in all_periods:
            demand = demand_grouped[
                (demand_grouped["pt_code"] == pt_code) & 
                (demand_grouped["period"] == period)
            ]["total_demand_qty"].sum()

            supply = supply_grouped[
                (supply_grouped["pt_code"] == pt_code) & 
                (supply_grouped["period"] == period)
            ]["total_supply_qty"].sum()

            total_available = carry_forward_qty + supply
            gap = total_available - demand
            fulfill_rate = (total_available / demand * 100) if demand > 0 else 100
            status = "✅ Fullfilled" if gap >= 0 else "❌ Shortage"

            results.append({
                "pt_code": pt_code,
                "product_name": product_name,
                "package_size": package_size,
                "standard_uom": uom,
                "period": period,
                "begin_inventory": carry_forward_qty,
                "supply_in_period": supply,
                "total_available": total_available,
                "total_demand_qty": demand,
                "gap_quantity": gap,
                "fulfillment_rate_percent": fulfill_rate,
                "fulfillment_status": status,
            })

            carry_forward_qty = max(0, gap)  # only forward surplus

    return pd.DataFrame(results)


# =========================
# 🔎 Demand & Supply Filters
# =========================
def apply_demand_filters(df):
    with st.expander("📎 Demand Filters", expanded=False):
        col1, col2, col3 = st.columns(3)
        selected_entity = col1.multiselect("Legal Entity", df["legal_entity"].dropna().unique(), key="gap_demand_entity")
        selected_customer = col2.multiselect("Customer", df["customer"].dropna().unique(), key="gap_demand_customer")
        selected_pt = col3.multiselect("PT Code", df["pt_code"].dropna().unique(), key="gap_demand_pt")

        col4, col5 = st.columns(2)
        start_date = col4.date_input("From Date (ETD)", df["etd"].min().date(), key="gap_demand_start_date")
        end_date = col5.date_input("To Date (ETD)", df["etd"].max().date(), key="gap_demand_end_date")

    df = df.copy()
    if selected_entity:
        df = df[df["legal_entity"].isin(selected_entity)]
    if selected_customer:
        df = df[df["customer"].isin(selected_customer)]
    if selected_pt:
        df = df[df["pt_code"].isin(selected_pt)]

    # Convert & Filter ETD safely
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    df = df[(df["etd"].isna()) | ((df["etd"] >= start_date) & (df["etd"] <= end_date))]

    return df


def apply_supply_filters(df):
    with st.expander("📎 Supply Filters", expanded=False):
        col1, col2, col3 = st.columns(3)
        selected_entity = col1.multiselect("Legal Entity", df["legal_entity"].dropna().unique(), key="gap_supply_entity")
        selected_brand = col2.multiselect("Brand", df["brand"].dropna().unique(), key="gap_supply_brand")
        selected_pt = col3.multiselect("PT Code", df["pt_code"].dropna().unique(), key="gap_supply_pt")

        col4, col5 = st.columns(2)
        start_date = col4.date_input("From Date (Ref)", df["date_ref"].min().date(), key="gap_supply_start_date")
        end_date = col5.date_input("To Date (Ref)", df["date_ref"].max().date(), key="gap_supply_end_date")

        exclude_expired = st.checkbox("📅 Exclude expired inventory", value=True, key="gap_exclude_expired")

    df = df.copy()
    if selected_entity:
        df = df[df["legal_entity"].isin(selected_entity)]
    if selected_brand:
        df = df[df["brand"].isin(selected_brand)]
    if selected_pt:
        df = df[df["pt_code"].isin(selected_pt)]
    df = df[(df["date_ref"].dt.date >= start_date) & (df["date_ref"].dt.date <= end_date)]
    if exclude_expired and "expiry_date" in df.columns:
        today = pd.to_datetime("today").normalize()
        df = df[(df["expiry_date"].isna()) | (df["expiry_date"] >= today)]
    return df


# =========================
# 📊 Streamlit Tab Entry
# =========================
def show_gap_analysis_tab(df_demand_all_sources, df_supply_all_sources):
    st.subheader("📊 Inventory GAP Analysis (Carry-Forward Logic)")

    col1, col2 = st.columns(2)
    selected_demand_sources = col1.multiselect("Select Demand Sources", df_demand_all_sources["source_type"].unique(), default=list(df_demand_all_sources["source_type"].unique()), key="gap_demand_sources")
    selected_supply_sources = col2.multiselect("Select Supply Sources", df_supply_all_sources["source_type"].unique(), default=list(df_supply_all_sources["source_type"].unique()), key="gap_supply_sources")

    df_demand = df_demand_all_sources[df_demand_all_sources["source_type"].isin(selected_demand_sources)]
    df_supply = df_supply_all_sources[df_supply_all_sources["source_type"].isin(selected_supply_sources)]

    df_demand = apply_demand_filters(df_demand)
    df_supply = apply_supply_filters(df_supply)

    col1, col2 = st.columns(2)
    period_type = col1.selectbox("Group By Period", ["Daily", "Weekly", "Monthly"], index=2, key="gap_period_type")
    show_shortage_only = col2.checkbox("🔎 Show only shortages", value=True, key="gap_shortage_checkbox")

    gap_df = calculate_gap_with_carry_forward(df_demand, df_supply, period_type)
    if show_shortage_only:
        gap_df = gap_df[gap_df["gap_quantity"] < 0]

    st.markdown("### 📄 GAP Details by Product & Period")
    total_unique_products = gap_df["pt_code"].nunique()
    total_gap = gap_df["gap_quantity"].where(gap_df["gap_quantity"] < 0).abs().sum()
    st.markdown(f"🔢 Total Unique Products: **{int(total_unique_products):,}**  💵 Total Shortage Quantity: **{total_gap:,.0f}**")

    st.dataframe(gap_df, use_container_width=True)

    # === PIVOT VIEW ===
    st.markdown("### 📊 Pivot View by GAP Quantity")
    style_mode = st.radio(
        "🎨 Styling Mode for Pivot Table",
        options=["None", "🔴 Highlight Shortage", "🌈 Heatmap"],
        horizontal=True,
        key="gap_style_mode"
    )

    pivot_gap = (
        gap_df.groupby(["product_name", "pt_code", "period"])
        .agg(gap_quantity=("gap_quantity", "sum"))
        .reset_index()
        .pivot(index=["product_name", "pt_code"], columns="period", values="gap_quantity")
        .fillna(0)
        .reset_index()
    )
    pivot_gap = sort_period_columns(pivot_gap, period_type)

    if show_shortage_only:
        pivot_gap = pivot_gap[pivot_gap.iloc[:, 2:].apply(lambda row: any(row < 0), axis=1)]

    # ✅ Làm tròn
    pivot_gap.iloc[:, 2:] = pivot_gap.iloc[:, 2:].applymap(lambda x: f"{x:,.1f}")

    if style_mode == "🔴 Highlight Shortage":
        def highlight_neg(val):
            try:
                val = float(val)
                if val < 0:
                    return "background-color: #fdd; color: red; font-weight: bold;"
            except:
                return ""
            return ""
        st.dataframe(pivot_gap.style.applymap(highlight_neg, subset=pivot_gap.columns[2:]), use_container_width=True)

    elif style_mode == "🌈 Heatmap":
        st.dataframe(pivot_gap.style.background_gradient(
            cmap='RdYlGn_r', subset=pivot_gap.columns[2:], axis=1
        ), use_container_width=True)

    else:
        st.dataframe(pivot_gap, use_container_width=True)

    # === Export buttons ===
    st.download_button("📊 Export GAP Pivot to Excel", convert_df_to_excel(pivot_gap), "gap_analysis_pivot.xlsx")

    st.download_button("📤 Export GAP Details to Excel", convert_df_to_excel(gap_df), "gap_analysis_details.xlsx")



# =========================
# 🔧 Utility: Convert period format
# =========================
def convert_to_period(series, period_type):
    if period_type == "Daily":
        return series.dt.strftime("%Y-%m-%d")
    elif period_type == "Weekly":
        return series.dt.isocalendar().week.astype(str).radd("Week ") + " - " + series.dt.isocalendar().year.astype(str)
    elif period_type == "Monthly":
        return series.dt.to_period("M").dt.strftime("%b %Y")
    else:
        return series.astype(str)


def get_period_datetime(period_str, period_type):
    if period_type == "Weekly":
        try:
            week, year = int(period_str.split(" - ")[0].replace("Week ", "")), int(period_str.split(" - ")[1])
            return datetime.strptime(f'{year}-W{week}-1', "%Y-W%W-%w")
        except:
            return pd.Timestamp.max
    elif period_type == "Monthly":
        try:
            return pd.to_datetime("01 " + period_str, format="%d %b %Y")
        except:
            return pd.Timestamp.max
    elif period_type == "Daily":
        try:
            return pd.to_datetime(period_str, format="%Y-%m-%d")
        except:
            return pd.Timestamp.max
    else:
        return pd.Timestamp.max


# =========================
# 📋 Helper: Sort period columns
# =========================
def sort_period_columns(df, period_type):
    cols = df.columns[:2].tolist() if df.columns[0] != "Metric" else df.columns[:1].tolist()
    period_cols = df.columns[len(cols):]

    if period_type == "Weekly":
        def safe_parse_week(x):
            try:
                parts = x.split(" - ")
                week = int(parts[0].replace("Week ", "").strip())
                year = int(parts[1].strip())
                return (year, week)
            except:
                return (9999, 99)
        sorted_periods = sorted(period_cols, key=safe_parse_week)

    elif period_type == "Monthly":
        sorted_periods = sorted(
            period_cols,
            key=lambda x: pd.to_datetime("01 " + x, format="%d %b %Y", errors="coerce") or pd.Timestamp.max
        )
    else:
        sorted_periods = sorted(period_cols)

    return df[cols + sorted_periods]

# =========================
# 📋 Helper: Export to Excel
# =========================
def convert_df_to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="GAP Analysis")
    return output.getvalue()
