import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from streamlit_option_menu import option_menu

# =========================
# إعداد الصفحة
# =========================

st.set_page_config(
    page_title="RRB Pharmacy System",
    page_icon="💊",
    layout="wide"
)

# =========================
# قاعدة البيانات
# =========================

engine = create_engine('sqlite:///pharmacy.db')

# =========================
# بيانات تجريبية
# =========================

sample_products = pd.DataFrame({
    "name": ["Panadol", "Amoxil", "Vitamin C", "Flagyl"],
    "barcode": [1111, 2222, 3333, 4444],
    "quantity": [50, 10, 100, 12],
    "purchase_price": [200, 500, 300, 400],
    "selling_price": [300, 700, 450, 600],
    "expiry_date": [
        datetime.now() + timedelta(days=200),
        datetime.now() + timedelta(days=20),
        datetime.now() + timedelta(days=100),
        datetime.now() + timedelta(days=5)
    ]
})

# =========================
# حفظ البيانات
# =========================

sample_products.to_sql(
    'products',
    engine,
    if_exists='replace',
    index=False
)

# =========================
# قراءة البيانات
# =========================

products = pd.read_sql('products', engine)

# =========================
# القائمة الجانبية
# =========================

with st.sidebar:
    selected = option_menu(
        "RRB Pharma Suite",
        [
            "Dashboard",
            "POS",
            "Inventory",
            "Alerts",
            "Reports"
        ],
        icons=[
            "speedometer2",
            "cart",
            "boxes",
            "bell",
            "bar-chart"
        ],
        menu_icon="capsule",
        default_index=0,
    )

# =========================
# Dashboard
# =========================

if selected == "Dashboard":

    st.title("💊 RRB Pharmacy Dashboard")

    total_products = len(products)
    low_stock = len(products[products['quantity'] <= 15])

    today_sales = 250000
    monthly_profit = 1200000

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Products", total_products)
    col2.metric("Low Stock", low_stock)
    col3.metric("Today Sales", f"SDG {today_sales}")
    col4.metric("Monthly Profit", f"SDG {monthly_profit}")

    st.divider()

    st.subheader("Sales Analytics")

    sales_data = pd.DataFrame({
        "Month": [
            "Jan", "Feb", "Mar",
            "Apr", "May", "Jun"
        ],
        "Sales": [
            10000,
            20000,
            15000,
            25000,
            30000,
            45000
        ]
    })

    fig = px.bar(
        sales_data,
        x='Month',
        y='Sales',
        title='Monthly Sales'
    )

    st.plotly_chart(fig, use_container_width=True)

# =========================
# POS
# =========================

elif selected == "POS":

    st.title("🛒 Point Of Sale")

    product_names = products['name'].tolist()

    selected_product = st.selectbox(
        "Select Product",
        product_names
    )

    qty = st.number_input(
        "Quantity",
        min_value=1,
        value=1
    )

    product_row = products[
        products['name'] == selected_product
    ].iloc[0]

    total = qty * product_row['selling_price']

    st.write(f"Price: SDG {product_row['selling_price']}")
    st.write(f"Total: SDG {total}")

    if st.button("Complete Sale"):

        new_qty = product_row['quantity'] - qty

        products.loc[
            products['name'] == selected_product,
            'quantity'
        ] = new_qty

        products.to_sql(
            'products',
            engine,
            if_exists='replace',
            index=False
        )

        st.success("Sale Completed Successfully")

# =========================
# Inventory
# =========================

elif selected == "Inventory":

    st.title("📦 Inventory Management")

    st.dataframe(
        products,
        use_container_width=True
    )

    st.subheader("Add Product")

    with st.form("add_product"):

        name = st.text_input("Product Name")
        barcode = st.text_input("Barcode")
        quantity = st.number_input("Quantity", min_value=0)
        purchase_price = st.number_input("Purchase Price")
        selling_price = st.number_input("Selling Price")
        expiry = st.date_input("Expiry Date")

        submit = st.form_submit_button("Add")

        if submit:

            new_product = pd.DataFrame({
                "name": [name],
                "barcode": [barcode],
                "quantity": [quantity],
                "purchase_price": [purchase_price],
                "selling_price": [selling_price],
                "expiry_date": [expiry]
            })

            updated = pd.concat([
                products,
                new_product
            ])

            updated.to_sql(
                'products',
                engine,
                if_exists='replace',
                index=False
            )

            st.success("Product Added Successfully")

# =========================
# Alerts
# =========================

elif selected == "Alerts":

    st.title("🚨 Alerts Center")

    st.subheader("Low Stock Products")

    low_stock_products = products[
        products['quantity'] <= 15
    ]

    st.dataframe(low_stock_products)

    st.subheader("Expiry Alerts")

    products['expiry_date'] = pd.to_datetime(
        products['expiry_date']
    )

    expiry_alerts = products[
        products['expiry_date'] <= datetime.now() + timedelta(days=30)
    ]

    st.dataframe(expiry_alerts)

# =========================
# Reports
# =========================

elif selected == "Reports":

    st.title("📊 Reports & Analytics")

    fig1 = px.pie(
        products,
        names='name',
        values='quantity',
        title='Stock Distribution'
    )

    st.plotly_chart(fig1, use_container_width=True)

    fig2 = px.bar(
        products,
        x='name',
        y='selling_price',
        title='Selling Prices'
    )

    st.plotly_chart(fig2, use_container_width=True)
