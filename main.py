import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import random
import time
import os

# --- CONFIGURATION ---
DB_FILE = "battery_shop.db"
SHOP_NAME = "EXIDE CARE VIKAS 23"


# --- DATABASE MANAGEMENT ---
def init_db():
    """Initialize the SQLite database with necessary tables and columns."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # Customer Table
    c.execute('''CREATE TABLE IF NOT EXISTS customers
                 (
                     phone
                     TEXT
                     PRIMARY
                     KEY,
                     name
                     TEXT,
                     created_at
                     TEXT
                 )''')

    # Battery Inventory/History Table
    c.execute('''CREATE TABLE IF NOT EXISTS batteries
                 (
                     serial_no
                     TEXT
                     PRIMARY
                     KEY,
                     model_type
                     TEXT,
                     status
                     TEXT,
                     sold_date
                     TEXT,
                     warranty_expiry
                     TEXT,
                     current_owner_phone
                     TEXT
                 )''')

    # Exchange/Service Logs
    c.execute('''CREATE TABLE IF NOT EXISTS exchanges
                 (
                     id
                     INTEGER
                     PRIMARY
                     KEY
                     AUTOINCREMENT,
                     date
                     TEXT,
                     old_battery_serial
                     TEXT,
                     new_battery_serial
                     TEXT,
                     customer_phone
                     TEXT,
                     action_taken
                     TEXT,
                     notes
                     TEXT
                 )''')

    # --- MIGRATION CHECK ---
    c.execute("PRAGMA table_info(exchanges)")
    columns = [column[1] for column in c.fetchall()]
    if 'action_taken' not in columns:
        try:
            c.execute("ALTER TABLE exchanges ADD COLUMN action_taken TEXT")
        except Exception as e:
            print(f"Migration notice: {e}")

    conn.commit()
    conn.close()


def get_db_connection():
    return sqlite3.connect(DB_FILE)


def cleanup_expired_data():
    """Automatically deletes records where the warranty has expired."""
    conn = get_db_connection()
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")

    try:
        c.execute("SELECT serial_no FROM batteries WHERE warranty_expiry < ? AND warranty_expiry IS NOT NULL", (today,))
        expired_batteries = [row[0] for row in c.fetchall()]

        if expired_batteries:
            placeholders = ','.join(['?'] * len(expired_batteries))
            c.execute(f'''DELETE FROM exchanges 
                          WHERE old_battery_serial IN ({placeholders}) 
                          OR new_battery_serial IN ({placeholders})''',
                      expired_batteries + expired_batteries)
            c.execute(f"DELETE FROM batteries WHERE serial_no IN ({placeholders})", expired_batteries)
            conn.commit()
    except Exception as e:
        print(f"Cleanup Error: {e}")
    finally:
        conn.close()


# --- HELPER FUNCTIONS ---

def generate_otp():
    """Generates a 4-digit OTP."""
    return str(random.randint(1000, 9999))


def send_otp_simulation(phone, otp):
    """Simulates sending an OTP."""
    with st.spinner(f"Sending OTP to {phone}..."):
        time.sleep(1)
    st.toast(f"🔔 SMS SENT: Your OTP is {otp}", icon="📱")
    return True


def process_pickup_db(serial, phone):
    """Helper to finalize the return of a battery to a customer."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("UPDATE batteries SET status='sold' WHERE serial_no=?", (serial,))
        c.execute(
            "INSERT INTO exchanges (date, old_battery_serial, new_battery_serial, customer_phone, action_taken, notes) VALUES (?, ?, ?, ?, ?, ?)",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), serial, serial, phone, "RETURNED_TO_CUST",
             "Service completed and returned to customer."))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error during pickup: {e}")
        return False
    finally:
        conn.close()


# --- UI PAGES ---

