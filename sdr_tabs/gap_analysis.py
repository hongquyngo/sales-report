import streamlit as st
import pandas as pd
from io import BytesIO


def calculate_gap_by_period(df_demand, df_supply, period_type="Weekly"):
    df_d = df_demand.copy()
    df_s = df_supply.copy()

    df_d["period"] = convert_to_period(df_d["etd"], period_type)
    df_s["period"] = convert_to_period(df_s["date_ref"], period_type)

    demand_grouped = (
        df_d.groupby(["pt_code", "product_pn", "package_size", "standard_uom", "period"])
        .agg(total_demand_qty=("demand_quantity", "sum"))
        .reset_index()
    )

    supply_grouped = (
        df_s.groupby(["pt_code", "product_name", "package_size", "standard_uom", "period"])
        .agg(total_supply_qty=("quantity", "sum"))
        .reset_index()
        .rename(columns={"product_name": "product_pn"})  # unify name with demand
    )

    gap_df = pd.merge(
        demand_grouped,
        supply_grouped,
        on=["pt_code", "product_pn", "package_size", "standard_uom", "period"],
        how="outer"
    ).fillna(0)

    gap_df["gap_quantity"] = gap_df["total_supply_qty"] - gap_df["total_demand_qty"]
    gap_df["fulfillment_rate_percent"] = gap_df.apply(
        lambda row: 100 * row["total_supply_qty"] / row["total_demand_qty"]
        if row["total_demand_qty"] > 0 else 100,
        axis=1
    )
    gap_df["fulfillment_status"] = gap_df["gap_quantity"].apply(
        lambda x: "✅ Fullfilled" if x >= 0 else "❌ Shortage"
    )

    return gap_df


def convert_to_period(series, period_type):
    if period_type == "Daily":
        return series.dt.strftime("%Y-%m-%d")
    elif period_type == "Weekly":
        return series.dt.isocalendar().week.astype(str).radd("W").add(" - ").add(series.dt.isocalendar().year.astype(str))
    elif period_type == "Monthly":
        return series.dt.to_period("M").dt.strftime("%b %Y")
    else:
        return series.astype(str)


def show_gap_analysis_tab(df_demand_all_sources, df_supply_all_sources):
    st.subheader("📊 Inventory GAP Analysis")

    # === Source Selectors ===
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

    # === Period & Filter Options ===
    col1, col2 = st.columns(2)
    with col1:
        period_type = st.selectbox("Group By Period", ["Daily", "Weekly", "Monthly"], index=1, key="gap_period_type")
    with col2:
        show_shortage_only = st.checkbox("🔎 Show only shortages", value=True, key="gap_shortage_checkbox")

    gap_df = calculate_gap_by_period(df_demand, df_supply, period_type)

    if show_shortage_only:
        gap_df = gap_df[gap_df["gap_quantity"] < 0]


    # ===================== 📄 GAP Details =====================
    st.markdown("### 📄 GAP Details by Product & Period")

    df_display = gap_df.copy()

    # Format numeric columns
    df_display["total_demand_qty"] = df_display["total_demand_qty"].map("{:,.0f}".format)
    df_display["total_supply_qty"] = df_display["total_supply_qty"].map("{:,.0f}".format)
    df_display["gap_quantity"] = df_display["gap_quantity"].map("{:,.0f}".format)
    df_display["fulfillment_rate_percent"] = df_display["fulfillment_rate_percent"].map("{:.1f}%".format)

    # Reorder columns
    df_display = df_display[
        ["pt_code", "product_pn", "package_size", "standard_uom", "period",
        "total_demand_qty", "total_supply_qty", "gap_quantity", "fulfillment_rate_percent", "fulfillment_status"]
    ]

    def highlight_gap(val):
        try:
            val_float = float(val.replace(",", "").replace("$", "").replace("%", ""))
            if val_float < 0:
                return "color: red;"
        except:
            return ""
        return ""

    styled_df = df_display.style.applymap(highlight_gap, subset=["gap_quantity"])
    st.dataframe(styled_df, use_container_width=True)


    # ===================== 📊 Pivot View =====================
    st.markdown("### 📊 Pivot View by GAP Quantity")

    # Chọn chế độ style
    style_mode = st.radio(
        "🎨 Styling Mode for Pivot Table",
        options=["None", "🔴 Highlight Shortage", "🌈 Heatmap"],
        horizontal=True,
        key="gap_style_mode"
    )

    # Tạo pivot view
    pivot_gap = (
        gap_df.groupby(["product_pn", "pt_code", "period"])
        .agg(gap_quantity=("gap_quantity", "sum"))
        .reset_index()
        .pivot(index=["product_pn", "pt_code"], columns="period", values="gap_quantity")
        .fillna(0)
        .reset_index()
    )

    pivot_gap = sort_period_columns(pivot_gap, period_type)

    if show_shortage_only:
        pivot_gap = pivot_gap[pivot_gap.iloc[:, 2:].apply(lambda row: any(row < 0), axis=1)]

    # Highlight logic
    def highlight_gap_advanced(val):
        try:
            val = float(val)
            if val < 0:
                return "background-color: #fdd; color: red; font-weight: bold;"
            elif val == 0:
                return "color: gray;"
        except:
            return ""
        return ""

    # Apply styling based on mode
    if style_mode == "🔴 Highlight Shortage":
        styled_df = pivot_gap.style.applymap(highlight_gap_advanced, subset=pivot_gap.columns[2:])
        st.dataframe(styled_df, use_container_width=True)

    elif style_mode == "🌈 Heatmap":
        styled_df = pivot_gap.style.background_gradient(
            cmap='RdYlGn_r', subset=pivot_gap.columns[2:], axis=1
        )
        st.dataframe(styled_df, use_container_width=True)

    else:
        st.dataframe(pivot_gap, use_container_width=True)





    # ===================== 📤 Export =====================
    export_details = convert_df_to_excel(gap_df)
    st.download_button("📤 Export GAP Details to Excel", export_details, "gap_analysis_details.xlsx")

    export_pivot = convert_df_to_excel(pivot_gap)
    st.download_button("📊 Export GAP Pivot to Excel", export_pivot, "gap_analysis_pivot.xlsx")


def convert_df_to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="GAP Analysis")
    return output.getvalue()

def sort_period_columns(df, period_type):
    # Phần non-period columns (product_pn, pt_code, hoặc Metric)
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
                return (9999, 99)  # đẩy lỗi xuống cuối

        sorted_periods = sorted(period_cols, key=safe_parse_week)

    elif period_type == "Monthly":
        sorted_periods = sorted(
            period_cols,
            key=lambda x: pd.to_datetime("01 " + x, format="%d %b %Y", errors="coerce") or pd.Timestamp.max
        )
    else:  # Daily
        sorted_periods = sorted(period_cols)

    return df[cols + sorted_periods]
