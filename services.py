from datetime import datetime
import random
import time
import streamlit as st
import pandas as pd
from database import get_session
from models import Customer, Battery, Exchange

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
    except ValueError:
        return "Invalid Date"

def generate_otp():
    return str(random.randint(1000, 9999))

def send_otp_simulation(phone, otp):
    with st.spinner(f"Sending OTP to {phone}..."):
        time.sleep(1)
    st.toast(f"🔔 SMS SENT: Your OTP is {otp}", icon="📱")
    return True

# --- READ OPERATIONS ---

def get_dashboard_stats():
    session = get_session()
    try:
        total_customers = session.query(Customer).count()
        batteries_replaced = session.query(Battery).filter_by(status='replaced').count()
        exchanges_done = session.query(Exchange).count()
        return {
            "total_customers": total_customers,
            "batteries_replaced": batteries_replaced,
            "exchanges_done": exchanges_done
        }
    finally:
        session.close()

def get_batteries_in_service():
    session = get_session()
    try:
        # Return list of objects. Since we query all, they are loaded.
        # We need to be careful about detachment if we try to refresh them, but for read it's fine.
        return session.query(Battery).filter(Battery.status.in_(['pending', 'ready_for_pickup'])).all()
    finally:
        session.close()

def get_recent_exchanges_df(limit=5):
    session = get_session()
    try:
        query = session.query(Exchange).order_by(Exchange.id.desc()).limit(limit).statement
        return pd.read_sql(query, session.bind)
    finally:
        session.close()

def get_battery_by_serial(serial):
    session = get_session()
    try:
        return session.query(Battery).filter_by(serial_no=serial).first()
    finally:
        session.close()

def get_battery_details_df(serial):
    session = get_session()
    try:
        query = session.query(Battery).filter_by(serial_no=serial).statement
        return pd.read_sql(query, session.bind)
    finally:
        session.close()

def get_battery_exchanges_df(serial):
    session = get_session()
    try:
        query = session.query(Exchange).filter((Exchange.old_battery_serial == serial) | (Exchange.new_battery_serial == serial)).statement
        return pd.read_sql(query, session.bind)
    finally:
        session.close()

def get_customer_by_phone(phone):
    session = get_session()
    try:
        return session.query(Customer).filter_by(phone=phone).first()
    finally:
        session.close()

def get_customer_details_df(phone):
    session = get_session()
    try:
        query = session.query(Customer).filter_by(phone=phone).statement
        return pd.read_sql(query, session.bind)
    finally:
        session.close()

def get_customer_batteries_df(phone):
    session = get_session()
    try:
        query = session.query(Battery).filter_by(current_owner_phone=phone).statement
        return pd.read_sql(query, session.bind)
    finally:
        session.close()

def get_customer_exchanges_df(phone):
    session = get_session()
    try:
        query = session.query(Exchange).filter_by(customer_phone=phone).statement
        return pd.read_sql(query, session.bind)
    finally:
        session.close()

def get_ready_for_pickup_items_df(phone):
    session = get_session()
    try:
        query = session.query(Battery.serial_no, Battery.model_type, Battery.status, Battery.ticket_id, Battery.vehicle_no, Battery.date_of_purchase)\
            .filter(Battery.current_owner_phone == phone)\
            .filter(Battery.status.in_(['ready_for_pickup', 'pending']))\
            .statement
        return pd.read_sql(query, session.bind)
    finally:
        session.close()

def get_pending_factory_stock_df():
    session = get_session()
    try:
        query = session.query(Battery).filter_by(status='factory_pending').statement
        return pd.read_sql(query, session.bind)
    finally:
        session.close()

def get_stock_receipt_history_df():
    session = get_session()
    try:
        query = session.query(Exchange.date.label("Received Date"), Exchange.old_battery_serial.label("Serial No"), Exchange.notes.label("Details"))\
            .filter_by(action_taken='STOCK_RECEIVED')\
            .order_by(Exchange.id.desc())\
            .statement
        return pd.read_sql(query, session.bind)
    finally:
        session.close()

# --- WRITE OPERATIONS ---

