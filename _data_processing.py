# data_processing.py

"""
Module: data_processing
Purpose: Handle all data calculations, aggregations, and preparation for visualizations.
"""

import pandas as pd
from constants import MONTH_ORDER

def calculate_overview_metrics(inv_df, inv_by_kpi_center_df, backlog_df, backlog_by_kpi_center_df, exclude_internal=True):
    """
    Calculate main KPIs for the Overview section.

    Returns:
        dict: Dictionary of calculated KPIs.
    """
    # Total revenue and GP (YTD)
    total_revenue = inv_df['calculated_invoiced_amount_usd'].sum()
    total_gp = inv_df['invoiced_gross_profit_usd'].sum()

    # Counts
    total_customers = inv_df['customer_id'].nunique()
    total_invoices = inv_df['si_id'].nunique()
    total_sales_orders_invoiced = inv_df['oc_number'].nunique()

    # Outstanding (partial OC only)
    outstanding_revenue = backlog_df['outstanding_amount_usd'].sum()
    outstanding_gp = backlog_df['outstanding_gross_profit_usd'].sum()

    # Adjust for INTERNAL if needed
    if exclude_internal:
        internal_revenue = inv_by_kpi_center_df[inv_by_kpi_center_df["kpi_type"] == "INTERNAL"]["sales_by_kpi_center_usd"].sum()
        display_revenue = max(total_revenue - internal_revenue, 0)

        internal_outstanding = backlog_by_kpi_center_df[backlog_by_kpi_center_df["kpi_type"] == "INTERNAL"]["backlog_by_kpi_center_usd"].sum()
        display_outstanding = max(outstanding_revenue - internal_outstanding, 0)
    else:
        display_revenue = total_revenue
        display_outstanding = outstanding_revenue

    # GP % calculations
    gp_percent = round((total_gp / display_revenue) * 100, 2) if display_revenue else 0
    outstanding_gp_percent = round((outstanding_gp / display_outstanding) * 100, 2) if display_outstanding else 0

    # Return as dictionary
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

def prepare_monthly_summary(inv_df, inv_by_kpi_center_df, exclude_internal):
    """
    Prepare the monthly summary DataFrame for building revenue, gross profit, and GP% charts.

    Args:
        inv_df (DataFrame): Invoice-level data.
        inv_by_kpi_center_df (DataFrame): Invoice data grouped by KPI center.
        exclude_internal (bool): Whether to exclude INTERNAL revenue.

    Returns:
        DataFrame: Monthly summary with adjusted revenue, gross profit, GP%, cumulative revenue, and cumulative GP.
    """
    # Extract month names (Jan, Feb, ...) from invoice date
    inv_df["invoice_month"] = pd.to_datetime(inv_df["inv_date"]).dt.strftime("%b")

    # Group by month: sum revenue and gross profit
    monthly_summary = inv_df.groupby("invoice_month").agg({
        "calculated_invoiced_amount_usd": "sum",
        "invoiced_gross_profit_usd": "sum"
    }).reindex(MONTH_ORDER).fillna(0).reset_index()

    # Get INTERNAL revenue monthly if needed
    if exclude_internal:
        internal_monthly = inv_by_kpi_center_df[
            inv_by_kpi_center_df["kpi_type"] == "INTERNAL"
        ].groupby("invoice_month").agg({
            "sales_by_kpi_center_usd": "sum"
        }).reindex(MONTH_ORDER).fillna(0).reset_index()

        # Adjust revenue by removing internal sales
        monthly_summary["adjusted_revenue_usd"] = (
            monthly_summary["calculated_invoiced_amount_usd"] - internal_monthly["sales_by_kpi_center_usd"]
        ).apply(lambda x: max(x, 0))
    else:
        monthly_summary["adjusted_revenue_usd"] = monthly_summary["calculated_invoiced_amount_usd"]

    # Calculate monthly gross profit %
    monthly_summary["gp_percent"] = monthly_summary.apply(
        lambda row: (row["invoiced_gross_profit_usd"] / row["adjusted_revenue_usd"] * 100)
        if row["adjusted_revenue_usd"] else 0,
        axis=1
    )

    # Calculate cumulative revenue and GP
    monthly_summary["cumulative_revenue"] = monthly_summary["adjusted_revenue_usd"].cumsum()
    monthly_summary["cumulative_gp"] = monthly_summary["invoiced_gross_profit_usd"].cumsum()

    return monthly_summary


