import os
import shutil
from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, File, status, BackgroundTasks
from sqlalchemy.orm import Session
from auth.schemas import UserRegisterRequest, OTPVerificationRequest, ResendOtpRequest, UserLoginRequest, UserProfileResponse
from auth.utils import format_phone_number, get_password_hash, verify_password, send_otp_via_whatsapp
from app.auth.models import User, OTP
from app.database.database import get_db
from datetime import datetime, timedelta
import random, string

auth_router = APIRouter()
router = APIRouter()

@auth_router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user: UserRegisterRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    try:
        user.phone_number = format_phone_number(user.phone_number)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Cek apakah email atau nomor telepon sudah terdaftar
    db_user = db.query(User).filter(
        (User.email == user.email) | (User.phone_number == user.phone_number)
    ).first()
    if db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email atau nomor telepon sudah terdaftar")

    # Hash password dan buat OTP
    hashed_password = get_password_hash(user.password)
    otp_code = ''.join(random.choices(string.digits, k=6))
    expires_at = datetime.utcnow() + timedelta(minutes=5)

    # Simpan atau perbarui OTP di database
    otp_entry = db.query(OTP).filter(OTP.phone_number == user.phone_number).first()
    if otp_entry:
        otp_entry.otp_code = otp_code
        otp_entry.expires_at = expires_at
        otp_entry.email = user.email
    else:
        otp_entry = OTP(phone_number=user.phone_number, otp_code=otp_code, email=user.email, expires_at=expires_at)
        db.add(otp_entry)

    # Simpan pengguna baru
    new_user = User(
        email=user.email, phone_number=user.phone_number,
        password=hashed_password, user_name=user.user_name
    )
    db.add(new_user)
    db.commit()

    # Kirim OTP via WhatsApp
    background_tasks.add_task(send_otp_via_whatsapp, user.phone_number, otp_code)

    return {"message": "OTP telah dikirim ke WhatsApp Anda. Silakan verifikasi untuk menyelesaikan pendaftaran."}

@auth_router.post("/verify-otp", status_code=status.HTTP_200_OK)
async def verify_otp(request: OTPVerificationRequest, db: Session = Depends(get_db)):
    formatted_phone_number = format_phone_number(request.phone_number)
    otp_entry = db.query(OTP).filter(
        OTP.phone_number == formatted_phone_number,
        OTP.email == request.email
    ).first()

    if not otp_entry or otp_entry.otp_code != request.otp or otp_entry.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP tidak valid atau telah kedaluwarsa")

    # Hapus OTP yang sudah diverifikasi
    db.delete(otp_entry)
    db.commit()

    return {"message": "Verifikasi OTP berhasil dan pengguna terdaftar"}

@auth_router.post("/resend-otp", status_code=status.HTTP_200_OK)
async def resend_otp(request: ResendOtpRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    formatted_phone_number = format_phone_number(request.phone_number)
    otp_entry = db.query(OTP).filter(OTP.phone_number == formatted_phone_number).first()

    if not otp_entry:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nomor telepon tidak ditemukan. Silakan daftar terlebih dahulu.")
    
    # Generate OTP baru dan perbarui expiry time
    otp_code = ''.join(random.choices(string.digits, k=6))
    otp_entry.otp_code = otp_code
    otp_entry.expires_at = datetime.utcnow() + timedelta(minutes=1)
    db.commit()

    # Kirim OTP via WhatsApp
    background_tasks.add_task(send_otp_via_whatsapp, formatted_phone_number, otp_code)

    return {"message": "OTP telah dikirim ulang ke WhatsApp Anda"}

@auth_router.post("/login", status_code=status.HTTP_200_OK)
async def login(user: UserLoginRequest, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email atau password salah")

    return {
        "success": True,
        "message": "Login berhasil",
        "user_id": db_user.id,          # Pastikan untuk mengirim user_id
        "user_name": db_user.user_name,
        "email": db_user.email,
        "phone_number": db_user.phone_number
    }


# Direktori penyimpanan untuk gambar profil
PROFILE_PICTURE_DIR = "static/profile_pictures/"

@router.post("/update-profile-picture", status_code=status.HTTP_200_OK)
async def update_profile_picture(
    user_id: int = Form(...), 
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    # Periksa apakah user dengan ID tertentu ada di database
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User tidak ditemukan")
    
    # Periksa ekstensi file
    file_extension = file.filename.split(".")[-1] in ("jpg", "jpeg", "png")
    if not file_extension:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File harus berupa gambar (jpg, jpeg, png)")

    # Buat path penyimpanan file
    file_location = os.path.join(PROFILE_PICTURE_DIR, f"{user_id}_{file.filename}")
    
    # Simpan file di direktori yang sudah ditentukan
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Update kolom `picture` pada user dengan path file
    user.picture = file_location
    db.commit()
    db.refresh(user)

    return {"message": "Gambar profil berhasil diperbarui", "picture_url": file_location}