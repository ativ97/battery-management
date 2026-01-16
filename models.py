from sqlalchemy import Column, String, Integer, Text, Boolean
from database import Base

class Customer(Base):
    __tablename__ = 'customers'
    phone = Column(Text, primary_key=True)
    name = Column(Text)
    created_at = Column(Text)

class Battery(Base):
    __tablename__ = 'batteries'
    serial_no = Column(Text, primary_key=True)
    model_type = Column(Text)
    status = Column(Text)
    sold_date = Column(Text)
    date_of_purchase = Column(Text)
    warranty_expiry = Column(Text)
    current_owner_phone = Column(Text)
    ticket_id = Column(Text)
    vehicle_no = Column(Text)
    # Removed complex loaner tracking, kept simple flag on the battery being serviced
    has_loaner = Column(Boolean, default=False)

class Exchange(Base):
    __tablename__ = 'exchanges'
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Text)
    old_battery_serial = Column(Text)
    new_battery_serial = Column(Text)
    customer_phone = Column(Text)
    action_taken = Column(Text)
    notes = Column(Text)

class ScrapBattery(Base):
    __tablename__ = 'scrap_batteries'
    serial_no = Column(Text, primary_key=True)
    model_type = Column(Text)
    received_date = Column(Text)
    customer_phone = Column(Text)
    ticket_id = Column(Text)
    notes = Column(Text)

class ChallanBattery(Base):
    __tablename__ = 'challan_batteries'
    serial_no = Column(Text, primary_key=True)
    model_type = Column(Text)
    received_date = Column(Text)
    customer_phone = Column(Text)
    ticket_id = Column(Text)
    notes = Column(Text)
    challan_date = Column(Text)

class ArchivedScrapBattery(Base):
    __tablename__ = 'audit_scrap_batteries'
    serial_no = Column(Text, primary_key=True)
    model_type = Column(Text)
    received_date = Column(Text)
    customer_phone = Column(Text)
    ticket_id = Column(Text)
    notes = Column(Text)
    challan_date = Column(Text)
    final_archived_date = Column(Text)
