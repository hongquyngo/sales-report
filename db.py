# data/db.py

import pandas as pd
from sqlalchemy import create_engine
from urllib.parse import quote_plus
import logging

from config import DB_CONFIG

# Cấu hình logger cho module này
logger = logging.getLogger(__name__)


# Hàm tạo engine kết nối đến cơ sở dữ liệu bằng SQLAlchemy
def get_db_engine():
    logger.info("🔌 Connecting to database...")

    user = DB_CONFIG["user"]
    password = quote_plus(str(DB_CONFIG["password"]))
    # password = quote_plus(DB_CONFIG["password"])  # Encode password để tránh lỗi ký tự đặc biệt
    host = DB_CONFIG["host"]
    port = DB_CONFIG["port"]
    database = DB_CONFIG["database"]

    # Tạo URL kết nối dạng chuẩn cho MySQL + PyMySQL
    url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"

    # In ra log dạng che password để debug nếu cần
    logger.info(f"🔐 Using SQLAlchemy URL: mysql+pymysql://{user}:***@{host}:{port}/{database}")

    return create_engine(url)


# Hàm chính để xử lý logic export theo từng loại dữ liệu
def get_data_by_type(data_type: str, engine) -> pd.DataFrame:
    """
    Trả về dataframe đã xử lý tương ứng với loại dữ liệu được chọn
    """
    try:
        if data_type == "Sales by Salesperson":
            query = "SELECT * FROM prostechvn.sales_report_flat_view;"
            df = pd.read_sql(query, engine)

        elif data_type ==  "Sales by KPI Center":
            query = "SELECT * FROM prostechvn.sales_report_by_kpi_center_flat_view;"
            df = pd.read_sql(query, engine)

        elif data_type == "Backlog":
            query = "SELECT * FROM prostechvn.backlog_full_view;"
            df = pd.read_sql(query, engine)

        elif data_type == "Broker Commission":
            query = "SELECT * FROM prostechvn.broker_commission_earning_view;"
            df = pd.read_sql(query, engine)

        else:
            logger.warning(f"❌ Unknown data type: {data_type}")
            return None

        return df

    except Exception as e:
        logger.exception(f"❌ Failed to load data for type: {data_type}")
        return None
