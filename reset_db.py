from database import init_db, get_db_engine
from models import Base

def reset_database():
    """
    Completely removes the existing database schema and recreates it.
    This action is irreversible and clears all customer, battery, and exchange data.
    """
    engine = get_db_engine()
    
    try:
        print("Dropping all tables...")
        Base.metadata.drop_all(engine)
        print("Tables dropped.")
        
        print("Re-initializing database...")
        init_db()
        print("Database reset complete. All data has been cleared.")
        
    except Exception as e:
        print(f"An error occurred during reset: {e}")

if __name__ == "__main__":
    confirm = input("WARNING: This will delete ALL data in the warranty system. Type 'RESET' to confirm: ")
    if confirm == "RESET":
        reset_database()
    else:
        print("Reset cancelled.")