def update_battery_status(serial, status):
    session = get_session()
    try:
        battery = session.query(Battery).filter_by(serial_no=serial).first()
        if battery:
            battery.status = status
            session.commit()
            return True
        return False
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def process_new_battery_exchange(customer_phone, customer_name, old_serial, new_serial, new_model, ticket_id, vehicle_no, purchase_date, notes):
    session = get_session()
    try:
        # 1. Upsert Customer
        customer = session.query(Customer).filter_by(phone=customer_phone).first()
        if customer:
            customer.name = customer_name
        else:
            customer = Customer(phone=customer_phone, name=customer_name, created_at=datetime.now().strftime("%Y-%m-%d"))
            session.add(customer)
        
        # 2. Update Old Battery
        old_battery = session.query(Battery).filter_by(serial_no=old_serial).first()
        if old_battery:
            old_battery.status = 'returned_faulty'
        
        # 3. Upsert New Battery
        p_date_str = purchase_date.strftime("%Y-%m-%d")
        new_battery = session.query(Battery).filter_by(serial_no=new_serial).first()
        if new_battery:
            new_battery.status = 'sold'
            new_battery.ticket_id = ticket_id
            new_battery.current_owner_phone = customer_phone
            new_battery.vehicle_no = vehicle_no
            new_battery.date_of_purchase = p_date_str
        else:
            new_battery = Battery(
                serial_no=new_serial,
                model_type=new_model,
                status='sold',
                sold_date=datetime.now().strftime("%Y-%m-%d"),
                date_of_purchase=p_date_str,
                current_owner_phone=customer_phone,
                ticket_id=ticket_id,
                vehicle_no=vehicle_no
            )
            session.add(new_battery)
            
        # 4. Create Exchange Record
        exchange = Exchange(
            date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            old_battery_serial=old_serial,
            new_battery_serial=new_serial,
            customer_phone=customer_phone,
            action_taken='NEW_REPLACEMENT_ISSUED',
            notes=f"Ticket: {ticket_id}. {notes}"
        )
        session.add(exchange)
        
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def process_service_entry(customer_phone, customer_name, battery_serial, ticket_id, vehicle_no, purchase_date, notes):
    session = get_session()
    try:
        # 1. Upsert Customer
        customer = session.query(Customer).filter_by(phone=customer_phone).first()
        if customer:
            customer.name = customer_name
        else:
            customer = Customer(phone=customer_phone, name=customer_name, created_at=datetime.now().strftime("%Y-%m-%d"))
            session.add(customer)

        # 2. Upsert Battery (Pending)
        p_date_str = purchase_date.strftime("%Y-%m-%d")
        battery = session.query(Battery).filter_by(serial_no=battery_serial).first()
        if battery:
            battery.status = 'pending'
            battery.current_owner_phone = customer_phone
            battery.ticket_id = ticket_id
            battery.vehicle_no = vehicle_no
            battery.date_of_purchase = p_date_str
        else:
             battery = Battery(
                serial_no=battery_serial,
                status='pending',
                current_owner_phone=customer_phone,
                ticket_id=ticket_id,
                vehicle_no=vehicle_no,
                date_of_purchase=p_date_str
            )
             session.add(battery)

        # 3. Exchange Record
        exchange = Exchange(
            date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            old_battery_serial=battery_serial,
            new_battery_serial=battery_serial,
            customer_phone=customer_phone,
            action_taken='SERVICE_PENDING',
            notes=f"Ticket: {ticket_id}. {notes}"
        )
        session.add(exchange)
        
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def process_return_to_customer(serial, phone):
    session = get_session()
    try:
        battery = session.query(Battery).filter_by(serial_no=serial).first()
        if battery:
            battery.status = 'active_with_customer'
        
        exchange = Exchange(
            date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            old_battery_serial=serial,
            new_battery_serial=None,
            customer_phone=phone,
            action_taken="RETURNED_TO_CUSTOMER",
            notes="Service completed, battery returned."
        )
        session.add(exchange)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def process_stock_reception(serial, model):
    session = get_session()
    try:
        battery = session.query(Battery).filter_by(serial_no=serial).first()
        if battery:
            battery.status = 'in_stock'
        
        exchange = Exchange(
            date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            old_battery_serial=serial,
            new_battery_serial=None,
            customer_phone='EXIDE_FACTORY',
            action_taken='STOCK_RECEIVED',
            notes=f"Received stock: {model}"
        )
        session.add(exchange)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def upsert_battery(serial, model, status, sold_date, p_date, phone, ticket, vehicle):
    session = get_session()
    try:
        battery = session.query(Battery).filter_by(serial_no=serial).first()
        if battery:
            battery.status = status
            battery.ticket_id = ticket
            battery.current_owner_phone = phone
            battery.vehicle_no = vehicle
            if p_date:
                battery.date_of_purchase = p_date
        else:
            battery = Battery(
                serial_no=serial,
                model_type=model,
                status=status,
                sold_date=sold_date,
                date_of_purchase=p_date,
                current_owner_phone=phone,
                ticket_id=ticket,
                vehicle_no=vehicle
            )
            session.add(battery)
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def add_inventory_stock(serial, model, p_date):
    session = get_session()
    try:
        battery = Battery(
            serial_no=serial,
            model_type=model,
            status='in_stock',
            date_of_purchase=p_date.strftime("%Y-%m-%d")
        )
        session.add(battery)
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()
