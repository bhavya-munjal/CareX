from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from app.database.db import engine
from app.models.models import Base
from app.routes import auth, user, chat, admin, doctor, appointments
import os
from dotenv import load_dotenv

load_dotenv()
Base.metadata.create_all(bind=engine)

app = FastAPI(title="CareX", docs_url=None, redoc_url=None)
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "carebot-secret-change-me"))
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(auth.router)
app.include_router(user.router)
app.include_router(chat.router)
app.include_router(admin.router)
app.include_router(doctor.router)
app.include_router(appointments.router)
