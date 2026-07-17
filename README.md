# CareBot — AI-Powered Healthcare Assistant

Final Year Engineering Project | FastAPI + Google Gemini + SQLite

---

## Tech Stack

- **Backend**: Python, FastAPI, SQLAlchemy ORM
- **Frontend**: HTML5, CSS3, Jinja2 Templates
- **AI**: Google Gemini 1.5 Flash API
- **Database**: SQLite
- **Auth**: Session-based (itsdangerous)
- **Reports**: ReportLab PDF generation

---

## Project Structure

```
carebot/
├── app/
│   ├── database/db.py          # SQLAlchemy engine & session
│   ├── models/models.py        # All ORM models
│   ├── routes/
│   │   ├── auth.py             # Login, register, logout
│   │   ├── user.py             # Dashboard, profile, history
│   │   ├── ai_features.py      # Symptom checker, chatbot, pain, wellness, BMI
│   │   ├── appointments_reports.py  # Appointments & PDF reports
│   │   └── admin.py            # Admin dashboard & management
│   ├── services/
│   │   ├── gemini_service.py   # Google Gemini AI integration
│   │   └── pdf_service.py      # ReportLab PDF generation
│   ├── templates/              # Jinja2 HTML templates
│   └── static/
│       ├── css/style.css       # Main stylesheet
│       └── reports/            # Generated PDFs (auto-created)
├── main.py                     # FastAPI app entry point
├── init_db.py                  # DB init + admin + doctors seeding
├── requirements.txt
├── .env.example
└── README.md
```

---

## Installation & Setup

### 1. Clone / Extract Project

```bash
cd carebot
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# Activate:
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env`:

```env
GEMINI_API_KEY=your_gemini_api_key_here
SECRET_KEY=your_random_secret_key_here
DATABASE_URL=sqlite:///./carebot.db
```

**Get Gemini API Key**: https://aistudio.google.com/app/apikey

### 5. Initialize Database

```bash
python init_db.py
```

This creates:
- SQLite database (`carebot.db`)
- Default admin account
- 6 sample doctors

### 6. Run the Application

```bash
uvicorn main:app --reload
```

Open: http://localhost:8000

---

## Default Credentials

### Admin
- URL: http://localhost:8000/admin/login
- Email: `admin@carebot.com`
- Password: `Admin@123`

### Users
Register at: http://localhost:8000/register

---

## Features

### User Features
| Feature | Route |
|---------|-------|
| Landing Page | `/` |
| Register | `/register` |
| Login | `/login` |
| Dashboard | `/dashboard` |
| Symptom Checker | `/symptom-checker` |
| AI Chatbot | `/chatbot` |
| Physical Pain Assistant | `/physical-pain` |
| Mental Wellness | `/mental-wellness` |
| BMI Calculator | `/bmi-calculator` |
| Appointments | `/appointments` |
| Health Reports | `/reports` |
| Health History | `/health-history` |
| Profile | `/profile` |

### Admin Features
| Feature | Route |
|---------|-------|
| Admin Login | `/admin/login` |
| Admin Dashboard | `/admin/dashboard` |
| Manage Users | `/admin/users` |
| Manage Appointments | `/admin/appointments` |
| View Reports | `/admin/reports` |
| Manage Doctors | `/admin/doctors` |
| Analytics | `/admin/analytics` |

---

## Gemini AI Usage

The Gemini API is called only for:
- Symptom analysis (`/symptom-checker`)
- Health chatbot responses (`/chatbot`)
- Physical pain guidance (`/physical-pain`)
- Mental wellness suggestions (`/mental-wellness`)

BMI calculation, appointments, dashboard, and CRUD operations are handled server-side — no AI calls.

---

## Security

- Passwords hashed with bcrypt
- Session-based auth (server-side)
- SQL injection protection via SQLAlchemy ORM
- Environment variables for all secrets
- Input validation on all forms

---

## Medical Disclaimer

CareBot is for **informational and educational purposes only**. It does not provide medical diagnosis, treatment, or prescriptions. Always consult a qualified healthcare professional.
