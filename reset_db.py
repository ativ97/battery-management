import sqlite3
import os

# --- CONFIGURATION ---
DB_FILE = "battery_shop.db"


def reset_database():
    """
    Completely removes the existing database file and recreates the schema.
    This action is irreversible and clears all customer, battery, and exchange data.
    """
    # 1. Check if the database file exists
    if os.path.exists(DB_FILE):
        try:
            # Attempt to delete the file
            os.remove(DB_FILE)
            print(f"Successfully deleted existing database: {DB_FILE}")
        except Exception as e:
            print(f"Error deleting database file: {e}")
            return
    else:
        print(f"No existing database found at {DB_FILE}. Creating fresh one.")

    # 2. Re-initialize the database with fresh tables
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()

        print("Creating tables...")

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

        # Battery Table
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
                         date_of_purchase
                         TEXT,
                         warranty_expiry
                         TEXT,
                         current_owner_phone
                         TEXT,
                         ticket_id
                         TEXT,
                         vehicle_no
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

        conn.commit()
        conn.close()
        print("Database reset complete. All data has been cleared.")

    except Exception as e:
        print(f"An error occurred during re-initialization: {e}")


if __name__ == "__main__":
    confirm = input("WARNING: This will delete ALL data in the warranty system. Type 'RESET' to confirm: ")
    if confirm == "RESET":
        reset_database()
    else:
        print("Reset cancelled.")