def prepare_territory_summary(inv_df, inv_by_kpi_center_df, total_revenue, exclude_internal=True):
    """
    Prepare summary data for Territory charts (Revenue, Gross Profit, GP%).

    Args:
        inv_df (DataFrame): Raw invoice data.
        inv_by_kpi_center_df (DataFrame): Invoice data grouped by KPI center.
        total_revenue (float): Total revenue for YTD.
        exclude_internal (bool): Whether to exclude INTERNAL.

    Returns:
        DataFrame: Combined summary with Center, Revenue, GrossProfit, Percent, GP_Percent.
    """
    # Filter out INTERNAL if needed
    territory_df = inv_by_kpi_center_df[
        (inv_by_kpi_center_df["kpi_type"] == "TERRITORY")
        & (~inv_by_kpi_center_df["kpi_center"].str.contains("INTERNAL") if exclude_internal else True)
    ]

    # Revenue
    territory_sum = territory_df["sales_by_kpi_center_usd"].sum()
    unmapped_revenue = max(total_revenue - territory_sum, 0)

    territory_grouped = territory_df.groupby("kpi_center")["sales_by_kpi_center_usd"].sum()
    territory_combined = pd.concat([
        territory_grouped, pd.Series({"Unmapped": unmapped_revenue})
    ]).reset_index()
    territory_combined.columns = ["Center", "Revenue"]
    territory_combined["Percent"] = (territory_combined["Revenue"] / territory_combined["Revenue"].sum()) * 100

    # Gross Profit
    territory_gp_df = inv_by_kpi_center_df[
        (inv_by_kpi_center_df["kpi_type"] == "TERRITORY")
        & (~inv_by_kpi_center_df["kpi_center"].str.contains("INTERNAL") if exclude_internal else True)
    ]
    territory_gp_sum = territory_gp_df["gross_profit_by_kpi_center_usd"].sum()
    total_gp_invoice = inv_df["invoiced_gross_profit_usd"].sum()
    unmapped_gp = max(total_gp_invoice - territory_gp_sum, 0)

    territory_gp_grouped = territory_gp_df.groupby("kpi_center")["gross_profit_by_kpi_center_usd"].sum()
    territory_gp_combined = pd.concat([
        territory_gp_grouped, pd.Series({"Unmapped": unmapped_gp})
    ]).reset_index()
    territory_gp_combined.columns = ["Center", "GrossProfit"]
    territory_gp_combined["Percent"] = (territory_gp_combined["GrossProfit"] / territory_gp_combined["GrossProfit"].sum()) * 100

    # Combine both
    summary_df = pd.merge(territory_combined, territory_gp_combined, on="Center", how="outer").fillna(0)
    summary_df["GP_Percent"] = summary_df.apply(
        lambda row: (row["GrossProfit"] / row["Revenue"] * 100) if row["Revenue"] else 0,
        axis=1
    )

    return summary_df



def prepare_vertical_summary(inv_df, inv_by_kpi_center_df, exclude_internal=True):
    """
    Prepare summarized data for VERTICAL KPIs.

    Args:
        inv_df (DataFrame): Invoice data.
        inv_by_kpi_center_df (DataFrame): KPI center data.
        exclude_internal (bool): Whether to exclude INTERNAL.

    Returns:
        DataFrame: Combined vertical summary.
    """
    vertical_df = inv_by_kpi_center_df[inv_by_kpi_center_df["kpi_type"] == "VERTICAL"]

    # Filter if needed
    if exclude_internal:
        vertical_df = vertical_df[vertical_df["kpi_center"] != "INTERNAL"]

    total_revenue = inv_df["calculated_invoiced_amount_usd"].sum()
    total_gp_invoice = inv_df["invoiced_gross_profit_usd"].sum()

    vertical_revenue_sum = vertical_df["sales_by_kpi_center_usd"].sum()
    vertical_gp_sum = vertical_df["gross_profit_by_kpi_center_usd"].sum()

    unmapped_revenue = max(total_revenue - vertical_revenue_sum, 0)
    unmapped_gp = max(total_gp_invoice - vertical_gp_sum, 0)

    vertical_grouped = vertical_df.groupby("kpi_center").agg({
        "sales_by_kpi_center_usd": "sum",
        "gross_profit_by_kpi_center_usd": "sum"
    }).reset_index()

    vertical_combined = pd.concat([
        vertical_grouped,
        pd.DataFrame([{
            "kpi_center": "Unmapped",
            "sales_by_kpi_center_usd": unmapped_revenue,
            "gross_profit_by_kpi_center_usd": unmapped_gp
        }])
    ])

    vertical_combined.rename(columns={
        "kpi_center": "Center",
        "sales_by_kpi_center_usd": "Revenue",
        "gross_profit_by_kpi_center_usd": "GrossProfit"
    }, inplace=True)

    vertical_combined["Percent_x"] = (vertical_combined["Revenue"] / vertical_combined["Revenue"].sum()) * 100
    vertical_combined["Percent_y"] = (vertical_combined["GrossProfit"] / vertical_combined["GrossProfit"].sum()) * 100
    vertical_combined["GP_Percent"] = vertical_combined.apply(
        lambda row: (row["GrossProfit"] / row["Revenue"] * 100) if row["Revenue"] else 0,
        axis=1
    )

    return vertical_combined
