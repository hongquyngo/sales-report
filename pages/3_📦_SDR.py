import streamlit as st
import pandas as pd
from data_loader import load_outbound_demand_data
from sdr_tabs.demand_tab import show_outbound_demand_tab
from sdr_tabs.supply_capability_tab import show_inbound_supply_tab


st.set_page_config(page_title="Supply-Demand Reconciliation", layout="wide")

st.title("📦 Supply-Demand Reconciliation (SDR)")
# st.markdown("""
# **Overview & Reconciliation of Supply and Demand:**
# - Compare outbound demand with inbound supply  
# - Identify inventory gaps by period  
# - Recommend allocation plans or new PO to resolve shortages 
# """)

with st.expander("⚙️ Global Advanced Options", expanded=False):
    if st.button("🔄 Clear Cached Data", key="clear_cache_global"):
        st.cache_data.clear()
        st.success("✅ Cache cleared. Please reload the page.")
        st.stop()

# === Tabs ===
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📤 Outbound Demand", 
    "📥 Supply Capability", 
    "📊 GAP Analysis", 
    "🧩 Allocation Plan", 
    "📌 PO/Reallocation Suggestions"
])

with tab1:
    show_outbound_demand_tab()

with tab2:
    show_inbound_supply_tab()

with tab3:
    st.subheader("📊 Inventory GAP Analysis")
    # st.dataframe(gap_df)

with tab4:
    st.subheader("🧩 Inventory Allocation Plan")
    # st.dataframe(allocation_df)

with tab5:
    st.subheader("📌 Suggested PO or Reallocation")
    # st.dataframe(suggestion_df)
