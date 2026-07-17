from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, Date
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.db import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=False)
    phone = Column(String(20))
    dob = Column(Date)
    gender = Column(String(10))
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

#  nya nam = relationship("jis se krna hai , back_populates="jis se krna hai")
    medical_history = relationship("MedicalHistory", back_populates="user", uselist=False)
    chats = relationship("ChatHistory", back_populates="user")
    reports = relationship("HealthReport", back_populates="user")
    bmi_records = relationship("BMIRecord", back_populates="user")

class Admin(Base):
    __tablename__ = "admins"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class MedicalHistory(Base):
    __tablename__ = "medical_history"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    allergies = Column(Text, default="")
    chronic_conditions = Column(Text, default="")
    surgeries = Column(Text, default="")
    medications = Column(Text, default="")
    family_history = Column(Text, default="")
    user = relationship("User", back_populates="medical_history")

class ChatHistory(Base):
    __tablename__ = "chat_history"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    session_id = Column(String(64), nullable=False, index=True)
    user_message = Column(Text, nullable=False)
    ai_response = Column(Text)
    message_index = Column(Integer, default=0)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="chats")

class HealthReport(Base):
    __tablename__ = "health_reports"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    session_id = Column(String(64))
    report_path = Column(String(255))
    report_title = Column(String(200), default="Health Assessment Report")
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="reports")

class BMIRecord(Base):
    __tablename__ = "bmi_records"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    height = Column(Float)
    weight = Column(Float)
    bmi = Column(Float)
    category = Column(String(30))
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="bmi_records")

class Doctor(Base):
    __tablename__ = "doctors"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    specialty = Column(String(100))
    available = Column(String(5), default="Yes")

class DoctorAccount(Base):
    __tablename__ = "doctor_accounts"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    specialty = Column(String(100))
    experience_years = Column(Integer, default=0)
    fee = Column(Float, default=500.0)
    bio = Column(Text, default="")
    qualification = Column(String(200), default="")
    rating = Column(Float, default=4.5)
    available = Column(String(5), default="Yes")
    created_at = Column(DateTime, default=datetime.utcnow)
    appointments = relationship("Appointment", back_populates="doctor")

class Appointment(Base):
    __tablename__ = "appointments"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    doctor_id = Column(Integer, ForeignKey("doctor_accounts.id"))
    status = Column(String(30), default="pending")
    txn_id = Column(String(64))
    fee_paid = Column(Float, default=0.0)
    platform_fee = Column(Float, default=0.0)
    symptoms_note = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User")
    doctor = relationship("DoctorAccount", back_populates="appointments")
    messages = relationship("ConsultationMessage", back_populates="appointment")
    prescription = relationship("Prescription", back_populates="appointment", uselist=False)
    invoice = relationship("Invoice", back_populates="appointment", uselist=False)

class ConsultationMessage(Base):
    __tablename__ = "consultation_messages"
    id = Column(Integer, primary_key=True, index=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"))
    sender_role = Column(String(10))  # patient / doctor
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    appointment = relationship("Appointment", back_populates="messages")

class Prescription(Base):
    __tablename__ = "prescriptions"
    id = Column(Integer, primary_key=True, index=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), unique=True)
    diagnosis = Column(Text)
    medicines = Column(Text)  # JSON string
    instructions = Column(Text)
    follow_up = Column(String(50))
    pdf_path = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    appointment = relationship("Appointment", back_populates="prescription")

class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, index=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), unique=True)
    txn_id = Column(String(64))
    amount = Column(Float)
    platform_fee = Column(Float)
    total = Column(Float)
    pdf_path = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    appointment = relationship("Appointment", back_populates="invoice")
