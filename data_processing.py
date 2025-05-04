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
    Prepare monthly summary (Revenue, Gross Profit, GP%, cumulative).
    """
    inv_df["invoice_month"] = pd.to_datetime(inv_df["inv_date"]).dt.strftime("%b")

    monthly_summary = inv_df.groupby("invoice_month").agg({
        "calculated_invoiced_amount_usd": "sum",
        "invoiced_gross_profit_usd": "sum"
    }).reindex(MONTH_ORDER).fillna(0).reset_index()

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

    monthly_summary["gp_percent"] = monthly_summary.apply(
        lambda row: (row["invoiced_gross_profit_usd"] / row["adjusted_revenue_usd"] * 100)
        if row["adjusted_revenue_usd"] else 0,
        axis=1
    )

    monthly_summary["cumulative_revenue"] = monthly_summary["adjusted_revenue_usd"].cumsum()
    monthly_summary["cumulative_gp"] = monthly_summary["invoiced_gross_profit_usd"].cumsum()

    return monthly_summary

def prepare_dimension_summary_data(inv_df, inv_by_kpi_center_df, dimension_type, exclude_internal=True):
    dimension_df = inv_by_kpi_center_df[
        (inv_by_kpi_center_df["kpi_type"] == dimension_type)
        & (~inv_by_kpi_center_df["kpi_center"].str.contains("INTERNAL") if exclude_internal else True)
    ]

    # Compute base revenue and GP (after exclude_internal)
    if exclude_internal:
        total_revenue = inv_df["calculated_invoiced_amount_usd"].sum() - \
            inv_by_kpi_center_df[inv_by_kpi_center_df["kpi_type"] == "INTERNAL"]["sales_by_kpi_center_usd"].sum()
    else:
        total_revenue = inv_df["calculated_invoiced_amount_usd"].sum()

    total_gp = inv_df["invoiced_gross_profit_usd"].sum()

    # Grouped Revenue & GP by center
    grouped = dimension_df.groupby("kpi_center").agg({
        "sales_by_kpi_center_usd": "sum",
        "gross_profit_by_kpi_center_usd": "sum"
    }).reset_index()

    revenue_sum = grouped["sales_by_kpi_center_usd"].sum()
    gp_sum = grouped["gross_profit_by_kpi_center_usd"].sum()

    unmapped_revenue = max(total_revenue - revenue_sum, 0)
    unmapped_gp = max(total_gp - gp_sum, 0)

    # Append Unmapped row
    combined = pd.concat([
        grouped,
        pd.DataFrame([{
            "kpi_center": "Unmapped",
            "sales_by_kpi_center_usd": unmapped_revenue,
            "gross_profit_by_kpi_center_usd": unmapped_gp
        }])
    ], ignore_index=True)

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
