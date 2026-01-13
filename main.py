import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
import random
import time
import os

# --- CONFIGURATION ---
# The DB_URL should be added in Streamlit Cloud -> Settings -> Secrets
# Format: DB_URL = "postgresql://user:password@host:port/dbname?sslmode=require"
DB_URL = st.secrets.get("DB_URL")
SHOP_NAME = "EXIDE CARE VIKAS 23"


# --- AUTHENTICATION SYSTEM ---
def check_login(username, password):
    """Verify credentials against Streamlit Secrets to ensure persistence."""
    # We use st.secrets here because credentials.txt would also reset on deployment.
    # Set these in Streamlit Cloud: ADMIN_USER="admin", ADMIN_PASSWORD="yourpassword"
    admin_user = st.secrets.get("ADMIN_USER", "admin")
    admin_pw = st.secrets.get("ADMIN_PASSWORD", "exide23")
    return username == admin_user and password == admin_pw


# --- DATABASE MANAGEMENT ---
def get_db_engine():
    """Create a SQLAlchemy engine for PostgreSQL."""
    if not DB_URL:
        st.error("Missing DB_URL in Streamlit Secrets!")
        st.stop()
    return create_engine(DB_URL)


def init_db():
    """Initialize the PostgreSQL database with necessary tables."""
    engine = get_db_engine()
    with engine.begin() as conn:
        # Customer Table
        conn.execute(text('''CREATE TABLE IF NOT EXISTS customers
                     (
                         phone TEXT PRIMARY KEY,
                         name TEXT,
                         created_at TEXT
                     )'''))

        # Battery Table
        conn.execute(text('''CREATE TABLE IF NOT EXISTS batteries
                     (
                         serial_no TEXT PRIMARY KEY,
                         model_type TEXT,
                         status TEXT,
                         sold_date TEXT,
                         date_of_purchase TEXT,
                         warranty_expiry TEXT,
                         current_owner_phone TEXT,
                         ticket_id TEXT,
                         vehicle_no TEXT
                     )'''))

        # Exchange/Service Logs
        # Note: Postgres uses SERIAL for autoincrement
        conn.execute(text('''CREATE TABLE IF NOT EXISTS exchanges
                     (
                         id SERIAL PRIMARY KEY,
                         date TEXT,
                         old_battery_serial TEXT,
                         new_battery_serial TEXT,
                         customer_phone TEXT,
                         action_taken TEXT,
                         notes TEXT
                     )'''))


# --- HELPER FUNCTIONS ---
def calculate_age(purchase_date_str):
    if not purchase_date_str: return "N/A"
    try:
        p_date = datetime.strptime(purchase_date_str, "%Y-%m-%d")
        today = datetime.now()
        diff = today - p_date
        days = diff.days
        months = days // 30
        remaining_days = days % 30
        return f"{days} days (~{months} months, {remaining_days} days)"
    except:
        return "Invalid Date"


def generate_otp():
    return str(random.randint(1000, 9999))


def send_otp_simulation(phone, otp):
    with st.spinner(f"Sending OTP to {phone}..."):
        time.sleep(1)
    st.toast(f"🔔 SMS SENT: Your OTP is {otp}", icon="📱")
    return True


# --- CALLBACKS ---
def verify_claim_otp():
    if st.session_state.claim_otp_input == st.session_state.current_otp:
        st.session_state.otp_verified = True
    else:
        st.error("Invalid OTP.")


def verify_pickup_otp():
    if st.session_state.pickup_otp_input == st.session_state.current_otp:
        st.session_state.pickup_verified = True
    else:
        st.error("Invalid OTP.")


def process_pickup_db(serial, phone):
    """Mark battery as returned to customer."""
    try:
        engine = get_db_engine()
        with engine.begin() as conn:
            conn.execute(text("UPDATE batteries SET status='active_with_customer' WHERE serial_no=:serial"),
                         {"serial": serial})
            conn.execute(text("""
                INSERT INTO exchanges (date, old_battery_serial, customer_phone, action_taken, notes) 
                VALUES (:date, :serial, :phone, :action, :notes)
            """), {
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "serial": serial,
                "phone": phone,
                "action": "RETURNED_TO_CUSTOMER",
                "notes": "Service completed, battery returned."
            })
        return True
    except Exception as e:
        st.error(f"Database Error: {e}")
        return False