def page_dashboard():
    st.title(f"🔋 {SHOP_NAME} Dashboard")

    conn = get_db_connection()
    col1, col2, col3 = st.columns(3)

    total_customers = pd.read_sql("SELECT count(*) as cnt FROM customers", conn).iloc[0]['cnt']
    batteries_sold = pd.read_sql("SELECT count(*) as cnt FROM batteries WHERE status='sold'", conn).iloc[0]['cnt']
    exchanges_done = pd.read_sql("SELECT count(*) as cnt FROM exchanges", conn).iloc[0]['cnt']

    col1.metric("Total Customers", total_customers)
    col2.metric("Active Batteries (Sold)", batteries_sold)
    col3.metric("Total Services/Exchanges", exchanges_done)

    st.markdown("---")
    st.subheader("🛠️ Active Service Management")
    in_service = pd.read_sql("""
                             SELECT serial_no, current_owner_phone, status
                             FROM batteries
                             WHERE status IN ('pending', 'ready_for_pickup')
                             """, conn)

    if not in_service.empty:
        for index, row in in_service.iterrows():
            with st.expander(
                    f"Battery: {row['serial_no']} | Customer: {row['current_owner_phone']} | Current: {row['status'].upper()}"):
                status_options = ['pending', 'ready_for_pickup', 'returned_faulty']
                new_status = st.selectbox(
                    f"Update status for {row['serial_no']}",
                    status_options,
                    index=status_options.index(row['status']) if row['status'] in status_options else 0,
                    key=f"status_{row['serial_no']}"
                )

                if new_status != row['status']:
                    if st.button(f"Save Status for {row['serial_no']}", key=f"btn_{row['serial_no']}"):
                        c = conn.cursor()
                        c.execute("UPDATE batteries SET status=? WHERE serial_no=?", (new_status, row['serial_no']))
                        if new_status == 'returned_faulty':
                            c.execute(
                                "INSERT INTO exchanges (date, old_battery_serial, new_battery_serial, customer_phone, action_taken, notes) VALUES (?, ?, ?, ?, ?, ?)",
                                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), row['serial_no'], "N/A",
                                 row['current_owner_phone'], "MARKED_FAULTY",
                                 "Technician marked as faulty via Dashboard."))
                        conn.commit()
                        st.success(f"Status updated to {new_status}!")
                        st.rerun()
    else:
        st.info("No batteries currently pending or ready for pickup.")

    st.markdown("---")
    st.subheader("Recent Service History")
    recent = pd.read_sql("SELECT * FROM exchanges ORDER BY id DESC LIMIT 5", conn)
    st.dataframe(recent, use_container_width=True)
    conn.close()


