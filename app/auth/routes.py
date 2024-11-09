import random
import string
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from .models import User, OTP  # Pastikan model sudah disesuaikan
from ..database import SessionLocal
from datetime import datetime, timedelta
from passlib.context import CryptContext
from typing import List
import requests

# Konfigurasi Fonnte
FONNTE_API_TOKEN = "BiVebeXVbCZuBt6j4L5K"  # Ganti dengan token Fonnte Anda

auth_router = APIRouter()

# Skema untuk Register, Login, Verifikasi OTP, dan Profil User
class UserRegisterRequest(BaseModel):
    email: EmailStr
    phone_number: str
    password: str
    user_name: str

class OTPVerificationRequest(BaseModel):
    phone_number: str
    otp: str
    email: EmailStr

class ResendOtpRequest(BaseModel):
    phone_number: str

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserProfileResponse(BaseModel):
    user_name: str
    email: EmailStr
    phone_number: str

# Dependency untuk mendapatkan session database
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Password hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# Fungsi untuk memformat nomor telepon
def format_phone_number(phone_number: str) -> str:
    phone_number = ''.join(filter(str.isdigit, phone_number))
    if phone_number.startswith("0"):
        phone_number = "62" + phone_number[1:]
    elif not phone_number.startswith("62"):
        raise ValueError("Nomor telepon harus dimulai dengan 0 atau 62")
    return phone_number

# Fungsi untuk mengirim OTP ke WhatsApp menggunakan API Fonnte
def send_otp_via_whatsapp(phone_number: str, otp: str):
    url = "https://api.fonnte.com/send"
    headers = {
        "Authorization": FONNTE_API_TOKEN,
    }
    data = {
        "target": phone_number,
        "message": f"Kode OTP Anda adalah: {otp}",
        "countryCode": "62",  # Kode negara Indonesia
    }
    response = requests.post(url, headers=headers, data=data)
    if response.status_code != 200:
        raise Exception(f"Gagal mengirim OTP via WhatsApp: {response.text}")

# Endpoint untuk registrasi user baru dan mengirim OTP
@auth_router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user: UserRegisterRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    try:
        user.phone_number = format_phone_number(user.phone_number)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    db_user = db.query(User).filter((User.email == user.email) | (User.phone_number == user.phone_number)).first()
    if db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email atau nomor telepon sudah terdaftar")

    # Hash password yang diinput oleh user dan simpan di database
    hashed_password = get_password_hash(user.password)
    
    # Generate OTP
    otp_code = ''.join(random.choices(string.digits, k=6))
    expires_at = datetime.utcnow() + timedelta(minutes=5)

    # Cek jika sudah ada OTP untuk phone_number, update jika ada, insert jika tidak ada
    otp_entry = db.query(OTP).filter(OTP.phone_number == user.phone_number).first()
    if otp_entry:
        otp_entry.otp_code = otp_code
        otp_entry.expires_at = expires_at
        otp_entry.email = user.email
    else:
        otp_entry = OTP(phone_number=user.phone_number, otp_code=otp_code, email=user.email, expires_at=expires_at)
        db.add(otp_entry)

    # Simpan data user di database
    new_user = User(email=user.email, phone_number=user.phone_number, password=hashed_password, user_name=user.user_name)
    db.add(new_user)

    db.commit()

    # Send OTP
    try:
        background_tasks.add_task(send_otp_via_whatsapp, user.phone_number, otp_code)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Gagal mengirim OTP via WhatsApp: {e}")

    return {"message": "OTP telah dikirim ke WhatsApp Anda. Silakan verifikasi untuk menyelesaikan pendaftaran."}

# Endpoint untuk verifikasi OTP
@auth_router.post("/verify-otp", status_code=status.HTTP_200_OK)
async def verify_otp(request: OTPVerificationRequest, db: Session = Depends(get_db)):
    formatted_phone_number = format_phone_number(request.phone_number)
    otp_entry = db.query(OTP).filter(
        OTP.phone_number == formatted_phone_number,
        OTP.email == request.email
    ).first()

    if not otp_entry:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP tidak ditemukan atau email tidak cocok.")

    if otp_entry.otp_code != request.otp or otp_entry.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP tidak valid atau telah kedaluwarsa")

    # Hapus OTP setelah verifikasi
    db.delete(otp_entry)
    db.commit()

    return {"message": "Verifikasi OTP berhasil dan pengguna terdaftar"}

# Endpoint untuk mengirim ulang OTP
@auth_router.post("/resend-otp", status_code=status.HTTP_200_OK)
async def resend_otp(request: ResendOtpRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    formatted_phone_number = format_phone_number(request.phone_number)
    otp_entry = db.query(OTP).filter(OTP.phone_number == formatted_phone_number).first()

    if not otp_entry:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nomor telepon tidak ditemukan. Silakan daftar terlebih dahulu.")
    
    # Generate OTP baru
    otp_code = ''.join(random.choices(string.digits, k=6))
    otp_entry.otp_code = otp_code
    otp_entry.expires_at = datetime.utcnow() + timedelta(minutes=5)

    db.commit()

    try:
        background_tasks.add_task(send_otp_via_whatsapp, formatted_phone_number, otp_code)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Gagal mengirim ulang OTP: {e}")

    return {"message": "OTP telah dikirim ulang ke WhatsApp Anda"}

# Endpoint untuk login
@auth_router.post("/login", status_code=status.HTTP_200_OK)
async def login(user: UserLoginRequest, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email tidak terdaftar")

    # Verifikasi password
    if not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password salah")

    return {
        "message": "Login berhasil",
        "user_name": db_user.user_name,
        "email": db_user.email,
        "phone_number": db_user.phone_number
    }
