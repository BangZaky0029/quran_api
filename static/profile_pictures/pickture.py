from fastapi.staticfiles import StaticFiles
from flask import app

app.mount("/static", StaticFiles(directory="static"), name="static")