def page_service():
    st.title("🔄 Process Service & Warranty")

    tab_claim, tab_pickup = st.tabs(["New Warranty Claim", "Customer Pickup / Return"])

    if 'otp_verified' not in st.session_state:
        st.session_state.otp_verified = False
    if 'current_otp' not in st.session_state:
        st.session_state.current_otp = None

    with tab_claim:
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
                conn = get_db_connection()
                batt = pd.read_sql(f"SELECT * FROM batteries WHERE serial_no='{old_serial}'", conn)

                valid_warranty = True
                if not batt.empty:
                    expiry = batt.iloc[0]['warranty_expiry']
                    if expiry and datetime.now().strftime("%Y-%m-%d") > expiry:
                        st.warning(f"⚠️ Warning: This battery warranty expired on {expiry}")
                        valid_warranty = False
                else:
                    st.info("New serial detected. Registering customer to this serial.")

                if valid_warranty:
                    otp = generate_otp()
                    st.session_state.current_otp = otp
                    st.session_state.temp_phone = phone
                    st.session_state.temp_old_serial = old_serial
                    st.session_state.workflow = "CLAIM"
                    st.session_state.otp_verified = False
                    send_otp_simulation(phone, otp)
                    st.info("OTP sent to customer's phone.")
                conn.close()

        if st.session_state.current_otp and not st.session_state.otp_verified and st.session_state.get(
                'workflow') == "CLAIM":
            otp_input = st.text_input("Enter OTP for Warranty Claim", key="claim_otp_field")
            if st.button("Verify OTP", key="claim_verify_btn"):
                if otp_input == st.session_state.current_otp:
                    st.session_state.otp_verified = True
                    st.success("Identity Verified!")
                    st.rerun()
                else:
                    st.error("Invalid OTP.")

        if st.session_state.otp_verified and st.session_state.get('workflow') == "CLAIM":
            st.subheader("Resolution")
            action = st.radio("Select Resolution:",
                              ["Keep for Service (Mark as Pending)", "Issue New Replacement Battery"])

            if action == "Issue New Replacement Battery":
                with st.form("exchange_final"):
                    cust_name = st.text_input("Customer Name")
                    new_serial = st.text_input("New Battery Serial Number (Scanning)")
                    new_model = st.selectbox("Battery Model",
                                             ["Exide Mileage", "Exide Matrix", "Exide Eezy", "Exide Gold"])
                    warranty_months = st.number_input("New Warranty Duration (Months)", min_value=12, value=48)
                    notes = st.text_area("Technician Notes", "Verified Dead Cell. Replaced with New Battery.")
                    final_submit = st.form_submit_button("Complete Exchange")

                    if final_submit:
                        if not new_serial:
                            st.error("Scan new serial.")
                        else:
                            conn = get_db_connection()
                            c = conn.cursor()
                            try:
                                c.execute("INSERT OR REPLACE INTO customers (phone, name, created_at) VALUES (?, ?, ?)",
                                          (st.session_state.temp_phone, cust_name, datetime.now().strftime("%Y-%m-%d")))
                                c.execute(
                                    "UPDATE batteries SET status='returned_faulty', current_owner_phone=NULL WHERE serial_no=?",
                                    (st.session_state.temp_old_serial,))
                                expiry_date = (datetime.now() + timedelta(days=30 * warranty_months)).strftime(
                                    "%Y-%m-%d")
                                c.execute(
                                    "INSERT OR REPLACE INTO batteries (serial_no, model_type, status, sold_date, warranty_expiry, current_owner_phone) VALUES (?, ?, 'sold', ?, ?, ?)",
                                    (new_serial, new_model, datetime.now().strftime("%Y-%m-%d"), expiry_date,
                                     st.session_state.temp_phone))
                                c.execute(
                                    "INSERT INTO exchanges (date, old_battery_serial, new_battery_serial, customer_phone, action_taken, notes) VALUES (?, ?, ?, ?, ?, ?)",
                                    (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), st.session_state.temp_old_serial,
                                     new_serial, st.session_state.temp_phone, "NEW_REPLACEMENT_ISSUED", notes))
                                conn.commit()
                                st.success(f"Replacement Success! New Battery {new_serial} issued.")
                                st.session_state.otp_verified = False
                                st.session_state.current_otp = None
                            finally:
                                conn.close()

            else:
                with st.form("repair_later"):
                    cust_name = st.text_input("Customer Name")
                    notes = st.text_area("Initial Observation", "Customer reports issue. Keeping for service.")
                    repair_submit = st.form_submit_button("Log Entry - Battery Kept for Service")
                    if repair_submit:
                        conn = get_db_connection()
                        c = conn.cursor()
                        try:
                            c.execute("INSERT OR REPLACE INTO customers (phone, name, created_at) VALUES (?, ?, ?)",
                                      (st.session_state.temp_phone, cust_name, datetime.now().strftime("%Y-%m-%d")))
                            c.execute(
                                "INSERT OR REPLACE INTO batteries (serial_no, status, current_owner_phone) VALUES (?, ?, ?)",
                                (st.session_state.temp_old_serial, 'pending', st.session_state.temp_phone))
                            c.execute(
                                "INSERT INTO exchanges (date, old_battery_serial, new_battery_serial, customer_phone, action_taken, notes) VALUES (?, ?, ?, ?, ?, ?)",
                                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), st.session_state.temp_old_serial,
                                 st.session_state.temp_old_serial, st.session_state.temp_phone, "SERVICE_PENDING",
                                 notes))
                            conn.commit()
                            st.info(f"Battery {st.session_state.temp_old_serial} is now marked as 'PENDING'.")
                            st.session_state.otp_verified = False
                            st.session_state.current_otp = None
                        finally:
                            conn.close()

    with tab_pickup:
        st.subheader("Return Battery to Customer")
        search_phone = st.text_input("Enter Customer Phone Number to Find Items", key="pickup_search_phone")

        if search_phone:
            conn = get_db_connection()
            ready_items = pd.read_sql(f"""
                SELECT serial_no, model_type, status 
                FROM batteries 
                WHERE current_owner_phone='{search_phone}' 
                AND status IN ('ready_for_pickup', 'pending')
            """, conn)
            conn.close()

            if not ready_items.empty:
                st.write("The following items are in service for this customer:")
                st.dataframe(ready_items)
                selected_serial = st.selectbox("Select Battery to Return", ready_items['serial_no'].tolist())

                if st.button("Verify Customer & Send OTP for Pickup", key="pickup_send_otp"):
                    otp = generate_otp()
                    st.session_state.current_otp = otp
                    st.session_state.temp_phone = search_phone
                    st.session_state.temp_pickup_serial = selected_serial
                    st.session_state.workflow = "PICKUP"
                    send_otp_simulation(search_phone, otp)

                if st.session_state.current_otp and st.session_state.get('workflow') == "PICKUP":
                    otp_pickup = st.text_input("Enter OTP for Pickup", key="otp_input_pickup")
                    if st.button("Confirm Return to Customer", key="confirm_pickup_btn"):
                        if otp_pickup == st.session_state.current_otp:
                            if process_pickup_db(st.session_state.temp_pickup_serial, search_phone):
                                st.success(f"Battery {st.session_state.temp_pickup_serial} returned successfully!")
                                st.session_state.current_otp = None
                                st.session_state.workflow = None
                                st.rerun()
                        else:
                            st.error("Invalid OTP.")
            else:
                st.warning("No items found in service for this phone number.")


