import streamlit as st
import pandas as pd
from datetime import datetime
from config import SHOP_NAME
from auth import check_login
from database import init_db
from services import (
    calculate_age, generate_otp, send_otp_simulation,
    get_battery_by_serial, update_battery_status,
    process_new_battery_exchange, process_service_entry,
    process_return_to_customer, process_stock_reception,
    upsert_battery, get_dashboard_stats, get_batteries_in_service,
    get_recent_exchanges_df, get_ready_for_pickup_items_df,
    get_battery_details_df, get_battery_exchanges_df,
    get_customer_details_df, get_customer_batteries_df,
    get_customer_exchanges_df, add_inventory_stock,
    get_pending_factory_stock_df, get_stock_receipt_history_df,
    get_customer_by_phone, get_scrap_batteries_df,
    move_scrap_to_challan, get_challan_batteries_df, clear_challan_to_archive
)
import streamlit.components.v1 as components

# --- CONSTANTS ---
BATTERY_MODELS = [
    "Exide Mileage", "Exide Matrix", "Exide Eezy", "Exide Gold",
    "Exide Epiq", "Exide Express", "Exide Drive", "Exide Eko",
    "Exide Ride", "Exide Xplore"
]

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


# --- PAGE COMPONENTS ---
def page_dashboard():
    st.title(f"🔋 {SHOP_NAME} Dashboard")
    
    stats = get_dashboard_stats()
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Customers", stats["total_customers"])
    col2.metric("Active Batteries (Replaced)", stats["batteries_replaced"])
    col3.metric("Total Services/Exchanges", stats["exchanges_done"])

    st.markdown("---")
    st.subheader("🛠️ Active Service Management")
    
    in_service = get_batteries_in_service()
    
    if in_service:
        # Summary Table
        data = []
        for b in in_service:
            data.append({
                "Serial No": b.serial_no,
                "Ticket ID": b.ticket_id,
                "Vehicle No": b.vehicle_no,
                "Status": b.status.upper(),
                "Purchase Date": b.date_of_purchase,
                "Age": calculate_age(b.date_of_purchase),
                "Loaner": "YES" if b.has_loaner else "No"
            })
        df_active = pd.DataFrame(data)
        st.dataframe(df_active, use_container_width=True)

        for battery in in_service:
            age_info = calculate_age(battery.date_of_purchase)
            loaner_badge = " | 🔴 HAS LOANER" if battery.has_loaner else ""
            with st.expander(
                    f"Battery: {battery.serial_no} | Vehicle: {battery.vehicle_no or 'N/A'} | Status: {battery.status.upper()}{loaner_badge}"):
                st.write(f"**Ticket ID:** {battery.ticket_id or 'N/A'}")
                st.write(f"**Age since Purchase:** {age_info}")
                if battery.has_loaner:
                    st.warning("⚠️ This customer has a temporary loaner battery.")

                status_options = ['pending', 'ready_for_pickup', 'returned_faulty', 'issue_replacement']
                
                # Determine current index, default to 0 if not found or if status is something else
                current_index = 0
                if battery.status in status_options:
                    current_index = status_options.index(battery.status)
                
                new_status = st.selectbox(
                    f"Update status for {battery.serial_no}",
                    status_options,
                    index=current_index,
                    key=f"status_{battery.serial_no}"
                )

                if new_status == 'issue_replacement':
                    if st.button(f"Proceed to Replacement for {battery.serial_no}", key=f"btn_replace_{battery.serial_no}"):
                        # Set session state variables to pre-fill the service page
                        st.session_state.prefill_service = True
                        st.session_state.prefill_old_serial = battery.serial_no
                        st.session_state.prefill_phone = battery.current_owner_phone
                        st.session_state.intent_issue_replacement = True
                        # Redirect to Service page
                        st.session_state.menu_selection = "Service"
                        st.rerun()
                elif new_status != battery.status:
                    if st.button(f"Save Status for {battery.serial_no}", key=f"btn_{battery.serial_no}"):
                        update_battery_status(battery.serial_no, new_status)
                        st.success(f"Status updated to {new_status}!")
                        st.rerun()
    else:
        st.info("No batteries currently pending or ready for pickup.")

    st.markdown("---")
    st.subheader("Recent Service History")
    recent = get_recent_exchanges_df()
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
            components.html(html_receipt, height=500, scrolling=True)

            col_p1, col_p2 = st.columns(2)
            with col_p1:
                if st.button("🖨️ Print Receipt"):
                    components.html(f"""
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
                # Clear all temp data
                keys_to_clear = ['temp_cust_name', 'temp_vehicle_no', 'intent_issue_replacement']
                for k in keys_to_clear:
                    if k in st.session_state:
                        del st.session_state[k]
                st.rerun()
            return

        st.subheader("1. Register Faulty Battery")

        # Check for pre-fill data from dashboard redirection
        default_phone = ""
        default_old_serial = ""
        if st.session_state.get("prefill_service"):
            default_phone = st.session_state.get("prefill_phone", "")
            default_old_serial = st.session_state.get("prefill_old_serial", "")

        with st.form("check_form"):
            col1, col2 = st.columns(2)
            phone = col1.text_input("Customer Phone Number", value=default_phone, max_chars=10)
            old_serial = col2.text_input("Faulty Battery Serial No.", value=default_old_serial)
            check_submit = st.form_submit_button("Verify Details & Send OTP")

        if check_submit:
            if len(phone) < 10 or not old_serial:
                st.error("Please enter valid Phone and Serial Number.")
            else:
                batt = get_battery_by_serial(old_serial)

                valid_warranty = True
                if batt:
                    expiry = batt.warranty_expiry
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
                    
                    # Fetch details for pre-filling next stage
                    cust = get_customer_by_phone(phone)
                    st.session_state.temp_cust_name = cust.name if cust else ""
                    st.session_state.temp_vehicle_no = batt.vehicle_no if batt and batt.vehicle_no else ""
                    
                    send_otp_simulation(phone, otp)
                    st.info("OTP sent to customer's phone.")
                    
                    # Clear prefill data after successful submission
                    if st.session_state.get("prefill_service"):
                        st.session_state.prefill_service = False
                        st.session_state.prefill_phone = ""
                        st.session_state.prefill_old_serial = ""

        if st.session_state.current_otp and not st.session_state.otp_verified and st.session_state.get(
                'workflow') == "CLAIM":
            st.text_input("Enter OTP for Warranty Claim", key="claim_otp_input")
            st.button("Verify OTP", key="claim_verify_btn", on_click=verify_claim_otp)

        if st.session_state.otp_verified and st.session_state.get('workflow') == "CLAIM":
            st.subheader("Resolution")
            
            # Determine default selection based on intent
            res_index = 0
            if st.session_state.get("intent_issue_replacement"):
                res_index = 1
                
            action = st.radio("Select Resolution:",
                              ["Keep for Service (Mark as Pending)", "Issue New Replacement Battery"],
                              index=res_index)

            if action == "Issue New Replacement Battery":
                with st.container(border=True):
                    col_a, col_b = st.columns(2)
                    
                    # Use temp values if available
                    val_name = st.session_state.get("temp_cust_name", "")
                    val_vehicle = st.session_state.get("temp_vehicle_no", "")
                    
                    cust_name = col_a.text_input("Customer Name", value=val_name)
                    vehicle_no = col_b.text_input("Vehicle Registration No.", value=val_vehicle)

                    col_c, col_d = st.columns(2)
                    new_serial = col_c.text_input("New Battery Serial Number")
                    ticket_id = col_d.text_input("Exide Ticket ID")

                    col_e, col_f = st.columns(2)
                    new_model = col_e.selectbox("Battery Model", BATTERY_MODELS)
                    purchase_date = col_f.date_input("Date of Purchase", value=datetime.now())
                    col_f.caption(f"Age: {calculate_age(purchase_date.strftime('%Y-%m-%d'))}")

                    notes = st.text_area("Technician Notes", "Warranty replacement issued.")
                    final_submit = st.button("Complete Exchange")

                    if final_submit:
                        if not new_serial or not ticket_id:
                            st.error("Serial and Ticket ID are mandatory.")
                        else:
                            try:
                                process_new_battery_exchange(
                                    customer_phone=st.session_state.temp_phone,
                                    customer_name=cust_name,
                                    old_serial=st.session_state.temp_old_serial,
                                    new_serial=new_serial,
                                    new_model=new_model,
                                    ticket_id=ticket_id,
                                    vehicle_no=vehicle_no,
                                    purchase_date=purchase_date,
                                    notes=notes
                                )

                                st.session_state.last_exchange_summary = {
                                    'cust_name': cust_name, 'vehicle_no': vehicle_no, 'new_serial': new_serial,
                                    'old_serial': st.session_state.temp_old_serial, 'ticket_id': ticket_id,
                                    'new_model': new_model, 'purchase_date': purchase_date.strftime("%Y-%m-%d"), 'notes': notes
                                }
                                st.session_state.exchange_complete = True
                                # Clear intent flag
                                if 'intent_issue_replacement' in st.session_state:
                                    del st.session_state.intent_issue_replacement
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
            else:
                with st.container(border=True):
                    col_x, col_y = st.columns(2)
                    
                    # Use temp values if available
                    val_name = st.session_state.get("temp_cust_name", "")
                    val_vehicle = st.session_state.get("temp_vehicle_no", "")
                    
                    cust_name = col_x.text_input("Customer Name", value=val_name)
                    ticket_id = col_y.text_input("Exide Ticket ID (If generated)")
                    col_z1, col_z2 = st.columns(2)
                    vehicle_no = col_z1.text_input("Vehicle Registration No.", value=val_vehicle)
                    purchase_date = col_z2.date_input("Date of Purchase", value=datetime.now())
                    col_z2.caption(f"Age: {calculate_age(purchase_date.strftime('%Y-%m-%d'))}")
                    
                    # --- NEW FEATURE: TEMPORARY BATTERY (SIMPLE) ---
                    st.markdown("---")
                    st.write("🔋 **Temporary Battery (Loaner)**")
                    give_loaner = st.checkbox("Issue a temporary battery to customer?")
                    
                    notes = st.text_area("Initial Observation", "Keeping for service/charging.")
                    repair_submit = st.button("Log Entry - Battery Kept for Service")

                    if repair_submit:
                        try:
                            process_service_entry(
                                customer_phone=st.session_state.temp_phone,
                                customer_name=cust_name,
                                battery_serial=st.session_state.temp_old_serial,
                                ticket_id=ticket_id,
                                vehicle_no=vehicle_no,
                                purchase_date=purchase_date,
                                notes=notes,
                                has_loaner=give_loaner
                            )
                            msg = f"Battery {st.session_state.temp_old_serial} is now marked as 'PENDING'."
                            if give_loaner:
                                msg += " (Loaner Issued)"
                            st.info(msg)
                            st.session_state.otp_verified = False
                            # Clear intent flag
                            if 'intent_issue_replacement' in st.session_state:
                                del st.session_state.intent_issue_replacement
                        except Exception as e:
                            st.error(f"Error: {e}")

    with tab_pickup:
        st.subheader("Return Battery to Customer")
        search_phone = st.text_input("Enter Customer Phone Number to Find Items", key="pickup_search_phone")
        if search_phone:
            ready_items = get_ready_for_pickup_items_df(search_phone)

            if not ready_items.empty:
                st.write("Items in service:")
                ready_items['Age'] = ready_items['date_of_purchase'].apply(calculate_age)
                # Show loaner status in table
                ready_items['Loaner'] = ready_items['has_loaner'].apply(lambda x: "YES" if x else "No")
                st.dataframe(ready_items[['serial_no', 'status', 'ticket_id', 'vehicle_no', 'Age', 'Loaner']])
                
                selected_serial = st.selectbox("Select Battery to Return", ready_items['serial_no'].tolist())
                
                # Check if selected battery has a loaner
                selected_row = ready_items[ready_items['serial_no'] == selected_serial].iloc[0]
                has_loaner = bool(selected_row['has_loaner'])
                
                return_loaner = False
                if has_loaner:
                    st.warning(f"⚠️ This service entry has a loaner battery marked.")
                    return_loaner = st.checkbox(f"Confirm return of loaner battery?", value=True)

                if st.button("Verify Customer & Send OTP for Pickup", key="pickup_send_otp"):
                    otp = generate_otp()
                    st.session_state.current_otp = otp
                    st.session_state.temp_phone = search_phone
                    st.session_state.temp_pickup_serial = selected_serial
                    st.session_state.workflow = "PICKUP"
                    st.session_state.pickup_verified = False
                    st.session_state.return_loaner_flag = return_loaner # Store this choice
                    send_otp_simulation(search_phone, otp)

                if st.session_state.current_otp and st.session_state.get('workflow') == "PICKUP":
                    st.text_input("Enter OTP for Pickup", key="pickup_otp_input")
                    if st.button("Confirm Return to Customer", key="confirm_pickup_btn", on_click=verify_pickup_otp):
                        if st.session_state.get('pickup_verified'):
                            if process_return_to_customer(
                                st.session_state.temp_pickup_serial, 
                                search_phone,
                                return_loaner=st.session_state.get('return_loaner_flag', False)
                            ):
                                st.success(f"Battery {st.session_state.temp_pickup_serial} returned successfully!")
                                if st.session_state.get('return_loaner_flag'):
                                    st.info("Loaner battery marked as returned.")
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
        if search_type == "Battery Serial Number":
            batt = get_battery_details_df(query)
            if not batt.empty:
                row = batt.iloc[0]
                st.subheader("Battery Details")
                st.write(f"**Ticket ID:** {row['ticket_id'] or 'N/A'}")
                st.write(f"**Vehicle No:** {row['vehicle_no'] or 'N/A'}")
                st.write(f"**Age since Purchase:** {calculate_age(row['date_of_purchase'])}")
                st.dataframe(batt)
                st.subheader("Service History")
                trans = get_battery_exchanges_df(query)
                st.dataframe(trans)
            else:
                st.warning("No battery found.")
        else:
            cust = get_customer_details_df(query)
            if not cust.empty:
                st.write(f"**Customer Name:** {cust.iloc[0]['name']}")
                st.subheader("Batteries Owned")
                owned = get_customer_batteries_df(query)
                if not owned.empty:
                    owned['Age'] = owned['date_of_purchase'].apply(calculate_age)
                    st.dataframe(owned[['serial_no', 'model_type', 'status', 'ticket_id', 'vehicle_no', 'Age']])
                st.subheader("Exchange Logs")
                history = get_customer_exchanges_df(query)
                st.dataframe(history)
            else:
                st.warning("Customer not found.")


def page_inventory():
    st.title("📦 Quick Inventory Add")
    with st.form("add_stock"):
        serial = st.text_input("Serial Number")
        model = st.selectbox("Model", BATTERY_MODELS)
        p_date = st.date_input("Date of Purchase (If pre-owned/return)", value=datetime.now())
        submit = st.form_submit_button("Add to Stock")
        if submit and serial:
            try:
                add_inventory_stock(serial, model, p_date)
                st.success(f"Battery {serial} added. Age: {calculate_age(p_date.strftime('%Y-%m-%d'))}")
            except Exception as e:
                st.error(f"Error: {e}")


def page_stock_loan_exide():
    st.title("🏭 Stock Loan Exide")
    with st.form("add_stock_loan"):
        st.subheader("New Stock Request / Loan")
        serial = st.text_input("Serial Number")
        model = st.selectbox("Battery Model", BATTERY_MODELS)
        ticket_id = st.text_input("Ticket ID")
        req_date = st.date_input("Date", value=datetime.now())
        submit = st.form_submit_button("Add to Pending Stock")
        if submit:
            if not serial:
                st.error("Serial Number is required")
            else:
                try:
                    upsert_battery(
                        serial=serial,
                        model=model,
                        status='factory_pending',
                        sold_date=None,
                        p_date=req_date.strftime("%Y-%m-%d"),
                        phone=None,
                        ticket=ticket_id,
                        vehicle=None
                    )
                    st.success(f"Added {serial} to pending list.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    st.markdown("---")
    st.subheader("⏳ Pending Stock from Exide Factory")
    pending_stock = get_pending_factory_stock_df()

    if not pending_stock.empty:
        for index, row in pending_stock.iterrows():
            col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 2])
            with col1:
                st.write(f"**SN:** {row['serial_no']}")
            with col2:
                st.write(f"**Model:** {row['model_type']}")
            with col3:
                st.write(f"**Ticket:** {row['ticket_id']}")
            with col4:
                st.write(f"**Date:** {row['date_of_purchase']}")
            with col5:
                if st.button("Mark Received", key=f"recv_{row['serial_no']}"):
                    process_stock_reception(row['serial_no'], row['model_type'])
                    st.success(f"Stock {row['serial_no']} received!")
                    st.rerun()
    else:
        st.info("No pending stock from factory.")

    st.markdown("---")
    st.subheader("📜 Received Stock History (Audit)")
    audit_log = get_stock_receipt_history_df()
    if not audit_log.empty:
        st.dataframe(audit_log, use_container_width=True)
    else:
        st.info("No stock receipt history found.")

def page_scrap_batteries():
    st.title("♻️ Scrap Batteries")
    st.subheader("List of Scrap Batteries (Replaced)")
    scrap_df = get_scrap_batteries_df()
    
    if not scrap_df.empty:
        # Insert a boolean column for selection
        scrap_df.insert(0, "Select", False)
        
        # Configure the editor to show checkboxes and disable editing other columns
        edited_df = st.data_editor(
            scrap_df,
            column_config={
                "Select": st.column_config.CheckboxColumn(
                    "Add to Challan?",
                    help="Select to move to challan",
                    default=False,
                )
            },
            disabled=[c for c in scrap_df.columns if c != "Select"],
            hide_index=True,
            use_container_width=True,
            key="scrap_editor"
        )
        
        selected_rows = edited_df[edited_df["Select"]]
        
        if not selected_rows.empty:
            st.write(f"Selected {len(selected_rows)} items.")
            if st.button("📦 Move Selected to Challan"):
                serials_to_move = selected_rows['serial_no'].tolist()
                if move_scrap_to_challan(serials_to_move):
                    st.success(f"Successfully moved {len(serials_to_move)} batteries to Challan.")
                    st.rerun()
                else:
                    st.error("Failed to move batteries.")
    else:
        st.info("No scrap batteries found.")

def page_chalaan():
    st.title("📜 Challan")
    st.subheader("Challan List")
    
    challan_df = get_challan_batteries_df()
    if not challan_df.empty:
        st.dataframe(challan_df, use_container_width=True)
        
        st.markdown("---")
        if st.button("🗑️ Clear Challan (Move to Audit)"):
            if clear_challan_to_archive():
                st.success("Challan cleared successfully! Records moved to audit.")
                st.rerun()
            else:
                st.error("Failed to clear challan.")
    else:
        st.info("No batteries in Challan.")

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

    # Handle menu selection redirection
    # We check if a redirection is requested
    if st.session_state.get("menu_selection"):
        # We update the session state variable that the radio button is bound to
        st.session_state.sidebar_menu = st.session_state.menu_selection
        # Clear the trigger
        st.session_state.menu_selection = None

    # Initialize the sidebar_menu state if not present
    if "sidebar_menu" not in st.session_state:
        st.session_state.sidebar_menu = "Dashboard"

    menu = st.sidebar.radio("Menu", ["Dashboard", "Service", "Search History", "Stock Loan Exide", "Scrap Batteries/Trnf", "Challan"], key="sidebar_menu")

    if menu == "Dashboard":
        page_dashboard()
    elif menu == "Service":
        page_service()
    elif menu == "Search History":
        page_history()
    elif menu == "Stock Loan Exide":
        page_stock_loan_exide()
    elif menu == "Scrap Batteries/Trnf":
        page_scrap_batteries()
    elif menu == "Challan":
        page_chalaan()
    #elif menu == "Add Inventory":
     #   page_inventory()


if __name__ == "__main__":
    main()