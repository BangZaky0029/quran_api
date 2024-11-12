from pydantic import BaseModel, EmailStr

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
