import pandas as pd
from sqlalchemy import text
from db import get_db_engine

def load_data():
    """
    Load all required datasets from the database.

    Returns:
        tuple: (inv_df, inv_by_kpi_center_df, backlog_df, backlog_by_kpi_center_df)
    """
    engine = get_db_engine()

    inv_query = """
        SELECT *
        FROM prostechvn.sales_invoice_full_looker_view
        WHERE DATE(inv_date) >= DATE_FORMAT(CURDATE(), '%Y-01-01')
          AND inv_date < DATE_ADD(DATE_FORMAT(CURDATE(), '%Y-%m-%d'), INTERVAL 1 DAY);
    """

    inv_by_kpi_center_query = """
        SELECT *
        FROM prostechvn.sales_report_by_kpi_center_flat_looker_view
        WHERE DATE(inv_date) >= DATE_FORMAT(CURDATE(), '%Y-01-01')
          AND inv_date < DATE_ADD(DATE_FORMAT(CURDATE(), '%Y-%m-%d'), INTERVAL 1 DAY);
    """

    backlog_query = """
        SELECT *
        FROM prostechvn.order_confirmation_full_looker_view
        WHERE IFNULL(total_invoiced_selling_quantity, 0) < selling_quantity;
    """

    backlog_by_kpi_center_query = """
        SELECT *
        FROM prostechvn.backlog_by_kpi_center_flat_looker_view
        WHERE IFNULL(total_invoiced_selling_quantity, 0) < selling_quantity;
    """

    inv_df = pd.read_sql(text(inv_query), engine)
    inv_by_kpi_center_df = pd.read_sql(text(inv_by_kpi_center_query), engine)
    backlog_df = pd.read_sql(text(backlog_query), engine)
    backlog_by_kpi_center_df = pd.read_sql(text(backlog_by_kpi_center_query), engine)

    return inv_df, inv_by_kpi_center_df, backlog_df, backlog_by_kpi_center_df