# --- PAGE COMPONENTS ---
def page_dashboard():
    st.title(f"🔋 {SHOP_NAME} Dashboard")
    engine = get_db_engine()
    col1, col2, col3 = st.columns(3)

    with engine.connect() as conn:
        total_customers = pd.read_sql(text("SELECT count(*) as cnt FROM customers"), conn).iloc[0]['cnt']
        batteries_replaced = \
        pd.read_sql(text("SELECT count(*) as cnt FROM batteries WHERE status='replaced'"), conn).iloc[0]['cnt']
        exchanges_done = pd.read_sql(text("SELECT count(*) as cnt FROM exchanges"), conn).iloc[0]['cnt']

    col1.metric("Total Customers", total_customers)
    col2.metric("Active Batteries (Replaced)", batteries_replaced)
    col3.metric("Total Services/Exchanges", exchanges_done)

    st.markdown("---")
    st.subheader("🛠️ Active Service Management")
    with engine.connect() as conn:
        in_service = pd.read_sql(text("""
                                 SELECT serial_no, current_owner_phone, status, date_of_purchase, ticket_id, vehicle_no
                                 FROM batteries
                                 WHERE status IN ('pending', 'ready_for_pickup')
                                 """), conn)

    if not in_service.empty:
        for index, row in in_service.iterrows():
            age_info = calculate_age(row['date_of_purchase'])
            with st.expander(
                    f"Battery: {row['serial_no']} | Vehicle: {row['vehicle_no'] or 'N/A'} | Status: {row['status'].upper()}"):
                st.write(f"**Ticket ID:** {row['ticket_id'] or 'N/A'}")
                st.write(f"**Age since Purchase:** {age_info}")

                status_options = ['pending', 'ready_for_pickup', 'returned_faulty']
                new_status = st.selectbox(
                    f"Update status for {row['serial_no']}",
                    status_options,
                    index=status_options.index(row['status']) if row['status'] in status_options else 0,
                    key=f"status_{row['serial_no']}"
                )

                if new_status != row['status']:
                    if st.button(f"Save Status for {row['serial_no']}", key=f"btn_{row['serial_no']}"):
                        with engine.begin() as conn:
                            conn.execute(text("UPDATE batteries SET status=:status WHERE serial_no=:serial"),
                                         {"status": new_status, "serial": row['serial_no']})
                        st.success(f"Status updated to {new_status}!")
                        st.rerun()
    else:
        st.info("No batteries currently pending or ready for pickup.")

    st.markdown("---")
    st.subheader("Recent Service History")
    with engine.connect() as conn:
        recent = pd.read_sql(text("SELECT * FROM exchanges ORDER BY id DESC LIMIT 5"), conn)
    st.dataframe(recent, use_container_width=True)


