from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from ..database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    phone_number = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    user_name = Column(String, nullable=False)  # Menambahkan kolom user_name

    def __init__(self, email: str, phone_number: str, password: str, user_name: str):
        self.email = email
        self.phone_number = phone_number
        self.password = password
        self.user_name = user_name  # Set user_name sebagai atribut


class OTP(Base):
    __tablename__ = "otps"
    phone_number = Column(String, primary_key=True, index=True)
    otp_code = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    email = Column(String, nullable=False)  # Menambahkan kolom email

    def __init__(self, phone_number: str, otp_code: str, email: str, expires_at: datetime):
        self.phone_number = phone_number
        self.otp_code = otp_code
        self.email = email
        self.expires_at = expires_at  # Set expires_at sebagai atribut
