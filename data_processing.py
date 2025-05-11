"""
Module: data_processing
Purpose: Handle all data calculations, aggregations, and preparation for visualizations.
"""

import pandas as pd
from constants import MONTH_ORDER


def prepare_salesperson_top_customers_by_gp(sales_df: pd.DataFrame, top_percent=0.8) -> pd.DataFrame:
    """
    Prepare top customers contributing to the specified % of total gross profit
    for a specific salesperson. Ensures inclusion of the customer that causes
    cumulative % to exceed the threshold.

    Args:
        sales_df (DataFrame): Filtered sales data for a specific salesperson.
        top_percent (float): Cumulative cutoff (e.g., 0.8 for top 80%).

    Returns:
        DataFrame: Top customers with gross profit, cumulative %, and GP %.
    """
    df = sales_df.groupby("customer").agg({
        "gross_profit_by_split_usd": "sum"
    }).reset_index()

    df = df.sort_values(by="gross_profit_by_split_usd", ascending=False)
    df["cumulative_gp"] = df["gross_profit_by_split_usd"].cumsum()
    total_gp = df["gross_profit_by_split_usd"].sum()
    df["cumulative_percent"] = df["cumulative_gp"] / total_gp

    # Tìm index đầu tiên mà cumulative_percent > top_percent
    first_exceed_index = df[df["cumulative_percent"] > top_percent].first_valid_index()

    if first_exceed_index is None:
        top_df = df.copy()
    else:
        top_df = df.loc[:first_exceed_index].copy()

    # Rename + Add GP %
    top_df.rename(columns={
        "customer": "Customer",
        "gross_profit_by_split_usd": "GrossProfit"
    }, inplace=True)
    top_df["GP_Percent"] = top_df["GrossProfit"] / total_gp * 100

    return top_df


