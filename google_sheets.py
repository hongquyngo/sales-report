# google_sheets.py

import datetime
import logging
import pytz
import pandas as pd
import json
import os
import streamlit as st

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from config import GOOGLE_SERVICE_ACCOUNT_JSON  # lấy từ config.py

# ======================
# CONFIG
# ======================

SPREADSHEET_ID = "11XRu4EeH__vjvOVL5LTIiJ4I5Aawco0icLKdUkOtsOc"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def export_to_google_sheets(data: pd.DataFrame, data_type: str) -> str:
    logger.info("📄 Exporting to Google Sheets...")

    # Xác thực Google Sheets API (tự động chọn credentials phù hợp)
    credentials = service_account.Credentials.from_service_account_info(
    GOOGLE_SERVICE_ACCOUNT_JSON,
    scopes=SCOPES)
    service = build("sheets", "v4", credentials=credentials)
    sheets_api = service.spreadsheets()

    # Tạo tên sheet mới
    # vn_tz = pytz.timezone("Asia/Ho_Chi_Minh")
    # now = datetime.datetime.now(vn_tz).strftime("%Y-%m-%d_%H%M")
    prefix = data_type.lower().replace(" ", "_")
    # new_sheet_title = f"{prefix}_{now}"
    new_sheet_title = f"{prefix}"

    try:
        # Kiểm tra sheet đã tồn tại chưa
        metadata = sheets_api.get(spreadsheetId=SPREADSHEET_ID).execute()
        sheets = metadata.get("sheets", [])
        target_sheet_id = None

        for s in sheets:
            title = s["properties"]["title"]
            if title.startswith(prefix):
                target_sheet_id = s["properties"]["sheetId"]
                break

        if target_sheet_id:
            logger.info(f"♻️ Updating existing sheet to: {new_sheet_title}")
            requests = [
                {
                    "updateSheetProperties": {
                        "properties": {
                            "sheetId": target_sheet_id,
                            "title": new_sheet_title
                        },
                        "fields": "title"
                    }
                },
                {
                    "updateCells": {
                        "range": {"sheetId": target_sheet_id},
                        "fields": "userEnteredValue"
                    }
                }
            ]
            sheets_api.batchUpdate(spreadsheetId=SPREADSHEET_ID, body={"requests": requests}).execute()
        else:
            logger.info(f"📄 Creating new sheet: {new_sheet_title}")
            sheets_api.batchUpdate(
                spreadsheetId=SPREADSHEET_ID,
                body={"requests": [{"addSheet": {"properties": {"title": new_sheet_title}}}]}
            ).execute()

        # Ghi header
        headers = [list(data.columns)]
        sheets_api.values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{new_sheet_title}!A1",
            valueInputOption="RAW",
            body={"values": headers}
        ).execute()

        # Ghi dữ liệu chính
        values = data.astype(str).values.tolist()
        sheets_api.values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{new_sheet_title}!A2",
            valueInputOption="USER_ENTERED",
            body={"values": values}
        ).execute()

        # Format sheet sau khi ghi
        format_sheet(service, SPREADSHEET_ID, new_sheet_title, data)

        logger.info("✅ Export completed successfully.")
        return new_sheet_title

    except Exception as e:
        logger.exception("❌ Export failed:")
        raise


def format_sheet(service, sheet_id, sheet_name, df):
    sheets_api = service.spreadsheets()
    sheet_id_num = get_sheet_id_by_name(service, sheet_id, sheet_name)
    col_index = {col: idx for idx, col in enumerate(df.columns)}
    requests = []

    requests.append({
        "updateSheetProperties": {
            "properties": {
                "sheetId": sheet_id_num,
                "gridProperties": {"frozenRowCount": 1}
            },
            "fields": "gridProperties.frozenRowCount"
        }
    })

    requests.append({
        "repeatCell": {
            "range": {
                "sheetId": sheet_id_num,
                "startRowIndex": 0,
                "endRowIndex": 1
            },
            "cell": {
                "userEnteredFormat": {
                    "textFormat": {"bold": True}
                }
            },
            "fields": "userEnteredFormat.textFormat.bold"
        }
    })

    if 'VAT Invoice Number' in col_index:
        col_idx = col_index['VAT Invoice Number']
        requests.append({
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id_num,
                    "startRowIndex": 1,
                    "startColumnIndex": col_idx,
                    "endColumnIndex": col_idx + 1
                },
                "cell": {
                    "userEnteredFormat": {
                        "numberFormat": {"type": "TEXT"}
                    }
                },
                "fields": "userEnteredFormat.numberFormat"
            }
        })

    if requests:
        try:
            sheets_api.batchUpdate(
                spreadsheetId=sheet_id,
                body={"requests": requests}
            ).execute()
            logger.info("🎨 Sheet formatting applied.")
        except HttpError as e:
            logger.error(f"❌ Formatting failed: {e}")


def get_sheet_id_by_name(service, spreadsheet_id, sheet_name):
    metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    for sheet in metadata.get("sheets", []):
        if sheet["properties"]["title"] == sheet_name:
            return sheet["properties"]["sheetId"]
    raise Exception(f"Sheet name '{sheet_name}' not found.")
