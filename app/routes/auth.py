from fastapi import APIRouter, Request, Form, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from datetime import date
from app.database.db import get_db
from app.models.models import User, Admin, MedicalHistory

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_current_user(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.query(User).filter(User.id == user_id).first()

def get_current_admin(request: Request, db: Session = Depends(get_db)):
    admin_id = request.session.get("admin_id")
    if not admin_id:
        return None
    return db.query(Admin).filter(Admin.id == admin_id).first()

@router.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    return templates.TemplateResponse("landing.html", {"request": request})

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("auth/register.html", {"request": request, "error": None})

@router.post("/register")
async def register(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    dob: str = Form(...),
    gender: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db)
):
    if password != confirm_password:
        return templates.TemplateResponse("auth/register.html", {"request": request, "error": "Passwords do not match."})
    if db.query(User).filter(User.email == email).first():
        return templates.TemplateResponse("auth/register.html", {"request": request, "error": "Email already registered."})
    if len(password) < 6:
        return templates.TemplateResponse("auth/register.html", {"request": request, "error": "Password must be at least 6 characters."})

    dob_parsed = date.fromisoformat(dob) if dob else None
    user = User(
        full_name=full_name, email=email, phone=phone,
        dob=dob_parsed, gender=gender,
        password_hash=pwd_ctx.hash(password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.add(MedicalHistory(user_id=user.id))
    db.commit()
    return RedirectResponse("/login?registered=1", status_code=status.HTTP_302_FOUND)

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, registered: str = None):
    return templates.TemplateResponse("auth/login.html", {"request": request, "error": None, "registered": registered})

@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email).first()
    if not user or not pwd_ctx.verify(password, user.password_hash):
        return templates.TemplateResponse("auth/login.html", {"request": request, "error": "Invalid email or password.", "registered": None})
    request.session["user_id"] = user.id
    return RedirectResponse("/dashboard", status_code=status.HTTP_302_FOUND)

@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=status.HTTP_302_FOUND)

@router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password(request: Request):
    return templates.TemplateResponse("auth/forgot_password.html", {"request": request})

@router.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    return templates.TemplateResponse("admin/login.html", {"request": request, "error": None})

@router.post("/admin/login")
async def admin_login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    admin = db.query(Admin).filter(Admin.email == email).first()
    if not admin or not pwd_ctx.verify(password, admin.password_hash):
        return templates.TemplateResponse("admin/login.html", {"request": request, "error": "Invalid credentials."})
    request.session["admin_id"] = admin.id
    return RedirectResponse("/admin/dashboard", status_code=status.HTTP_302_FOUND)

@router.get("/admin/logout")
async def admin_logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=status.HTTP_302_FOUND)

    # request.session.pop("admin_id", None)
    # return RedirectResponse("/admin/login", status_code=status.HTTP_302_FOUND)
