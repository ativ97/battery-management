import streamlit as st

def get_db_url():
    return st.secrets.get("DB_URL")

def get_admin_credentials():
    return st.secrets.get("ADMIN_USER", "admin"), st.secrets.get("ADMIN_PASSWORD", "exide23")

SHOP_NAME = "EXIDE CARE VIKAS 23"
