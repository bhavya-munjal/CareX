from fastapi import APIRouter, Request, Form, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import uuid, os
from datetime import datetime
from app.database.db import get_db
from app.models.models import DoctorAccount, Appointment, ConsultationMessage, Invoice
from app.routes.auth import get_current_user
from app.services.consultation_pdf import generate_invoice_pdf

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

PLATFORM_FEE_PERCENT = 10  # 10%

def _log_payment_email(user, doctor, appt, total):
    sep = "═" * 58
    print(f"\n{sep}")
    print(f"  📧 CAREBOT PAYMENT CONFIRMATION — EMAIL SIMULATION")
    print(sep)
    print(f"  To:      {user.email}")
    print(f"  Subject: Payment Confirmed — Consultation with Dr. {doctor.full_name}")
    print(f"")
    print(f"  Dear {user.full_name},")
    print(f"")
    print(f"  Your payment has been successfully processed.")
    print(f"")
    print(f"  ┌─ Transaction Details ────────────────────────────")
    print(f"  │  Transaction ID  : {appt.txn_id}")
    print(f"  │  Doctor          : Dr. {doctor.full_name} ({doctor.specialty})")
    print(f"  │  Consultation Fee: ₹{appt.fee_paid:,.0f}")
    print(f"  │  Platform Fee    : ₹{appt.platform_fee:,.0f}")
    print(f"  │  Total Paid      : ₹{total:,.0f}")
    print(f"  │  Date & Time     : {datetime.now().strftime('%d %b %Y, %H:%M IST')}")
    print(f"  └──────────────────────────────────────────────────")
    print(f"")
    print(f"  Your consultation is now confirmed. The doctor will")
    print(f"  accept and begin your session shortly.")
    print(f"")
    print(f"  Visit: http://localhost:8000/appointments/my")
    print(f"  — CareBot Health Platform")
    print(f"{sep}\n")

@router.get("/doctors", response_class=HTMLResponse)
async def browse_doctors(request: Request, specialty: str = "", db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    q = db.query(DoctorAccount).filter(DoctorAccount.available == "Yes")
    if specialty:
        q = q.filter(DoctorAccount.specialty == specialty)
    doctors = q.all()
    specialties = db.query(DoctorAccount.specialty).distinct().all()
    specialties = [s[0] for s in specialties if s[0]]
    return templates.TemplateResponse("user/doctors.html", {
        "request": request, "user": user, "doctors": doctors,
        "specialties": specialties, "selected_specialty": specialty,
    })

@router.get("/doctors/{doctor_id}/book", response_class=HTMLResponse)
async def book_page(request: Request, doctor_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    doctor = db.query(DoctorAccount).filter(DoctorAccount.id == doctor_id, DoctorAccount.available == "Yes").first()
    if not doctor: return RedirectResponse("/doctors", status_code=status.HTTP_302_FOUND)
    platform_fee = round(doctor.fee * PLATFORM_FEE_PERCENT / 100)
    total = doctor.fee + platform_fee
    return templates.TemplateResponse("user/book_appointment.html", {
        "request": request, "user": user, "doctor": doctor,
        "platform_fee": platform_fee, "total": total,
    })

@router.post("/doctors/{doctor_id}/pay")
async def process_payment(
    request: Request, doctor_id: int,
    symptoms_note: str = Form(""),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user: return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    doctor = db.query(DoctorAccount).filter(DoctorAccount.id == doctor_id).first()
    if not doctor: return RedirectResponse("/doctors", status_code=status.HTTP_302_FOUND)

    platform_fee = round(doctor.fee * PLATFORM_FEE_PERCENT / 100)
    total = doctor.fee + platform_fee
    txn_id = f"CB{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"

    appt = Appointment(
        user_id=user.id, doctor_id=doctor_id,
        status="paid", txn_id=txn_id,
        fee_paid=doctor.fee, platform_fee=platform_fee,
        symptoms_note=symptoms_note,
    )
    db.add(appt); db.flush()

    inv_pdf = generate_invoice_pdf(appt, user, doctor)
    invoice = Invoice(appointment_id=appt.id, txn_id=txn_id,
                      amount=doctor.fee, platform_fee=platform_fee,
                      total=total, pdf_path=inv_pdf)
    db.add(invoice)
    db.commit()

    _log_payment_email(user, doctor, appt, total)

    return templates.TemplateResponse("user/payment_success.html", {
        "request": request, "user": user,
        "appt": appt, "doctor": doctor,
        "total": total, "txn_id": txn_id,
        "invoice": invoice,
    })

@router.get("/appointments/my", response_class=HTMLResponse)
async def my_appointments(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    appts = db.query(Appointment).filter(Appointment.user_id == user.id).order_by(Appointment.created_at.desc()).all()
    return templates.TemplateResponse("user/my_appointments.html", {"request": request, "user": user, "appts": appts})

@router.get("/consultation/{appt_id}", response_class=HTMLResponse)
async def patient_consultation(request: Request, appt_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    appt = db.query(Appointment).filter(Appointment.id == appt_id, Appointment.user_id == user.id).first()
    if not appt: return RedirectResponse("/appointments/my", status_code=status.HTTP_302_FOUND)
    messages = db.query(ConsultationMessage).filter(ConsultationMessage.appointment_id == appt_id).order_by(ConsultationMessage.timestamp).all()
    return templates.TemplateResponse("user/consultation.html", {
        "request": request, "user": user, "appt": appt, "messages": messages,
    })

@router.post("/consultation/{appt_id}/send")
async def patient_send(request: Request, appt_id: int, message: str = Form(...), db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    appt = db.query(Appointment).filter(Appointment.id == appt_id, Appointment.user_id == user.id).first()
    if appt and appt.status == "active":
        db.add(ConsultationMessage(appointment_id=appt_id, sender_role="patient", message=message))
        db.commit()
    return RedirectResponse(f"/consultation/{appt_id}", status_code=status.HTTP_302_FOUND)

@router.get("/consultation/{appt_id}/messages.json")
async def patient_messages_json(request: Request, appt_id: int, after: int = 0, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return {"messages": []}
    appt = db.query(Appointment).filter(Appointment.id == appt_id, Appointment.user_id == user.id).first()
    if not appt: return {"messages": []}
    msgs = db.query(ConsultationMessage).filter(
        ConsultationMessage.appointment_id == appt_id,
        ConsultationMessage.id > after
    ).order_by(ConsultationMessage.timestamp).all()
    return {"messages": [{"id": m.id, "role": m.sender_role, "text": m.message,
                          "time": m.timestamp.strftime("%H:%M") if m.timestamp else ""} for m in msgs]}

@router.get("/invoice/download/{filename}")
async def dl_invoice(request: Request, filename: str, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    fp = os.path.join("app/static/reports", filename)
    if os.path.exists(fp): return FileResponse(fp, media_type="application/pdf", filename=filename)
    return RedirectResponse("/appointments/my", status_code=status.HTTP_302_FOUND)

@router.get("/prescription/download/{filename}")
async def dl_rx(request: Request, filename: str, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    fp = os.path.join("app/static/reports", filename)
    if os.path.exists(fp): return FileResponse(fp, media_type="application/pdf", filename=filename)
    return RedirectResponse("/appointments/my", status_code=status.HTTP_302_FOUND)
