from fastapi import APIRouter, Request, Form, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from passlib.context import CryptContext
import json, os, asyncio
from datetime import datetime
from app.database.db import get_db
from app.models.models import DoctorAccount, Appointment, ConsultationMessage, Prescription, Invoice
from app.services.consultation_pdf import generate_prescription_pdf

router = APIRouter(prefix="/doctor")
templates = Jinja2Templates(directory="app/templates")
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_doctor(request: Request, db: Session = Depends(get_db)):
    did = request.session.get("doctor_id")
    if not did: return None
    return db.query(DoctorAccount).filter(DoctorAccount.id == did).first()

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("doctor/login.html", {"request": request, "error": None})

@router.post("/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    doc = db.query(DoctorAccount).filter(DoctorAccount.email == email).first()
    if not doc or not pwd_ctx.verify(password, doc.password_hash):
        return templates.TemplateResponse("doctor/login.html", {"request": request, "error": "Invalid credentials."})
    request.session["doctor_id"] = doc.id
    return RedirectResponse("/doctor/dashboard", status_code=status.HTTP_302_FOUND)

@router.get("/logout")
async def logout(request: Request):
    request.session.pop("doctor_id", None)
    return RedirectResponse("/doctor/login", status_code=status.HTTP_302_FOUND)

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    doc = get_doctor(request, db)
    if not doc: return RedirectResponse("/doctor/login", status_code=status.HTTP_302_FOUND)

    pending = db.query(Appointment).filter(Appointment.doctor_id == doc.id, Appointment.status == "paid").order_by(Appointment.created_at.desc()).all()
    active  = db.query(Appointment).filter(Appointment.doctor_id == doc.id, Appointment.status == "active").order_by(Appointment.created_at.desc()).all()
    completed_list = db.query(Appointment).filter(Appointment.doctor_id == doc.id, Appointment.status == "completed").order_by(Appointment.created_at.desc()).all()
    total_earned = sum(a.fee_paid for a in completed_list)

    return templates.TemplateResponse("doctor/dashboard.html", {
        "request": request, "doc": doc,
        "pending": pending, "active": active,
        "completed": completed_list,
        "completed_count": len(completed_list),
        "total_earned": total_earned,
    })

@router.post("/appointment/{appt_id}/accept")
async def accept(request: Request, appt_id: int, db: Session = Depends(get_db)):
    doc = get_doctor(request, db)
    if not doc: return RedirectResponse("/doctor/login", status_code=status.HTTP_302_FOUND)
    appt = db.query(Appointment).filter(Appointment.id == appt_id, Appointment.doctor_id == doc.id).first()
    if appt and appt.status == "paid":
        appt.status = "active"
        db.commit()
        msg = ConsultationMessage(appointment_id=appt.id, sender_role="doctor",
            message=f"Hello {appt.user.full_name}! I'm Dr. {doc.full_name}. I've reviewed your case. Please describe your main concerns and I'll guide you.")
        db.add(msg); db.commit()
    return RedirectResponse(f"/doctor/consultation/{appt_id}", status_code=status.HTTP_302_FOUND)

@router.get("/consultation/{appt_id}", response_class=HTMLResponse)
async def consultation(request: Request, appt_id: int, db: Session = Depends(get_db)):
    doc = get_doctor(request, db)
    if not doc: return RedirectResponse("/doctor/login", status_code=status.HTTP_302_FOUND)
    appt = db.query(Appointment).filter(Appointment.id == appt_id, Appointment.doctor_id == doc.id).first()
    if not appt: return RedirectResponse("/doctor/dashboard", status_code=status.HTTP_302_FOUND)
    messages = db.query(ConsultationMessage).filter(ConsultationMessage.appointment_id == appt_id).order_by(ConsultationMessage.timestamp).all()
    return templates.TemplateResponse("doctor/consultation.html", {
        "request": request, "doc": doc, "appt": appt, "messages": messages,
    })

@router.post("/consultation/{appt_id}/send")
async def send_msg(request: Request, appt_id: int, message: str = Form(...), db: Session = Depends(get_db)):
    doc = get_doctor(request, db)
    if not doc: return RedirectResponse("/doctor/login", status_code=status.HTTP_302_FOUND)
    appt = db.query(Appointment).filter(Appointment.id == appt_id, Appointment.doctor_id == doc.id).first()
    if appt and appt.status == "active":
        db.add(ConsultationMessage(appointment_id=appt_id, sender_role="doctor", message=message))
        db.commit()
    return RedirectResponse(f"/doctor/consultation/{appt_id}", status_code=status.HTTP_302_FOUND)

@router.post("/consultation/{appt_id}/prescribe")
async def prescribe(
    request: Request, appt_id: int,
    diagnosis: str = Form(...),
    instructions: str = Form(""),
    follow_up: str = Form(""),
    medicine_names: list = Form(default=[]),
    medicine_dosages: list = Form(default=[]),
    medicine_freqs: list = Form(default=[]),
    medicine_durations: list = Form(default=[]),
    db: Session = Depends(get_db)
):
    doc = get_doctor(request, db)
    if not doc: return RedirectResponse("/doctor/login", status_code=status.HTTP_302_FOUND)
    appt = db.query(Appointment).filter(Appointment.id == appt_id, Appointment.doctor_id == doc.id).first()
    if not appt: return RedirectResponse("/doctor/dashboard", status_code=status.HTTP_302_FOUND)

    meds = [{"name": n, "dosage": d, "frequency": f, "duration": du}
            for n, d, f, du in zip(medicine_names, medicine_dosages, medicine_freqs, medicine_durations) if n.strip()]

    pres = Prescription(appointment_id=appt_id, diagnosis=diagnosis,
                        medicines=json.dumps(meds), instructions=instructions, follow_up=follow_up)
    db.add(pres); db.flush()

    pdf_file = generate_prescription_pdf(appt, pres, appt.user, doc)
    pres.pdf_path = pdf_file

    appt.status = "completed"
    db.add(ConsultationMessage(appointment_id=appt_id, sender_role="doctor",
        message="I have issued your prescription. You can download it from the consultation page. Please follow the instructions carefully and take care! 🙏"))
    db.commit()
    return RedirectResponse(f"/doctor/consultation/{appt_id}", status_code=status.HTTP_302_FOUND)

@router.get("/consultation/{appt_id}/messages.json")
async def messages_json(request: Request, appt_id: int, after: int = 0, db: Session = Depends(get_db)):
    doc = get_doctor(request, db)
    if not doc: return {"messages": []}
    msgs = db.query(ConsultationMessage).filter(
        ConsultationMessage.appointment_id == appt_id,
        ConsultationMessage.id > after
    ).order_by(ConsultationMessage.timestamp).all()
    return {"messages": [{"id": m.id, "role": m.sender_role, "text": m.message,
                          "time": m.timestamp.strftime("%H:%M") if m.timestamp else ""} for m in msgs]}

@router.get("/prescription/download/{filename}")
async def dl_prescription(request: Request, filename: str, db: Session = Depends(get_db)):
    doc = get_doctor(request, db)
    if not doc: return RedirectResponse("/doctor/login", status_code=status.HTTP_302_FOUND)
    fp = os.path.join("app/static/reports", filename)
    if os.path.exists(fp): return FileResponse(fp, media_type="application/pdf", filename=filename)
    return RedirectResponse("/doctor/dashboard", status_code=status.HTTP_302_FOUND)
