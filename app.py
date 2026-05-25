import streamlit as st

st.set_page_config(
    page_title="RRB Pharmacy",
    page_icon="💊",
    layout="wide"
)

st.title("💊 RRB Pharmacy System")

st.success("System Running Successfully")

col1, col2, col3 = st.columns(3)

col1.metric("Products", 120)
col2.metric("Sales", "SDG 250,000")
col3.metric("Low Stock", 5)

st.subheader("Inventory")

data = {
    "Product": ["Panadol", "Amoxil", "Vitamin C"],
    "Stock": [50, 10, 100],
    "Price": [300, 700, 450]
}

st.table(data)
