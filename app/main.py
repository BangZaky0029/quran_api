# backend/app/main.py
from fastapi import FastAPI
from .auth.routes import auth_router
from .database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(auth_router, prefix="/auth")
