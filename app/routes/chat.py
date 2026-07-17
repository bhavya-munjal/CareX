from fastapi import APIRouter, Request, Form, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import uuid, os
from app.database.db import get_db
from app.models.models import ChatHistory, HealthReport, BMIRecord
from app.routes.auth import get_current_user
from app.services import gemini_service, pdf_service

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

REPORT_PROMPT_THRESHOLD = 10

def _get_or_create_session(request: Request) -> str:
    if "chat_session_id" not in request.session:
        request.session["chat_session_id"] = str(uuid.uuid4())
    return request.session["chat_session_id"]

@router.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)

    session_id = _get_or_create_session(request)
    chats = db.query(ChatHistory).filter(
        ChatHistory.user_id == user.id,
        ChatHistory.session_id == session_id
    ).order_by(ChatHistory.message_index).all()

    msg_count = len(chats)
    show_report_prompt = msg_count >= REPORT_PROMPT_THRESHOLD and msg_count % REPORT_PROMPT_THRESHOLD == 0

    existing_report = None
    if msg_count > 0:
        existing_report = db.query(HealthReport).filter(
            HealthReport.user_id == user.id,
            HealthReport.session_id == session_id
        ).order_by(HealthReport.created_at.desc()).first()

    return templates.TemplateResponse("user/chat.html", {
        "request": request, "user": user, "chats": chats,
        "msg_count": msg_count,
        "show_report_prompt": show_report_prompt and not existing_report,
        "session_id": session_id,
        "existing_report": existing_report,
    })

@router.post("/chat")
async def send_message(
    request: Request,
    message: str = Form(...),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)

    session_id = _get_or_create_session(request)

    prev_chats = db.query(ChatHistory).filter(
        ChatHistory.user_id == user.id,
        ChatHistory.session_id == session_id
    ).order_by(ChatHistory.message_index).all()

    conversation_history = []
    for c in prev_chats:
        conversation_history.append({"role": "user", "content": c.user_message})
        conversation_history.append({"role": "model", "content": c.ai_response})

    ai_response = gemini_service.chat_response(conversation_history, message)

    next_index = len(prev_chats)
    chat = ChatHistory(
        user_id=user.id, session_id=session_id,
        user_message=message, ai_response=ai_response,
        message_index=next_index
    )
    db.add(chat)
    db.commit()

    return RedirectResponse("/chat", status_code=status.HTTP_302_FOUND)

@router.post("/chat/new-session")
async def new_session(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    request.session["chat_session_id"] = str(uuid.uuid4())
    return RedirectResponse("/chat", status_code=status.HTTP_302_FOUND)

@router.post("/chat/generate-report")
async def generate_report(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)

    session_id = _get_or_create_session(request)
    chats = db.query(ChatHistory).filter(
        ChatHistory.user_id == user.id,
        ChatHistory.session_id == session_id
    ).order_by(ChatHistory.message_index).all()

    if not chats:
        return RedirectResponse("/chat", status_code=status.HTTP_302_FOUND)

    conversation_history = []
    for c in chats:
        conversation_history.append({"role": "user", "content": c.user_message})
        conversation_history.append({"role": "model", "content": c.ai_response})

    report_data = gemini_service.generate_report_data(conversation_history, user.full_name)
    filename = pdf_service.generate_health_report(user, report_data, session_id)

    report = HealthReport(
        user_id=user.id, session_id=session_id,
        report_path=filename,
        report_title=report_data.get("report_title", "Health Assessment Report")
    )
    db.add(report)
    db.commit()

    return RedirectResponse("/chat", status_code=status.HTTP_302_FOUND)

@router.get("/chat/download/{filename}")
async def download_report(request: Request, filename: str, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    report = db.query(HealthReport).filter(
        HealthReport.report_path == filename,
        HealthReport.user_id == user.id
    ).first()
    if not report:
        return RedirectResponse("/chat", status_code=status.HTTP_302_FOUND)
    filepath = os.path.join("app/static/reports", filename)
    if os.path.exists(filepath):
        return FileResponse(filepath, media_type="application/pdf", filename=filename)
    return RedirectResponse("/chat", status_code=status.HTTP_302_FOUND)