def page_service():
    st.title("🔄 Process Service & Warranty")

    tab_claim, tab_pickup = st.tabs(["New Warranty Claim", "Customer Pickup / Return"])

    if 'otp_verified' not in st.session_state:
        st.session_state.otp_verified = False
    if 'current_otp' not in st.session_state:
        st.session_state.current_otp = None
    if 'exchange_complete' not in st.session_state:
        st.session_state.exchange_complete = False

    with tab_claim:
        if st.session_state.exchange_complete:
            st.success("Exchange Logged Successfully!")
            summary = st.session_state.last_exchange_summary

            # Professionally formatted HTML Receipt
            html_receipt = f"""
            <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 20px; border: 1px solid #eee; max-width: 500px; margin: auto; background-color: white; color: #333;">
                <div style="text-align: center; border-bottom: 2px solid #ed1c24; padding-bottom: 10px;">
                    <h2 style="margin: 0; color: #ed1c24;">{SHOP_NAME}</h2>
                    <p style="margin: 5px 0; font-size: 14px;">Authorized Exide Care Dealer</p>
                </div>

                <div style="margin: 20px 0;">
                    <h4 style="border-bottom: 1px solid #eee; padding-bottom: 5px;">WARRANTY TRANSACTION RECEIPT</h4>
                    <table style="width: 100%; font-size: 14px; border-collapse: collapse;">
                        <tr><td style="padding: 5px 0; color: #666;">Customer Name:</td><td style="padding: 5px 0; font-weight: bold;">{summary['cust_name']}</td></tr>
                        <tr><td style="padding: 5px 0; color: #666;">Vehicle Reg No:</td><td style="padding: 5px 0; font-weight: bold;">{summary['vehicle_no']}</td></tr>
                        <tr><td style="padding: 5px 0; color: #666;">New Battery SN:</td><td style="padding: 5px 0; font-weight: bold;">{summary['new_serial']}</td></tr>
                        <tr><td style="padding: 5px 0; color: #666;">Old Battery SN:</td><td style="padding: 5px 0; font-weight: bold;">{summary['old_serial']}</td></tr>
                        <tr><td style="padding: 5px 0; color: #666;">Exide Ticket ID:</td><td style="padding: 5px 0; font-weight: bold;">{summary['ticket_id']}</td></tr>
                        <tr><td style="padding: 5px 0; color: #666;">Battery Model:</td><td style="padding: 5px 0; font-weight: bold;">{summary['new_model']}</td></tr>
                        <tr><td style="padding: 5px 0; color: #666;">Purchase Date:</td><td style="padding: 5px 0; font-weight: bold;">{summary['purchase_date']}</td></tr>
                    </table>
                </div>

                <div style="margin-top: 20px; padding: 10px; background-color: #f9f9f9; border-radius: 4px; font-size: 13px;">
                    <strong>Technician Notes:</strong><br>
                    {summary['notes']}
                </div>

                <div style="margin-top: 30px; text-align: center; font-size: 12px; color: #999; border-top: 1px solid #eee; padding-top: 10px;">
                    Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}<br>
                    Thank you for choosing Exide Care!
                </div>
            </div>
            """

            st.markdown("### 📄 Transaction Receipt")
            st.components.v1.html(html_receipt, height=500, scrolling=True)

            col_p1, col_p2 = st.columns(2)
            with col_p1:
                if st.button("🖨️ Print Receipt"):
                    st.components.v1.html(f"""
                        <script>
                            var printWin = window.open('', '', 'width=800,height=900');
                            printWin.document.write('<html><head><title>Receipt - {summary['new_serial']}</title></head><body>');
                            printWin.document.write(`{html_receipt}`);
                            printWin.document.write('<script>window.onload = function() {{ window.print(); window.close(); }}<\\/script>');
                            printWin.document.write('</body></html>');
                            printWin.document.close();
                        </script>
                    """, height=0)

            with col_p2:
                st.download_button("💾 Save as HTML", html_receipt, file_name=f"receipt_{summary['new_serial']}.html",
                                   mime="text/html")

            if st.button("Process Another Claim"):
                st.session_state.exchange_complete = False
                st.rerun()
            return

        st.subheader("1. Register Faulty Battery")

        with st.form("check_form"):
            col1, col2 = st.columns(2)
            phone = col1.text_input("Customer Phone Number", max_chars=10)
            old_serial = col2.text_input("Faulty Battery Serial No.")
            check_submit = st.form_submit_button("Verify Details & Send OTP")

        if check_submit:
            if len(phone) < 10 or not old_serial:
                st.error("Please enter valid Phone and Serial Number.")
            else:
                engine = get_db_engine()
                with engine.connect() as conn:
                    batt = pd.read_sql(text("SELECT * FROM batteries WHERE serial_no=:serial"),
                                       conn, params={"serial": old_serial})

                valid_warranty = True
                if not batt.empty:
                    expiry = batt.iloc[0]['warranty_expiry']
                    if expiry and datetime.now().strftime("%Y-%m-%d") > expiry:
                        st.warning(f"⚠️ Warning: This battery warranty expired on {expiry}")
                        valid_warranty = False

                if valid_warranty:
                    otp = generate_otp()
                    st.session_state.current_otp = otp
                    st.session_state.temp_phone = phone
                    st.session_state.temp_old_serial = old_serial
                    st.session_state.workflow = "CLAIM"
                    st.session_state.otp_verified = False
                    send_otp_simulation(phone, otp)
                    st.info("OTP sent to customer's phone.")

        if st.session_state.current_otp and not st.session_state.otp_verified and st.session_state.get(
                'workflow') == "CLAIM":
            st.text_input("Enter OTP for Warranty Claim", key="claim_otp_input")
            st.button("Verify OTP", key="claim_verify_btn", on_click=verify_claim_otp)

        if st.session_state.otp_verified and st.session_state.get('workflow') == "CLAIM":
            st.subheader("Resolution")
            action = st.radio("Select Resolution:",
                              ["Keep for Service (Mark as Pending)", "Issue New Replacement Battery"])

            if action == "Issue New Replacement Battery":
                with st.form("exchange_final"):
                    col_a, col_b = st.columns(2)
                    cust_name = col_a.text_input("Customer Name")
                    vehicle_no = col_b.text_input("Vehicle Registration No.")

                    col_c, col_d = st.columns(2)
                    new_serial = col_c.text_input("New Battery Serial Number")
                    ticket_id = col_d.text_input("Exide Ticket ID")

                    col_e, col_f = st.columns(2)
                    new_model = col_e.selectbox("Battery Model",
                                                ["Exide Mileage", "Exide Matrix", "Exide Eezy", "Exide Gold"])
                    purchase_date = col_f.date_input("Date of Purchase", value=datetime.now())

                    notes = st.text_area("Technician Notes", "Warranty replacement issued.")
                    final_submit = st.form_submit_button("Complete Exchange")

                    if final_submit:
                        if not new_serial or not ticket_id:
                            st.error("Serial and Ticket ID are mandatory.")
                        else:
                            engine = get_db_engine()
                            try:
                                with engine.begin() as conn:
                                    p_date_str = purchase_date.strftime("%Y-%m-%d")
                                    # Postgres UPSERT for Customer
                                    conn.execute(text("""
                                        INSERT INTO customers (phone, name, created_at) VALUES (:phone, :name, :date)
                                        ON CONFLICT (phone) DO UPDATE SET name = EXCLUDED.name
                                    """), {"phone": st.session_state.temp_phone, "name": cust_name,
                                           "date": datetime.now().strftime("%Y-%m-%d")})

                                    conn.execute(
                                        text("UPDATE batteries SET status='returned_faulty' WHERE serial_no=:serial"),
                                        {"serial": st.session_state.temp_old_serial})

                                    # Postgres UPSERT for Battery
                                    conn.execute(text("""
                                        INSERT INTO batteries (serial_no, model_type, status, sold_date, date_of_purchase, current_owner_phone, ticket_id, vehicle_no)
                                        VALUES (:serial, :model, 'sold', :sold_date, :p_date, :phone, :ticket, :vehicle)
                                        ON CONFLICT (serial_no) DO UPDATE SET 
                                            status = EXCLUDED.status, 
                                            ticket_id = EXCLUDED.ticket_id, 
                                            current_owner_phone = EXCLUDED.current_owner_phone,
                                            vehicle_no = EXCLUDED.vehicle_no
                                    """), {
                                        "serial": new_serial, "model": new_model,
                                        "sold_date": datetime.now().strftime("%Y-%m-%d"),
                                        "p_date": p_date_str, "phone": st.session_state.temp_phone, "ticket": ticket_id,
                                        "vehicle": vehicle_no
                                    })

                                    conn.execute(text("""
                                        INSERT INTO exchanges (date, old_battery_serial, new_battery_serial, customer_phone, action_taken, notes) 
                                        VALUES (:date, :old, :new, :phone, 'NEW_REPLACEMENT_ISSUED', :notes)
                                    """), {
                                        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        "old": st.session_state.temp_old_serial,
                                        "new": new_serial, "phone": st.session_state.temp_phone,
                                        "notes": f"Ticket: {ticket_id}. {notes}"
                                    })

                                st.session_state.last_exchange_summary = {
                                    'cust_name': cust_name, 'vehicle_no': vehicle_no, 'new_serial': new_serial,
                                    'old_serial': st.session_state.temp_old_serial, 'ticket_id': ticket_id,
                                    'new_model': new_model, 'purchase_date': p_date_str, 'notes': notes
                                }
                                st.session_state.exchange_complete = True
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
            else:
                with st.form("repair_later"):
                    col_x, col_y = st.columns(2)
                    cust_name = col_x.text_input("Customer Name")
                    ticket_id = col_y.text_input("Exide Ticket ID (If generated)")
                    col_z1, col_z2 = st.columns(2)
                    vehicle_no = col_z1.text_input("Vehicle Registration No.")
                    purchase_date = col_z2.date_input("Date of Purchase", value=datetime.now())
                    notes = st.text_area("Initial Observation", "Keeping for service/charging.")
                    repair_submit = st.form_submit_button("Log Entry - Battery Kept for Service")

                    if repair_submit:
                        engine = get_db_engine()
                        try:
                            with engine.begin() as conn:
                                conn.execute(text("""
                                    INSERT INTO customers (phone, name, created_at) VALUES (:phone, :name, :date)
                                    ON CONFLICT (phone) DO UPDATE SET name = EXCLUDED.name
                                """), {"phone": st.session_state.temp_phone, "name": cust_name,
                                       "date": datetime.now().strftime("%Y-%m-%d")})

                                conn.execute(text("""
                                    INSERT INTO batteries (serial_no, status, current_owner_phone, ticket_id, vehicle_no, date_of_purchase)
                                    VALUES (:serial, 'pending', :phone, :ticket, :vehicle, :p_date)
                                    ON CONFLICT (serial_no) DO UPDATE SET 
                                        status = 'pending', 
                                        current_owner_phone = EXCLUDED.current_owner_phone, 
                                        ticket_id = EXCLUDED.ticket_id, 
                                        vehicle_no = EXCLUDED.vehicle_no, 
                                        date_of_purchase = EXCLUDED.date_of_purchase
                                """), {
                                    "serial": st.session_state.temp_old_serial, "phone": st.session_state.temp_phone,
                                    "ticket": ticket_id, "vehicle": vehicle_no,
                                    "p_date": purchase_date.strftime("%Y-%m-%d")
                                })

                                conn.execute(text("""
                                    INSERT INTO exchanges (date, old_battery_serial, new_battery_serial, customer_phone, action_taken, notes) 
                                    VALUES (:date, :old, :new, :phone, 'SERVICE_PENDING', :notes)
                                """), {
                                    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    "old": st.session_state.temp_old_serial,
                                    "new": st.session_state.temp_old_serial, "phone": st.session_state.temp_phone,
                                    "notes": f"Ticket: {ticket_id}. {notes}"
                                })
                            st.info(f"Battery {st.session_state.temp_old_serial} is now marked as 'PENDING'.")
                            st.session_state.otp_verified = False
                        except Exception as e:
                            st.error(f"Error: {e}")

    with tab_pickup:
        st.subheader("Return Battery to Customer")
        search_phone = st.text_input("Enter Customer Phone Number to Find Items", key="pickup_search_phone")
        if search_phone:
            engine = get_db_engine()
            with engine.connect() as conn:
                ready_items = pd.read_sql(text("""
                    SELECT serial_no, model_type, status, ticket_id, vehicle_no, date_of_purchase
                    FROM batteries 
                    WHERE current_owner_phone=:phone AND status IN ('ready_for_pickup', 'pending')
                """), conn, params={"phone": search_phone})

            if not ready_items.empty:
                st.write("Items in service:")
                ready_items['Age'] = ready_items['date_of_purchase'].apply(calculate_age)
                st.dataframe(ready_items[['serial_no', 'status', 'ticket_id', 'vehicle_no', 'Age']])
                selected_serial = st.selectbox("Select Battery to Return", ready_items['serial_no'].tolist())

                if st.button("Verify Customer & Send OTP for Pickup", key="pickup_send_otp"):
                    otp = generate_otp()
                    st.session_state.current_otp = otp
                    st.session_state.temp_phone = search_phone
                    st.session_state.temp_pickup_serial = selected_serial
                    st.session_state.workflow = "PICKUP"
                    st.session_state.pickup_verified = False
                    send_otp_simulation(search_phone, otp)

                if st.session_state.current_otp and st.session_state.get('workflow') == "PICKUP":
                    st.text_input("Enter OTP for Pickup", key="pickup_otp_input")
                    if st.button("Confirm Return to Customer", key="confirm_pickup_btn", on_click=verify_pickup_otp):
                        if st.session_state.get('pickup_verified'):
                            if process_pickup_db(st.session_state.temp_pickup_serial, search_phone):
                                st.success(f"Battery {st.session_state.temp_pickup_serial} returned successfully!")
                                st.session_state.current_otp = None
                                st.session_state.workflow = None
                                st.session_state.pickup_verified = False
                                st.rerun()
            else:
                st.warning("No items found in service for this phone number.")


