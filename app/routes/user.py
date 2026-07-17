from fastapi import APIRouter, Request, Form, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import date
import os
from app.database.db import get_db
from app.models.models import User, MedicalHistory, ChatHistory, HealthReport, BMIRecord
from app.routes.auth import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)

    total_chats = db.query(ChatHistory).filter(ChatHistory.user_id == user.id).count()
    total_reports = db.query(HealthReport).filter(HealthReport.user_id == user.id).count()
    recent_reports = db.query(HealthReport).filter(HealthReport.user_id == user.id).order_by(HealthReport.created_at.desc()).limit(3).all()
    latest_bmi = db.query(BMIRecord).filter(BMIRecord.user_id == user.id).order_by(BMIRecord.created_at.desc()).first()
    recent_chats = db.query(ChatHistory).filter(ChatHistory.user_id == user.id).order_by(ChatHistory.timestamp.desc()).limit(4).all()

    return templates.TemplateResponse("user/dashboard.html", {
        "request": request, "user": user,
        "total_chats": total_chats,
        "total_reports": total_reports,
        "recent_reports": recent_reports,
        "latest_bmi": latest_bmi,
        "recent_chats": recent_chats,
    })

@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    history = db.query(MedicalHistory).filter(MedicalHistory.user_id == user.id).first()
    return templates.TemplateResponse("user/profile.html", {"request": request, "user": user, "history": history, "success": None, "error": None})

@router.post("/profile")
async def update_profile(
    request: Request,
    full_name: str = Form(...),
    phone: str = Form(""),
    dob: str = Form(""),
    gender: str = Form(""),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    user.full_name = full_name
    user.phone = phone
    user.gender = gender
    if dob:
        user.dob = date.fromisoformat(dob)
    db.commit()
    history = db.query(MedicalHistory).filter(MedicalHistory.user_id == user.id).first()
    return templates.TemplateResponse("user/profile.html", {"request": request, "user": user, "history": history, "success": "Profile updated successfully.", "error": None})

@router.post("/profile/medical")
async def update_medical(
    request: Request,
    allergies: str = Form(""),
    chronic_conditions: str = Form(""),
    surgeries: str = Form(""),
    medications: str = Form(""),
    family_history: str = Form(""),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    history = db.query(MedicalHistory).filter(MedicalHistory.user_id == user.id).first()
    if not history:
        history = MedicalHistory(user_id=user.id)
        db.add(history)
    history.allergies = allergies
    history.chronic_conditions = chronic_conditions
    history.surgeries = surgeries
    history.medications = medications
    history.family_history = family_history
    db.commit()
    return templates.TemplateResponse("user/profile.html", {"request": request, "user": user, "history": history, "success": "Medical history updated.", "error": None})

@router.get("/bmi-calculator", response_class=HTMLResponse)
async def bmi_calculator(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    records = db.query(BMIRecord).filter(BMIRecord.user_id == user.id).order_by(BMIRecord.created_at.desc()).limit(10).all()
    return templates.TemplateResponse("user/bmi_calculator.html", {"request": request, "user": user, "bmi_result": None, "records": records})

@router.post("/bmi-calculator")
async def calculate_bmi(
    request: Request,
    height: float = Form(...),
    weight: float = Form(...),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)

    bmi = weight / ((height / 100) ** 2)
    if bmi < 18.5:
        category = "Underweight"
    elif bmi < 25:
        category = "Normal Weight"
    elif bmi < 30:
        category = "Overweight"
    else:
        category = "Obese"

    record = BMIRecord(user_id=user.id, height=height, weight=weight, bmi=round(bmi, 1), category=category)
    db.add(record)
    db.commit()

    records = db.query(BMIRecord).filter(BMIRecord.user_id == user.id).order_by(BMIRecord.created_at.desc()).limit(10).all()
    return templates.TemplateResponse("user/bmi_calculator.html", {
        "request": request, "user": user,
        "bmi_result": {"bmi": round(bmi, 1), "category": category, "height": height, "weight": weight},
        "records": records
    })

@router.get("/health-history", response_class=HTMLResponse)
async def health_history(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)

    from sqlalchemy import func
    sessions = db.query(
        ChatHistory.session_id,
        func.count(ChatHistory.id).label("msg_count"),
        func.min(ChatHistory.timestamp).label("started_at"),
        func.max(ChatHistory.timestamp).label("last_at"),
    ).filter(ChatHistory.user_id == user.id).group_by(ChatHistory.session_id).order_by(func.max(ChatHistory.timestamp).desc()).all()

    session_data = []
    for s in sessions:
        first_msg = db.query(ChatHistory).filter(
            ChatHistory.user_id == user.id,
            ChatHistory.session_id == s.session_id
        ).order_by(ChatHistory.message_index).first()
        report = db.query(HealthReport).filter(
            HealthReport.user_id == user.id,
            HealthReport.session_id == s.session_id
        ).first()
        session_data.append({
            "session_id": s.session_id,
            "msg_count": s.msg_count,
            "started_at": s.started_at,
            "last_at": s.last_at,
            "first_msg": first_msg.user_message[:80] if first_msg else "",
            "report": report,
        })

    bmi_records = db.query(BMIRecord).filter(BMIRecord.user_id == user.id).order_by(BMIRecord.created_at.desc()).all()

    return templates.TemplateResponse("user/health_history.html", {
        "request": request, "user": user,
        "session_data": session_data,
        "bmi_records": bmi_records,
    })

@router.get("/health-history/session/{session_id}", response_class=HTMLResponse)
async def view_session(request: Request, session_id: str, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    chats = db.query(ChatHistory).filter(
        ChatHistory.user_id == user.id,
        ChatHistory.session_id == session_id
    ).order_by(ChatHistory.message_index).all()
    report = db.query(HealthReport).filter(
        HealthReport.user_id == user.id,
        HealthReport.session_id == session_id
    ).first()
    return templates.TemplateResponse("user/session_view.html", {
        "request": request, "user": user,
        "chats": chats, "report": report, "session_id": session_id
    })

@router.get("/reports/download/{filename}")
async def download_report(request: Request, filename: str, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    report = db.query(HealthReport).filter(
        HealthReport.report_path == filename,
        HealthReport.user_id == user.id
    ).first()
    if not report:
        return RedirectResponse("/health-history", status_code=status.HTTP_302_FOUND)
    filepath = os.path.join("app/static/reports", filename)
    if os.path.exists(filepath):
        return FileResponse(filepath, media_type="application/pdf", filename=filename)
    return RedirectResponse("/health-history", status_code=status.HTTP_302_FOUND)
