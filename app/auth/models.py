from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from ..database.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    phone_number = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    user_name = Column(String, nullable=False)
    picture = Column(String, nullable=True)  # Kolom baru untuk gambar profil


class OTP(Base):
    __tablename__ = "otps"
    phone_number = Column(String, primary_key=True, index=True)
    otp_code = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    email = Column(String, nullable=False)