def page_history():
    st.title("🔎 Search History")
    search_type = st.radio("Search By:", ["Battery Serial Number", "Customer Phone"])
    query = st.text_input("Enter Search Term")
    if query:
        engine = get_db_engine()
        with engine.connect() as conn:
            if search_type == "Battery Serial Number":
                batt = pd.read_sql(text("SELECT * FROM batteries WHERE serial_no=:q"), conn, params={"q": query})
                if not batt.empty:
                    row = batt.iloc[0]
                    st.subheader("Battery Details")
                    st.write(f"**Ticket ID:** {row['ticket_id'] or 'N/A'}")
                    st.write(f"**Vehicle No:** {row['vehicle_no'] or 'N/A'}")
                    st.write(f"**Age since Purchase:** {calculate_age(row['date_of_purchase'])}")
                    st.dataframe(batt)
                    st.subheader("Service History")
                    trans = pd.read_sql(text("""SELECT * FROM exchanges 
                                            WHERE old_battery_serial=:q 
                                            OR new_battery_serial=:q """), conn, params={"q": query})
                    st.dataframe(trans)
                else:
                    st.warning("No battery found.")
            else:
                cust = pd.read_sql(text("SELECT * FROM customers WHERE phone=:q"), conn, params={"q": query})
                if not cust.empty:
                    st.write(f"**Customer Name:** {cust.iloc[0]['name']}")
                    st.subheader("Batteries Owned")
                    owned = pd.read_sql(text("SELECT * FROM batteries WHERE current_owner_phone=:q"), conn,
                                        params={"q": query})
                    if not owned.empty:
                        owned['Age'] = owned['date_of_purchase'].apply(calculate_age)
                        st.dataframe(owned[['serial_no', 'model_type', 'status', 'ticket_id', 'vehicle_no', 'Age']])
                    st.subheader("Exchange Logs")
                    history = pd.read_sql(text("SELECT * FROM exchanges WHERE customer_phone=:q"), conn,
                                          params={"q": query})
                    st.dataframe(history)
                else:
                    st.warning("Customer not found.")


