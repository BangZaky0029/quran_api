from fastapi import FastAPI
from app.database.database import create_database
from app.auth.routes import auth_router, router as profile_router  # Import kedua router
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# Buat database saat pertama kali aplikasi berjalan
create_database()

# Register router untuk authentication
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(profile_router, tags=["profile"])  # Daftarkan router untuk profil

# Mount static files untuk mengakses gambar profil
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return {"message": "Aplikasi berjalan"}
