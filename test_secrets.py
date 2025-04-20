import streamlit as st
import json

st.title("🔐 Streamlit Secrets Debugger")

# Kiểm tra xem có secrets không
if st.secrets:
    st.success("✅ Secrets loaded from streamlit runtime.")
    st.subheader("📦 st.secrets keys:")
    st.json(list(st.secrets.keys()))

    # In chi tiết từng phần
    if "DB_CONFIG" in st.secrets:
        st.subheader("🧩 DB_CONFIG")
        st.json(dict(st.secrets["DB_CONFIG"]))

    if "API" in st.secrets:
        st.subheader("🔑 API Key")
        st.write(st.secrets["API"]["EXCHANGE_RATE_API_KEY"])

    if "GOOGLE" in st.secrets:
        st.subheader("🔐 Google Service JSON (short preview)")
        sa_json = st.secrets["GOOGLE"].get("GOOGLE_SERVICE_ACCOUNT_JSON", "Not found")
        try:
            parsed = json.loads(sa_json)
            st.code(parsed["client_email"])
        except Exception as e:
            st.error(f"❌ Lỗi khi parse JSON: {e}")
            st.text(sa_json[:300])  # hiển thị 300 ký tự đầu để debug
else:
    st.error("❌ Không tìm thấy bất kỳ secret nào trong st.secrets.")
