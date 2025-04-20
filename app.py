# app.py

# Import thư viện cần thiết
import streamlit as st                      # Thư viện tạo giao diện web đơn giản
import pandas as pd                        # Xử lý bảng dữ liệu
import logging                             # Ghi log để debug hoặc theo dõi trạng thái

# Import các hàm xử lý từ các module con
from db import get_db_engine, get_data_by_type        # Hàm kết nối DB và lấy dữ liệu
from google_sheets import export_to_google_sheets     # Hàm export dữ liệu lên Google Sheets

# Thiết lập hệ thống log, ghi ở mức INFO (hiển thị các bước chính)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    # Cấu hình giao diện trang web
    st.set_page_config(page_title="POS Data Export", page_icon="📊")

    # Tiêu đề chính của ứng dụng
    st.title("📤 Export POS Data to Google Sheets")

    # Dropdown cho người dùng chọn loại dữ liệu muốn export
    data_type = st.selectbox("Select data type to export:", [
        "Sales by Salesperson",
        "Sales by KPI Center",       
        "Backlog",                  # Đơn hàng chưa giao
        "Broker Commission"
    ])

    # Cho phép người dùng điều chỉnh số dòng preview dữ liệu trước khi export
    preview_rows = st.slider("Preview rows:", 5, 100, 20)

    # Khi người dùng nhấn nút export
    if st.button("Export to Google Sheets"):
        try:
            # Bước 1: Tạo kết nối đến database
            engine = get_db_engine()

            # Bước 2: Gọi hàm tương ứng để truy vấn và xử lý dữ liệu theo data_type
            logger.info(f"📥 Loading data for: {data_type}")
            df = get_data_by_type(data_type, engine)

            # Bước 3: Kiểm tra nếu không có dữ liệu thì báo người dùng
            if df is None or df.empty:
                st.warning("⚠️ No data found.")
                return

            # Bước 4: Hiển thị bảng dữ liệu preview
            st.subheader("📄 Preview Data")
            st.dataframe(df.head(preview_rows))   # Hiển thị số dòng preview được chọn

            # Bước 5: Export lên Google Sheets
            sheet_name = export_to_google_sheets(df, data_type)

            # Bước 6: Thông báo thành công
            st.success(f"✅ Exported to Google Sheet: `{sheet_name}`")

        except Exception as e:
            # Nếu có lỗi xảy ra thì ghi log và báo lỗi ra giao diện
            logger.exception("❌ Export failed:")
            st.error(f"❌ Export failed: {e}")


# Gọi hàm chính khi chạy file này
if __name__ == "__main__":
    main()