def page_inventory():
    st.title("📦 Quick Inventory Add")
    with st.form("add_stock"):
        serial = st.text_input("Serial Number")
        model = st.selectbox("Model", ["Exide Mileage", "Exide Matrix", "Exide Eezy", "Exide Gold"])
        p_date = st.date_input("Date of Purchase (If pre-owned/return)", value=datetime.now())
        submit = st.form_submit_button("Add to Stock")
        if submit and serial:
            engine = get_db_engine()
            try:
                with engine.begin() as conn:
                    conn.execute(text('''INSERT INTO batteries (serial_no, model_type, status, date_of_purchase)
                                 VALUES (:s, :m, 'in_stock', :d)'''),
                                 {"s": serial, "m": model, "d": p_date.strftime("%Y-%m-%d")})
                st.success(f"Battery {serial} added. Age: {calculate_age(p_date.strftime('%Y-%m-%d'))}")
            except Exception as e:
                st.error(f"Error: {e}")


def page_stock_loan_exide():
    st.title("🏭 Stock Loan Exide")
    with st.form("add_stock_loan"):
        st.subheader("New Stock Request / Loan")
        serial = st.text_input("Serial Number")
        model = st.selectbox("Battery Model", ["Exide Mileage", "Exide Matrix", "Exide Eezy", "Exide Gold"])
        req_date = st.date_input("Date", value=datetime.now())
        submit = st.form_submit_button("Add to Pending Stock")
        if submit:
            if not serial:
                st.error("Serial Number is required")
            else:
                engine = get_db_engine()
                try:
                    with engine.begin() as conn:
                        conn.execute(text("""
                            INSERT INTO batteries (serial_no, model_type, status, date_of_purchase) 
                            VALUES (:s, :m, 'factory_pending', :d)
                            ON CONFLICT (serial_no) DO UPDATE SET status = 'factory_pending'
                        """), {"s": serial, "m": model, "d": req_date.strftime("%Y-%m-%d")})
                    st.success(f"Added {serial} to pending list.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    st.markdown("---")
    st.subheader("⏳ Pending Stock from Exide Factory")
    engine = get_db_engine()
    with engine.connect() as conn:
        pending_stock = pd.read_sql(text("SELECT * FROM batteries WHERE status='factory_pending'"), conn)

    if not pending_stock.empty:
        for index, row in pending_stock.iterrows():
            col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
            with col1:
                st.write(f"**SN:** {row['serial_no']}")
            with col2:
                st.write(f"**Model:** {row['model_type']}")
            with col3:
                st.write(f"**Date:** {row['date_of_purchase']}")
            with col4:
                if st.button("Mark Received", key=f"recv_{row['serial_no']}"):
                    with engine.begin() as conn:
                        conn.execute(text("UPDATE batteries SET status='in_stock' WHERE serial_no=:s"),
                                     {"s": row['serial_no']})
                        conn.execute(text('''INSERT INTO exchanges (date, old_battery_serial, customer_phone, action_taken, notes) 
                                     VALUES (:d, :s, 'EXIDE_FACTORY', 'STOCK_RECEIVED', :n)'''),
                                     {"d": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "s": row['serial_no'],
                                      "n": f"Received stock: {row['model_type']}"})
                    st.success(f"Stock {row['serial_no']} received!")
                    st.rerun()
    else:
        st.info("No pending stock from factory.")

    st.markdown("---")
    st.subheader("📜 Received Stock History (Audit)")
    with engine.connect() as conn:
        audit_log = pd.read_sql(text("""
            SELECT date as "Received Date", old_battery_serial as "Serial No", notes as "Details" 
            FROM exchanges 
            WHERE action_taken='STOCK_RECEIVED' 
            ORDER BY id DESC
        """), conn)
    if not audit_log.empty:
        st.dataframe(audit_log, use_container_width=True)
    else:
        st.info("No stock receipt history found.")


def main():
    st.set_page_config(page_title="Exide Warranty System", page_icon="🔋")
    init_db()

    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.title("🔐 Login")
        user = st.text_input("Username")
        pw = st.text_input("Password", type="password")
        if st.button("Login"):
            if check_login(user, pw):
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Invalid credentials.")
        return

    st.sidebar.title(SHOP_NAME)
    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.rerun()

    menu = st.sidebar.radio("Menu", ["Dashboard", "Service", "Search History", "Stock Loan Exide"])
    if menu == "Dashboard":
        page_dashboard()
    elif menu == "Service":
        page_service()
    elif menu == "Search History":
        page_history()
    elif menu == "Stock Loan Exide":
        page_stock_loan_exide()
    #elif menu == "Add Inventory":
     #   page_inventory()


if __name__ == "__main__":
    main()