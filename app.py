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
# تهيئة الجداول (إن لم تكن موجودة)
# =========================
def init_db():
    with engine.connect() as conn:
        # جدول المنتجات
        conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            barcode TEXT,
            quantity INTEGER,
            purchase_price REAL,
            selling_price REAL,
            expiry_date TEXT
        )
        """)
        # جدول المستخدمين
        conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
        """)
        # جدول الفواتير
        conn.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_no TEXT,
            date TEXT,
            user TEXT,
            total REAL
        )
        """)
        # تفاصيل الفواتير
        conn.execute("""
        CREATE TABLE IF NOT EXISTS invoice_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER,
            product_name TEXT,
            quantity INTEGER,
            price REAL,
            total REAL
        )
        """)
        # جدول المشتريات
        conn.execute("""
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            supplier TEXT,
            product_name TEXT,
            quantity INTEGER,
            cost REAL,
            total REAL
        )
        """)
        # مستخدم افتراضي (مدير)
        users = pd.read_sql("SELECT * FROM users", conn)
        if users.empty:
            conn.execute("""
            INSERT INTO users (username, password, role)
            VALUES ('admin', 'admin123', 'admin')
            """)

init_db()

# =========================
# تحميل البيانات
# =========================
def load_products():
    try:
        return pd.read_sql("SELECT * FROM products", engine)
    except:
        df = pd.DataFrame({
            "name": ["Panadol", "Amoxil", "Vitamin C", "Flagyl"],
            "barcode": ["1111", "2222", "3333", "4444"],
            "quantity": [50, 10, 100, 12],
            "purchase_price": [200, 500, 300, 400],
            "selling_price": [300, 700, 450, 600],
            "expiry_date": [
                (datetime.now() + timedelta(days=200)).strftime("%Y-%m-%d"),
                (datetime.now() + timedelta(days=20)).strftime("%Y-%m-%d"),
                (datetime.now() + timedelta(days=100)).strftime("%Y-%m-%d"),
                (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
            ]
        })
        df.to_sql("products", engine, if_exists="replace", index=False)
        return df

def load_invoices():
    return pd.read_sql("SELECT * FROM invoices", engine)

def load_purchases():
    return pd.read_sql("SELECT * FROM purchases", engine)

products = load_products()

# =========================
# CSS بسيط لتحسين الواجهة
# =========================
st.markdown("""
    <style>
    .main-title {
        font-size: 32px;
        font-weight: 700;
        color: #2c3e50;
    }
    .sub-title {
        font-size: 20px;
        font-weight: 600;
        color: #34495e;
    }
    </style>