def prepare_salesperson_cumulative_data(monthly_df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare cumulative revenue & gross profit data for a salesperson.
    """
    df = monthly_df.copy()
    df['Cumulative Revenue'] = df['sales_by_split_usd'].cumsum()
    df['Cumulative Gross Profit'] = df['gross_profit_by_split_usd'].cumsum()
    return df


def prepare_salesperson_monthly_summary_data(sales_df: pd.DataFrame):
    """
    Prepare monthly summary for a salesperson, including Revenue, GP, GP% and Customer Count.

    Args:
        sales_df (DataFrame): Filtered sales data of a salesperson.

    Returns:
        DataFrame with columns: invoice_month, sales_by_split_usd, gross_profit_by_split_usd, gp_percent, customer_count
    """
    # Group by invoice_month
    monthly_summary = sales_df.groupby('invoice_month').agg({
        'sales_by_split_usd': 'sum',
        'gross_profit_by_split_usd': 'sum',
        'customer': pd.Series.nunique
    }).reset_index()

    # Calculate GP %
    monthly_summary['gp_percent'] = monthly_summary.apply(
        lambda row: (row['gross_profit_by_split_usd'] / row['sales_by_split_usd'] * 100) if row['sales_by_split_usd'] else 0,
        axis=1
    )

    # Rename for clarity
    monthly_summary.rename(columns={'customer': 'customer_count'}, inplace=True)

    # Ensure all months are present
    all_months = pd.DataFrame({'invoice_month': MONTH_ORDER})
    monthly_summary = all_months.merge(monthly_summary, on='invoice_month', how='left').fillna(0)

    return monthly_summary


def calculate_salesperson_overview_metrics(sales_df, backlog_df, kpi_df, selected_sales):
    """
    Calculate YTD KPIs and KPI performance for a single salesperson.

    Args:
        sales_df (DataFrame): Sales performance data (filtered for the salesperson).
        backlog_df (DataFrame): Backlog data (filtered for the salesperson).
        kpi_df (DataFrame): KPI assignment data.
        selected_sales (str): Salesperson name.

    Returns:
        dict: Metrics including total performance and % KPI achieved.
    """
    # === YTD Metrics ===
    total_customers = sales_df['customer'].nunique()
    total_invoices = sales_df['inv_number'].nunique()
    total_sales_orders_invoiced = sales_df['oc_number'].nunique()

    total_revenue = sales_df['sales_by_split_usd'].sum()
    total_gp = sales_df['gross_profit_by_split_usd'].sum()

    gp_percent = (total_gp / total_revenue * 100) if total_revenue else 0

    outstanding_revenue = backlog_df['backlog_sales_by_split_usd'].sum()
    outstanding_gp = backlog_df['backlog_gp_by_split_usd'].sum()

    outstanding_gp_percent = (outstanding_gp / outstanding_revenue * 100) if outstanding_revenue else 0

    # === Get KPI Assignments ===
    kpi_revenue = None
    kpi_gp = None

    sales_kpi_row = kpi_df[kpi_df['employee_name'] == selected_sales]

    if not sales_kpi_row.empty:
        # KPI Revenue
        kpi_revenue_row = sales_kpi_row[sales_kpi_row['kpi_name'].str.lower() == 'revenue']
        if not kpi_revenue_row.empty:
            kpi_revenue = float(kpi_revenue_row['annual_target_value'].str.replace(',', '').iloc[0])

        # KPI GP
        kpi_gp_row = sales_kpi_row[sales_kpi_row['kpi_name'].str.lower() == 'gross_profit']
        if not kpi_gp_row.empty:
            kpi_gp = float(kpi_gp_row['annual_target_value'].str.replace(',', '').iloc[0])

    # === Calculate % KPI Achieved ===
    percent_revenue_kpi = (total_revenue / kpi_revenue * 100) if kpi_revenue else None
    percent_gp_kpi = (total_gp / kpi_gp * 100) if kpi_gp else None

    return {
        'total_customers': total_customers,
        'total_invoices': total_invoices,
        'total_sales_orders_invoiced': total_sales_orders_invoiced,
        'display_revenue': total_revenue,
        'total_gp': total_gp,
        'gp_percent': round(gp_percent, 2),
        'display_outstanding': outstanding_revenue,
        'outstanding_gp': outstanding_gp,
        'outstanding_gp_percent': round(outstanding_gp_percent, 2),
        'percent_revenue_kpi': round(percent_revenue_kpi, 1) if percent_revenue_kpi is not None else None,
        'percent_gp_kpi': round(percent_gp_kpi, 1) if percent_gp_kpi is not None else None
    }


###############

def calculate_overview_metrics(inv_df, inv_by_kpi_center_df, backlog_df, backlog_by_kpi_center_df, exclude_internal=True):
    """
    Calculate main KPIs for the Overview section.
    Returns:
        dict: Dictionary of calculated KPIs.
    """
    total_revenue = inv_df['calculated_invoiced_amount_usd'].sum()
    total_gp = inv_df['invoiced_gross_profit_usd'].sum()

    total_customers = inv_df['customer_id'].nunique()
    total_invoices = inv_df['si_id'].nunique()
    total_sales_orders_invoiced = inv_df['oc_number'].nunique()

    outstanding_revenue = backlog_df['outstanding_amount_usd'].sum()
    outstanding_gp = backlog_df['outstanding_gross_profit_usd'].sum()

    if exclude_internal:
        internal_revenue = inv_by_kpi_center_df[inv_by_kpi_center_df["kpi_type"] == "INTERNAL"]["sales_by_kpi_center_usd"].sum()
        display_revenue = max(total_revenue - internal_revenue, 0)

        internal_outstanding = backlog_by_kpi_center_df[backlog_by_kpi_center_df["kpi_type"] == "INTERNAL"]["backlog_by_kpi_center_usd"].sum()
        display_outstanding = max(outstanding_revenue - internal_outstanding, 0)
    else:
        display_revenue = total_revenue
        display_outstanding = outstanding_revenue

    gp_percent = round((total_gp / display_revenue) * 100, 2) if display_revenue else 0
    outstanding_gp_percent = round((outstanding_gp / display_outstanding) * 100, 2) if display_outstanding else 0

    return {
        'total_revenue': total_revenue,
        'total_gp': total_gp,
        'total_customers': total_customers,
        'total_invoices': total_invoices,
        'total_sales_orders_invoiced': total_sales_orders_invoiced,
        'outstanding_revenue': outstanding_revenue,
        'outstanding_gp': outstanding_gp,
        'display_revenue': display_revenue,
        'display_outstanding': display_outstanding,
        'gp_percent': gp_percent,
        'outstanding_gp_percent': outstanding_gp_percent,
    }


def prepare_monthly_summary_data(inv_df, inv_by_kpi_center_df, exclude_internal=True):
    """
    Prepare monthly summary for Revenue, Gross Profit, GP%, Customer Count, and cumulative metrics.

    Args:
        inv_df (DataFrame): Invoice-level data.
        inv_by_kpi_center_df (DataFrame): KPI center-level summary.
        exclude_internal (bool): Whether to exclude INTERNAL sales.

    Returns:
        DataFrame: Monthly summary with calculated fields.
    """
    # Extract invoice month
    inv_df["invoice_month"] = pd.to_datetime(inv_df["inv_date"]).dt.strftime("%b")

    # Group by invoice month
    monthly_summary = inv_df.groupby("invoice_month").agg({
        "calculated_invoiced_amount_usd": "sum",
        "invoiced_gross_profit_usd": "sum",
        "customer": pd.Series.nunique  # customer count
    }).reindex(MONTH_ORDER).fillna(0).reset_index()

    # Rename for clarity
    monthly_summary.rename(columns={"customer": "customer_count"}, inplace=True)

    # Handle exclude_internal logic
    if exclude_internal:
        internal_monthly = inv_by_kpi_center_df[
            inv_by_kpi_center_df["kpi_type"] == "INTERNAL"
        ].groupby("invoice_month").agg({
            "sales_by_kpi_center_usd": "sum"
        }).reindex(MONTH_ORDER).fillna(0).reset_index()

        monthly_summary["adjusted_revenue_usd"] = (
            monthly_summary["calculated_invoiced_amount_usd"] - internal_monthly["sales_by_kpi_center_usd"]
        ).apply(lambda x: max(x, 0))
    else:
        monthly_summary["adjusted_revenue_usd"] = monthly_summary["calculated_invoiced_amount_usd"]

    # GP %
    monthly_summary["gp_percent"] = monthly_summary.apply(
        lambda row: (row["invoiced_gross_profit_usd"] / row["adjusted_revenue_usd"] * 100)
        if row["adjusted_revenue_usd"] else 0,
        axis=1
    )

    # Cumulative
    monthly_summary["cumulative_revenue"] = monthly_summary["adjusted_revenue_usd"].cumsum()
    monthly_summary["cumulative_gp"] = monthly_summary["invoiced_gross_profit_usd"].cumsum()

    return monthly_summary


def prepare_dimension_summary_data(inv_df, inv_by_kpi_center_df, dimension_type, exclude_internal=True):
    """
    Prepare summary for any KPI dimension (TERRITORY, VERTICAL).

    Args:
        inv_df (DataFrame): Invoice-level data.
        inv_by_kpi_center_df (DataFrame): KPI center-level summary.
        dimension_type (str): 'TERRITORY' or 'VERTICAL'.
        exclude_internal (bool): Whether to exclude INTERNAL revenue.

    Returns:
        DataFrame: Summary with Revenue, GrossProfit, Percentages, GP%.
    """
    # Calculate base totals (adjusting for internal if needed)
    total_revenue = inv_df["calculated_invoiced_amount_usd"].sum()
    total_gp = inv_df["invoiced_gross_profit_usd"].sum()

    if exclude_internal:
        internal_revenue = inv_by_kpi_center_df[
            inv_by_kpi_center_df["kpi_type"] == "INTERNAL"
        ]["sales_by_kpi_center_usd"].sum()
        total_revenue = max(total_revenue - internal_revenue, 0)

    # Filter dimension data (excluding INTERNAL rows if needed)
    dimension_df = inv_by_kpi_center_df[
        (inv_by_kpi_center_df["kpi_type"] == dimension_type)
        & (~inv_by_kpi_center_df["kpi_center"].str.contains("INTERNAL") if exclude_internal else True)
    ]

    # Group by center
    grouped = dimension_df.groupby("kpi_center").agg({
        "sales_by_kpi_center_usd": "sum",
        "gross_profit_by_kpi_center_usd": "sum"
    }).reset_index()

    # Calculate unmapped
    dimension_revenue_sum = grouped["sales_by_kpi_center_usd"].sum()
    dimension_gp_sum = grouped["gross_profit_by_kpi_center_usd"].sum()

    unmapped_revenue = max(total_revenue - dimension_revenue_sum, 0)
    unmapped_gp = max(total_gp - dimension_gp_sum, 0)

    # Append Unmapped row
    combined = pd.concat([
        grouped,
        pd.DataFrame([{
            "kpi_center": "Unmapped",
            "sales_by_kpi_center_usd": unmapped_revenue,
            "gross_profit_by_kpi_center_usd": unmapped_gp
        }])
    ], ignore_index=True)

    # Rename and calculate percentages
    combined.rename(columns={
        "kpi_center": "Center",
        "sales_by_kpi_center_usd": "Revenue",
        "gross_profit_by_kpi_center_usd": "GrossProfit"
    }, inplace=True)

    combined["Percent_Revenue"] = (combined["Revenue"] / combined["Revenue"].sum()) * 100
    combined["Percent_GP"] = (combined["GrossProfit"] / combined["GrossProfit"].sum()) * 100

    combined["GP_Percent"] = combined.apply(
        lambda row: (row["GrossProfit"] / row["Revenue"] * 100) if row["Revenue"] else 0,
        axis=1
    )

    return combined

def prepare_top_customers_by_gp(inv_df, top_percent=0.8):
    """
    Prepare top customers contributing to the specified % of total gross profit.
    Ensures inclusion of the first customer that causes cumulative % to exceed the threshold.

    Args:
        inv_df (DataFrame): Raw invoice data.
        top_percent (float): Cumulative cutoff (e.g., 0.8 for top 80%).

    Returns:
        DataFrame: Top customers with gross profit, cumulative %, and GP %.
    """
    # Group GP by customer
    customer_gp = inv_df.groupby("customer")["invoiced_gross_profit_usd"].sum().reset_index()
    customer_gp = customer_gp.sort_values(by="invoiced_gross_profit_usd", ascending=False)

    # Calculate cumulative %
    customer_gp["cumulative_gp"] = customer_gp["invoiced_gross_profit_usd"].cumsum()
    total_gp = customer_gp["invoiced_gross_profit_usd"].sum()
    customer_gp["cumulative_percent"] = customer_gp["cumulative_gp"] / total_gp

    # Tìm index đầu tiên mà cumulative_percent > top_percent
    first_exceed_index = customer_gp[customer_gp["cumulative_percent"] > top_percent].first_valid_index()

    if first_exceed_index is None:
        top_customers = customer_gp.copy()  # Trường hợp không có khách nào vượt ngưỡng
    else:
        top_customers = customer_gp.loc[:first_exceed_index].copy()

    # Đổi tên cột và tính thêm GP %
    top_customers.rename(columns={
        "customer": "Customer",
        "invoiced_gross_profit_usd": "GrossProfit"
    }, inplace=True)
    top_customers["GP_Percent"] = top_customers["GrossProfit"] / total_gp * 100

    return top_customers
