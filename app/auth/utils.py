import requests
from passlib.context import CryptContext
import re
from config.settings import FONNTE_API_TOKEN

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def format_phone_number(phone_number: str) -> str:
    phone_number = ''.join(filter(str.isdigit, phone_number))
    if phone_number.startswith("0"):
        phone_number = "62" + phone_number[1:]
    elif not phone_number.startswith("62"):
        raise ValueError("Nomor telepon harus dimulai dengan 0 atau 62")
    return phone_number

def send_otp_via_whatsapp(phone_number: str, otp: str):
    url = "https://api.fonnte.com/send"
    headers = {"Authorization": FONNTE_API_TOKEN}
    data = {"target": phone_number, "message": f"Kode OTP Anda adalah: {otp}", "countryCode": "62"}
    response = requests.post(url, headers=headers, data=data)
    if response.status_code != 200:
        raise Exception(f"Gagal mengirim OTP via WhatsApp: {response.text}")