""", unsafe_allow_html=True)

# =========================
# إدارة الجلسة (Session State)
# =========================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = None
if "role" not in st.session_state:
    st.session_state.role = None

# =========================
# شاشة تسجيل الدخول
# =========================
def login_screen():
    st.title("🔐 RRB Pharmacy Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        users = pd.read_sql("SELECT * FROM users", engine)
        user_row = users[(users['username'] == username) & (users['password'] == password)]
        if not user_row.empty:
            user_row = user_row.iloc[0]
            st.session_state.logged_in = True
            st.session_state.username = user_row['username']
            st.session_state.role = user_row['role']
            st.success(f"Welcome, {user_row['username']} ({user_row['role']})")
            st.experimental_rerun()
        else:
            st.error("Invalid username or password")

# =========================
# Sidebar Menu
# =========================
def sidebar_menu():
    with st.sidebar:
        st.markdown(f"**User:** {st.session_state.username} ({st.session_state.role})")
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.role = None
            st.experimental_rerun()

        selected = option_menu(
            "RRB Pharma Suite",
            ["Dashboard", "POS", "Inventory", "Purchases", "Invoices", "Users", "Alerts", "Reports"],
            icons=["speedometer2", "cart", "boxes", "truck", "receipt", "person-lock", "bell", "bar-chart"],
            menu_icon="capsule",
            default_index=0,
        )
    return selected

# =========================
# وظائف مساعدة
# =========================
def create_invoice(cart_items, user):
    if not cart_items:
        return None

    df_cart = pd.DataFrame(cart_items)
    total = df_cart['total'].sum()
    invoice_no = f"INV-{int(datetime.now().timestamp())}"

    with engine.begin() as conn:
        conn.execute(
            "INSERT INTO invoices (invoice_no, date, user, total) VALUES (?, ?, ?, ?)",
            (invoice_no, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user, total)
        )
        invoice_id = pd.read_sql("SELECT last_insert_rowid() as id", conn).iloc[0]['id']

        for _, row in df_cart.iterrows():
            conn.execute(
                "INSERT INTO invoice_items (invoice_id, product_name, quantity, price, total) VALUES (?, ?, ?, ?, ?)",
                (invoice_id, row['product_name'], int(row['quantity']), float(row['price']), float(row['total']))
            )
            # تحديث المخزون
            conn.execute(
                "UPDATE products SET quantity = quantity - ? WHERE name = ?",
                (int(row['quantity']), row['product_name'])
            )

    return invoice_no

def add_purchase(supplier, product_name, quantity, cost):
    total = quantity * cost
    with engine.begin() as conn:
        conn.execute(
            "INSERT INTO purchases (date, supplier, product_name, quantity, cost, total) VALUES (?, ?, ?, ?, ?, ?)",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), supplier, product_name, int(quantity), float(cost), float(total))
        )
        # زيادة المخزون
        conn.execute(
            "UPDATE products SET quantity = quantity + ?, purchase_price = ? WHERE name = ?",
            (int(quantity), float(cost), product_name)
        )

# =========================
# واجهات الصفحات
# =========================

def page_dashboard():
    st.markdown('<div class="main-title">💊 RRB Pharmacy Dashboard</div>', unsafe_allow_html=True)

    products = load_products()
    invoices = load_invoices()
    purchases = load_purchases()

    total_products = len(products)
    low_stock = len(products[products['quantity'] <= 15])
    total_sales = invoices['total'].sum() if not invoices.empty else 0
    total_purchases = purchases['total'].sum() if not purchases.empty else 0
    profit = total_sales - total_purchases

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Products", total_products)
    col2.metric("Low Stock", low_stock)
    col3.metric("Total Sales", f"SDG {total_sales:,.0f}")
    col4.metric("Estimated Profit", f"SDG {profit:,.0f}")

    st.divider()

    if not invoices.empty:
        invoices['date'] = pd.to_datetime(invoices['date'])
        invoices['Month'] = invoices['date'].dt.to_period('M').astype(str)
        sales_data = invoices.groupby('Month')['total'].sum().reset_index(name='Sales')
        fig = px.bar(sales_data, x='Month', y='Sales', title='Monthly Sales')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No sales data yet.")

def page_pos():
    st.markdown('<div class="main-title">🛒 Point Of Sale</div>', unsafe_allow_html=True)

    products = load_products()
    product_names = products['name'].tolist()

    if "cart" not in st.session_state:
        st.session_state.cart = []

    col1, col2 = st.columns([2, 1])

    with col1:
        selected_product = st.selectbox("Select Product", product_names)
        qty = st.number_input("Quantity", min_value=1, value=1)

        product_row = products[products['name'] == selected_product]
        if not product_row.empty:
            product_row = product_row.iloc[0]
            price = product_row['selling_price']
            total = qty * price

            st.write(f"Price: SDG {price}")
            st.write(f"Total: SDG {total}")

            if st.button("Add to Cart"):
                if qty <= product_row['quantity']:
                    st.session_state.cart.append({
                        "product_name": selected_product,
                        "quantity": qty,
                        "price": price,
                        "total": total
                    })
                    st.success("Added to cart")
                else:
                    st.error("Not enough stock!")

    with col2:
        st.subheader("🧾 Cart")
        if st.session_state.cart:
            df_cart = pd.DataFrame(st.session_state.cart)
            st.table(df_cart)
            grand_total = df_cart['total'].sum()
            st.write(f"**Grand Total: SDG {grand_total}**")

            if st.button("Complete Sale"):
                invoice_no = create_invoice(st.session_state.cart, st.session_state.username)
                if invoice_no:
                    st.success(f"Sale Completed. Invoice No: {invoice_no}")
                    st.session_state.cart = []
                    st.experimental_rerun()
        else:
            st.info("Cart is empty.")

def page_inventory():
    st.markdown('<div class="main-title">📦 Inventory Management</div>', unsafe_allow_html=True)

    products = load_products()
    st.dataframe(products, use_container_width=True)

    st.subheader("Add Product")

    with st.form("add_product"):
        name = st.text_input("Product Name")
        barcode = st.text_input("Barcode")
        quantity = st.number_input("Quantity", min_value=0)
        purchase_price = st.number_input("Purchase Price", min_value=0.0)
        selling_price = st.number_input("Selling Price", min_value=0.0)
        expiry = st.date_input("Expiry Date")

        submit = st.form_submit_button("Add")

        if submit and name:
            new_product = pd.DataFrame({
                "name": [name],
                "barcode": [barcode],
                "quantity": [quantity],
                "purchase_price": [purchase_price],
                "selling_price": [selling_price],
                "expiry_date": [expiry.strftime("%Y-%m-%d")]
            })
            products_updated = pd.concat([products, new_product], ignore_index=True)
            products_updated.to_sql('products', engine, if_exists='replace', index=False)
            st.success("Product Added Successfully")
            st.experimental_rerun()

def page_purchases():
    st.markdown('<div class="main-title">🚚 Purchases & Suppliers</div>', unsafe_allow_html=True)

    products = load_products()
    product_names = products['name'].tolist()

    st.subheader("Add Purchase")

    with st.form("add_purchase"):
        supplier = st.text_input("Supplier Name")
        product_name = st.selectbox("Product", product_names)
        quantity = st.number_input("Quantity", min_value=1, value=1)
        cost = st.number_input("Cost per Unit", min_value=0.0)

        submit = st.form_submit_button("Save Purchase")

        if submit and supplier:
            add_purchase(supplier, product_name, quantity, cost)
            st.success("Purchase saved and stock updated.")
            st.experimental_rerun()

    st.subheader("Purchases History")
    purchases = load_purchases()
    if not purchases.empty:
        st.dataframe(purchases, use_container_width=True)
    else:
        st.info("No purchases recorded yet.")

def page_invoices():
    st.markdown('<div class="main-title">📄 Invoices</div>', unsafe_allow_html=True)

    invoices = load_invoices()
    if invoices.empty:
        st.info("No invoices yet.")
        return

    st.dataframe(invoices, use_container_width=True)

    invoice_ids = invoices['id'].tolist()
    selected_id = st.selectbox("Select Invoice ID", invoice_ids)

    if selected_id:
        with engine.connect() as conn:
            items = pd.read_sql(
                f"SELECT * FROM invoice_items WHERE invoice_id = {selected_id}",
                conn
            )
        st.subheader(f"Invoice Items (ID: {selected_id})")
        st.table(items)

def page_users():
    if st.session_state.role != "admin":
        st.error("Access denied. Admins only.")
        return

    st.markdown('<div class="main-title">👤 Users & Roles</div>', unsafe_allow_html=True)

    with engine.connect() as conn:
        users = pd.read_sql("SELECT id, username, role FROM users", conn)

    st.subheader("Existing Users")
    st.dataframe(users, use_container_width=True)

    st.subheader("Add User")

    with st.form("add_user"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        role = st.selectbox("Role", ["admin", "cashier", "manager"])

        submit = st.form_submit_button("Create User")

        if submit and username and password:
            try:
                with engine.begin() as conn:
                    conn.execute(
                        "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                        (username, password, role)
                    )
                st.success("User created successfully.")
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Error: {e}")

def page_alerts():
    st.markdown('<div class="main-title">🚨 Alerts Center</div>', unsafe_allow_html=True)

    products = load_products()

    st.subheader("Low Stock Products")
    low_stock_products = products[products['quantity'] <= 15]
    if not low_stock_products.empty:
        st.dataframe(low_stock_products, use_container_width=True)
    else:
        st.info("No low stock products.")

    st.subheader("Expiry Alerts")
    products['expiry_date'] = pd.to_datetime(products['expiry_date'])
    expiry_alerts = products[
        products['expiry_date'] <= datetime.now() + timedelta(days=30)
    ]
    if not expiry_alerts.empty:
        st.dataframe(expiry_alerts, use_container_width=True)
    else:
        st.info("No expiry alerts.")

def page_reports():
    st.markdown('<div class="main-title">📊 Reports & Analytics</div>', unsafe_allow_html=True)

    products = load_products()
    invoices = load_invoices()
    purchases = load_purchases()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Stock Distribution")
        if not products.empty:
            fig1 = px.pie(
                products,
                names='name',
                values='quantity',
                title='Stock Distribution'
            )
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.info("No products.")

    with col2:
        st.subheader("Selling Prices")
        if not products.empty:
            fig2 = px.bar(
                products,
                x='name',
                y='selling_price',
                title='Selling Prices'
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No products.")

    st.divider()

    st.subheader("Sales vs Purchases")
    total_sales = invoices['total'].sum() if not invoices.empty else 0
    total_purchases = purchases['total'].sum() if not purchases.empty else 0

    df_sp = pd.DataFrame({
        "Type": ["Sales", "Purchases"],
        "Amount": [total_sales, total_purchases]
    })
    fig3 = px.bar(df_sp, x="Type", y="Amount", title="Sales vs Purchases")
    st.plotly_chart(fig3, use_container_width=True)

# =========================
# تشغيل التطبيق
# =========================
if not st.session_state.logged_in:
    login_screen()
else:
    selected = sidebar_menu()

    if selected == "Dashboard":
        page_dashboard()
    elif selected == "POS":
        page_pos()
    elif selected == "Inventory":
        page_inventory()
    elif selected == "Purchases":
        page_purchases()
    elif selected == "Invoices":
        page_invoices()
    elif selected == "Users":
        page_users()
    elif selected == "Alerts":
        page_alerts()
    elif selected == "Reports":
        page_reports()
