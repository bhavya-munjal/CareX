from fastapi import APIRouter, Request, Form, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.models.models import User, Admin, HealthReport, ChatHistory, Doctor, BMIRecord
from app.routes.auth import get_current_admin

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="app/templates")

@router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    admin = get_current_admin(request, db)
    if not admin:
        return RedirectResponse("/admin/login", status_code=status.HTTP_302_FOUND)

    total_users = db.query(User).count()
    total_reports = db.query(HealthReport).count()
    total_chats = db.query(ChatHistory).count()

    from sqlalchemy import func
    top_users = db.query(User, func.count(ChatHistory.id).label("cnt")).join(
        ChatHistory, ChatHistory.user_id == User.id, isouter=True
    ).group_by(User.id).order_by(func.count(ChatHistory.id).desc()).limit(5).all()

    recent_reports = db.query(HealthReport).order_by(HealthReport.created_at.desc()).limit(5).all()

    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request, "admin": admin,
        "total_users": total_users,
        "total_reports": total_reports,
        "total_chats": total_chats,
        "top_users": top_users,
        "recent_reports": recent_reports,
    })

@router.get("/users", response_class=HTMLResponse)
async def admin_users(request: Request, db: Session = Depends(get_db)):
    admin = get_current_admin(request, db)
    if not admin:
        return RedirectResponse("/admin/login", status_code=status.HTTP_302_FOUND)
    from sqlalchemy import func
    users = db.query(User).order_by(User.created_at.desc()).all()
    users_data = []
    for u in users:
        chat_cnt = db.query(ChatHistory).filter(ChatHistory.user_id == u.id).count()
        report_cnt = db.query(HealthReport).filter(HealthReport.user_id == u.id).count()
        users_data.append((u, chat_cnt, report_cnt))
    return templates.TemplateResponse("admin/users.html", {"request": request, "admin": admin, "users_data": users_data})

@router.get("/reports", response_class=HTMLResponse)
async def admin_reports(request: Request, db: Session = Depends(get_db)):
    admin = get_current_admin(request, db)
    if not admin:
        return RedirectResponse("/admin/login", status_code=status.HTTP_302_FOUND)
    reports = db.query(HealthReport).order_by(HealthReport.created_at.desc()).all()
    return templates.TemplateResponse("admin/reports.html", {"request": request, "admin": admin, "reports": reports})

@router.get("/doctors", response_class=HTMLResponse)
async def admin_doctors(request: Request, db: Session = Depends(get_db)):
    admin = get_current_admin(request, db)
    if not admin:
        return RedirectResponse("/admin/login", status_code=status.HTTP_302_FOUND)
    doctors = db.query(Doctor).all()
    return templates.TemplateResponse("admin/doctors.html", {"request": request, "admin": admin, "doctors": doctors, "success": None})

@router.post("/doctors/add")
async def add_doctor(request: Request, name: str = Form(...), specialty: str = Form(...), db: Session = Depends(get_db)):
    admin = get_current_admin(request, db)
    if not admin:
        return RedirectResponse("/admin/login", status_code=status.HTTP_302_FOUND)
    db.add(Doctor(name=name, specialty=specialty, available="Yes"))
    db.commit()
    doctors = db.query(Doctor).all()
    return templates.TemplateResponse("admin/doctors.html", {"request": request, "admin": admin, "doctors": doctors, "success": "Doctor added."})

@router.post("/doctors/{doctor_id}/toggle")
async def toggle_doctor(request: Request, doctor_id: int, db: Session = Depends(get_db)):
    admin = get_current_admin(request, db)
    if not admin:
        return RedirectResponse("/admin/login", status_code=status.HTTP_302_FOUND)
    doc = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if doc:
        doc.available = "No" if doc.available == "Yes" else "Yes"
        db.commit()
    return RedirectResponse("/admin/doctors", status_code=status.HTTP_302_FOUND)

@router.get("/analytics", response_class=HTMLResponse)
async def admin_analytics(request: Request, db: Session = Depends(get_db)):
    admin = get_current_admin(request, db)
    if not admin:
        return RedirectResponse("/admin/login", status_code=status.HTTP_302_FOUND)
    from sqlalchemy import func
    bmi_stats = db.query(BMIRecord.category, func.count(BMIRecord.id).label("cnt")).group_by(BMIRecord.category).all()
    total_bmi = db.query(BMIRecord).count()
    reports_per_user = db.query(func.count(HealthReport.id)).filter(HealthReport.user_id == User.id).scalar() or 0
    return templates.TemplateResponse("admin/analytics.html", {
        "request": request, "admin": admin,
        "bmi_stats": bmi_stats, "total_bmi": total_bmi,
        "total_users": db.query(User).count(),
        "total_reports": db.query(HealthReport).count(),
        "total_chats": db.query(ChatHistory).count(),
    })

@router.get("/doctor-accounts", response_class=HTMLResponse)
async def admin_doctor_accounts(request: Request, db: Session = Depends(get_db)):
    from app.models.models import DoctorAccount
    admin = get_current_admin(request, db)
    if not admin:
        return RedirectResponse("/admin/login", status_code=status.HTTP_302_FOUND)
    doctors = db.query(DoctorAccount).all()
    return templates.TemplateResponse("admin/doctor_accounts.html", {"request": request, "admin": admin, "doctors": doctors, "success": None, "error": None})

@router.post("/doctor-accounts/add")
async def add_doctor_account(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    specialty: str = Form(...),
    qualification: str = Form(""),
    experience_years: int = Form(0),
    fee: float = Form(500.0),
    bio: str = Form(""),
    db: Session = Depends(get_db)
):
    from app.models.models import DoctorAccount
    from passlib.context import CryptContext
    admin = get_current_admin(request, db)
    if not admin:
        return RedirectResponse("/admin/login", status_code=status.HTTP_302_FOUND)
    pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
    if db.query(DoctorAccount).filter(DoctorAccount.email == email).first():
        doctors = db.query(DoctorAccount).all()
        return templates.TemplateResponse("admin/doctor_accounts.html", {"request": request, "admin": admin, "doctors": doctors, "error": "Email already exists.", "success": None})
    db.add(DoctorAccount(full_name=full_name, email=email, password_hash=pwd.hash(password),
                         specialty=specialty, qualification=qualification,
                         experience_years=experience_years, fee=fee, bio=bio, available="Yes"))
    db.commit()
    doctors = db.query(DoctorAccount).all()
    return templates.TemplateResponse("admin/doctor_accounts.html", {"request": request, "admin": admin, "doctors": doctors, "success": f"Dr. {full_name} added successfully.", "error": None})

@router.post("/doctor-accounts/{doc_id}/toggle")
async def toggle_doctor_account(request: Request, doc_id: int, db: Session = Depends(get_db)):
    from app.models.models import DoctorAccount
    admin = get_current_admin(request, db)
    if not admin:
        return RedirectResponse("/admin/login", status_code=status.HTTP_302_FOUND)
    doc = db.query(DoctorAccount).filter(DoctorAccount.id == doc_id).first()
    if doc:
        doc.available = "No" if doc.available == "Yes" else "Yes"
        db.commit()
    return RedirectResponse("/admin/doctor-accounts", status_code=status.HTTP_302_FOUND)