def page_history():
    st.title("🔎 Search History")
    search_type = st.radio("Search By:", ["Battery Serial Number", "Customer Phone"])
    query = st.text_input("Enter Search Term")

    if query:
        conn = get_db_connection()
        if search_type == "Battery Serial Number":
            batt = pd.read_sql(f"SELECT * FROM batteries WHERE serial_no='{query}'", conn)
            if not batt.empty:
                row = batt.iloc[0]
                st.subheader("Battery Details")
                st.dataframe(batt)
                if row['status'] in ['pending', 'ready_for_pickup']:
                    st.info(f"Current Status: {row['status'].upper()}. You can process pickup here.")
                    if st.button(f"Generate OTP for Serial {row['serial_no']}"):
                        otp = generate_otp()
                        st.session_state.current_otp = otp
                        st.session_state.temp_phone = row['current_owner_phone']
                        st.session_state.temp_pickup_serial = row['serial_no']
                        st.session_state.workflow = "HISTORY_PICKUP"
                        send_otp_simulation(row['current_owner_phone'], otp)
                st.subheader("Service History")
                trans = pd.read_sql(f'''SELECT * FROM exchanges 
                                        WHERE old_battery_serial='{query}' 
                                        OR new_battery_serial='{query}' ''', conn)
                st.dataframe(trans)
            else:
                st.warning("No battery found.")
        else:
            cust = pd.read_sql(f"SELECT * FROM customers WHERE phone='{query}'", conn)
            if not cust.empty:
                st.write(f"**Customer Name:** {cust.iloc[0]['name']}")
                st.subheader("Batteries Currently Owned")
                owned = pd.read_sql(f"SELECT * FROM batteries WHERE current_owner_phone='{query}'", conn)
                st.dataframe(owned)
                in_shop = owned[owned['status'].isin(['pending', 'ready_for_pickup'])]
                if not in_shop.empty:
                    st.subheader("Process Pickup")
                    pick_serial = st.selectbox("Select Item in Shop", in_shop['serial_no'].tolist())
                    if st.button(f"Send Pickup OTP to {query}"):
                        otp = generate_otp()
                        st.session_state.current_otp = otp
                        st.session_state.temp_phone = query
                        st.session_state.temp_pickup_serial = pick_serial
                        st.session_state.workflow = "HISTORY_PICKUP"
                        send_otp_simulation(query, otp)
                st.subheader("Exchange Logs")
                history = pd.read_sql(f"SELECT * FROM exchanges WHERE customer_phone='{query}'", conn)
                st.dataframe(history)
            else:
                st.warning("Customer not found.")

        if st.session_state.get('current_otp') and st.session_state.get('workflow') == "HISTORY_PICKUP":
            h_otp = st.text_input("Enter OTP to Confirm Customer Pickup", key="history_otp_input")
            if st.button("Finalize Customer Pickup"):
                if h_otp == st.session_state.current_otp:
                    if process_pickup_db(st.session_state.temp_pickup_serial, st.session_state.temp_phone):
                        st.success("Battery marked as 'Picked up by Customer'.")
                        st.session_state.current_otp = None
                        st.session_state.workflow = None
                        st.rerun()
                else:
                    st.error("Incorrect OTP.")
        conn.close()


def page_inventory():
    st.title("📦 Quick Inventory Add")
    with st.form("add_stock"):
        serial = st.text_input("Serial Number")
        model = st.selectbox("Model", ["Exide Mileage", "Exide Matrix", "Exide Eezy", "Exide Gold"])
        submit = st.form_submit_button("Add to Stock")
        if submit and serial:
            conn = get_db_connection()
            try:
                c = conn.cursor()
                c.execute('''INSERT INTO batteries (serial_no, model_type, status)
                             VALUES (?, ?, 'in_stock')''', (serial, model))
                conn.commit()
                st.success(f"Battery {serial} added to stock.")
            except sqlite3.IntegrityError:
                st.error("Battery with this serial number already exists.")
            finally:
                conn.close()


def main():
    """Main function to run the Streamlit app."""
    st.set_page_config(page_title="Exide Warranty System", page_icon="🔋")
    init_db()
    cleanup_expired_data()
    st.sidebar.title(SHOP_NAME)
    menu = st.sidebar.radio("Menu", ["Dashboard", "Service", "Search History", "Add Inventory"])
    if menu == "Dashboard":
        page_dashboard()
    elif menu == "Service":
        page_service()
    elif menu == "Search History":
        page_history()
    elif menu == "Add Inventory":
        page_inventory()


if __name__ == "__main__":
    main()