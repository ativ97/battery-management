from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from config import get_db_url
import streamlit as st

Base = declarative_base()

def get_db_engine():
    db_url = get_db_url()
    if not db_url:
        st.error("Missing DB_URL in Streamlit Secrets!")
        st.stop()
    return create_engine(db_url)

def get_session():
    engine = get_db_engine()
    Session = sessionmaker(bind=engine)
    return Session()

def init_db():
    engine = get_db_engine()
    Base.metadata.create_all(engine)
