# utils/handlers.py

import requests
import pandas as pd
from config import EXCHANGE_RATE_API_KEY

# ============================
# Hàm lấy tỉ giá ngoại tệ mới nhất từ API
# ============================
def get_latest_exchange_rate(_from: str, _to: str) -> float:
    """
    Lấy tỉ giá mới nhất từ một loại tiền sang loại khác (ví dụ: VND → USD)
    Dùng API từ exchangeratesapi.io (hoặc dịch vụ tương đương)
    
    Args:
        _from (str): mã tiền tệ gốc (ví dụ "VND")
        _to (str): mã tiền tệ đích (ví dụ "USD")

    Returns:
        float: tỉ giá (_from → _to)
    """
    url = (
        f"http://api.exchangeratesapi.io/v1/latest"
        f"?access_key={EXCHANGE_RATE_API_KEY}&base={_from}&symbols={_to}"
    )
    
    response = requests.get(url)
    response.raise_for_status()  # Nếu lỗi sẽ raise Exception

    rate = response.json()["rates"][_to]
    return float(rate)

def count_decimal_zeros(number: float) -> int:
    if number == 0:
        return 0

    zeros = 0
    while number < 1:
        number *= 10
        if int(number) == 0:
            zeros += 1
        else:
            break
    return zeros
