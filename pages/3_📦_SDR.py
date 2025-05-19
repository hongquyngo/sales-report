import streamlit as st
import pandas as pd
from data_loader import load_outbound_demand_data
from sdr_tabs.outbound_tab import show_outbound_demand_tab

st.title("📦 Supply-Demand Reconciliation (SDR)")
st.markdown("""
**Overview & Reconciliation of Supply and Demand:**
- Compare outbound demand with inbound supply  
- Identify inventory gaps by period  
- Recommend allocation plans or new PO to resolve shortages 
""")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📤 Outbound Demand", 
    "📥 Inbound Supply", 
    "📊 GAP Analysis", 
    "🧩 Allocation Plan", 
    "📌 PO/Reallocation Suggestions"
])

with tab1:
   show_outbound_demand_tab()
with tab2:
    st.subheader("📥 Inbound Supply by Period")
    # st.dataframe(inbound_df)

with tab3:
    st.subheader("📊 Inventory GAP Analysis")
    # st.dataframe(gap_df)

with tab4:
    st.subheader("🧩 Inventory Allocation Plan")
    # st.dataframe(allocation_df)

with tab5:
    st.subheader("📌 Suggested PO or Reallocation")
    # st.dataframe(suggestion_df)
