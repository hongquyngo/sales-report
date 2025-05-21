import streamlit as st
import pandas as pd
from io import BytesIO

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


# =========================
# 📊 Main GAP Calculation with Carry-Forward Logic
# =========================
def calculate_gap_with_carry_forward(df_demand, df_supply, period_type="Weekly"):
    df_d = df_demand.copy()
    df_s = df_supply.copy()

    df_d["period"] = convert_to_period(df_d["etd"], period_type)
    df_s["period"] = convert_to_period(df_s["date_ref"], period_type)

    # Aggregate demand and supply by product and period
    demand_grouped = df_d.groupby(["pt_code", "product_name", "package_size", "standard_uom", "period"]).agg(
        total_demand_qty=("demand_quantity", "sum")
    ).reset_index()

    supply_grouped = df_s.groupby(["pt_code", "product_name", "package_size", "standard_uom", "period"]).agg(
        total_supply_qty=("quantity", "sum")
    ).reset_index()

    # Build timeline: ordered list of periods
    all_periods = sorted(
        set(demand_grouped["period"]).union(set(supply_grouped["period"]))
    )

    # Get all unique product combinations
    all_keys = pd.concat([demand_grouped, supply_grouped])[["pt_code", "product_name", "package_size", "standard_uom"]].drop_duplicates()

    results = []

    # Loop through each product and each period sequentially to apply carry-forward logic
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

            carry_forward_qty = max(0, gap)  # Surplus carried into next period

    return pd.DataFrame(results)


# =========================
# 📋 Helper: Export to Excel
# =========================
def convert_df_to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="GAP Analysis")
    return output.getvalue()


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
# 📊 Streamlit Tab Entry
# =========================
def show_gap_analysis_tab(df_demand_all_sources, df_supply_all_sources):
    st.subheader("📊 Inventory GAP Analysis (Carry-Forward Logic)")

    # Filter by selected sources
    st.markdown("#### 🧮 Data Source Filters")
    col1, col2 = st.columns(2)
    with col1:
        selected_demand_sources = st.multiselect(
            "Select Demand Sources",
            options=df_demand_all_sources["source_type"].unique().tolist(),
            default=df_demand_all_sources["source_type"].unique().tolist(),
            key="gap_demand_sources"
        )
    with col2:
        selected_supply_sources = st.multiselect(
            "Select Supply Sources",
            options=df_supply_all_sources["source_type"].unique().tolist(),
            default=df_supply_all_sources["source_type"].unique().tolist(),
            key="gap_supply_sources"
        )

    df_demand = df_demand_all_sources[df_demand_all_sources["source_type"].isin(selected_demand_sources)].copy()
    df_supply = df_supply_all_sources[df_supply_all_sources["source_type"].isin(selected_supply_sources)].copy()

    # Period control
    col1, col2 = st.columns(2)
    with col1:
        period_type = st.selectbox("Group By Period", ["Daily", "Weekly", "Monthly"], index=1, key="gap_period_type")
    with col2:
        show_shortage_only = st.checkbox("🔎 Show only shortages", value=True, key="gap_shortage_checkbox")

    gap_df = calculate_gap_with_carry_forward(df_demand, df_supply, period_type)

    if show_shortage_only:
        gap_df = gap_df[gap_df["gap_quantity"] < 0]

    # Display Details Table
    st.markdown("### 📄 GAP Details by Product & Period")

    total_unique_products = gap_df["pt_code"].nunique()
    total_value_usd = gap_df["gap_quantity"].where(gap_df["gap_quantity"] < 0).abs().sum()
    st.markdown(f"🔢 Total Unique Products: **{int(total_unique_products):,}**  💵 Total Shortage Value (units): **{total_value_usd:,.0f}**")

    df_display = gap_df.copy()
    df_display["gap_quantity"] = df_display["gap_quantity"].map("{:,.0f}".format)
    df_display["total_demand_qty"] = df_display["total_demand_qty"].map("{:,.0f}".format)
    df_display["supply_in_period"] = df_display["supply_in_period"].map("{:,.0f}".format)
    df_display["begin_inventory"] = df_display["begin_inventory"].map("{:,.0f}".format)
    df_display["fulfillment_rate_percent"] = df_display["fulfillment_rate_percent"].map("{:.1f}%".format)

    def highlight_shortage(row):
        if "❌" in row["fulfillment_status"]:
            return ["background-color: #ffe6e6"] * len(row)
        return [""] * len(row)

    st.dataframe(
        df_display.style.apply(highlight_shortage, axis=1),
        use_container_width=True
    )

    # Display Pivot Table
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

    # Export buttons
    st.download_button("📤 Export GAP Details to Excel", convert_df_to_excel(gap_df), "gap_analysis_details.xlsx")
    st.download_button("📊 Export GAP Pivot to Excel", convert_df_to_excel(pivot_gap), "gap_analysis_pivot.xlsx")
