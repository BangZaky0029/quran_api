# backend/app/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Menambahkan port 8889 dan socket path ke URL koneksi
DATABASE_URL = (
    "mysql+pymysql://root:root@127.0.0.1:8889/alquran_db"
    "?unix_socket=/Applications/MAMP/tmp/mysql/mysql.sock"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def create_database():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
