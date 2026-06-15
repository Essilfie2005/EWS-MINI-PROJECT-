from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from datetime import datetime
from database.db import Base


class SMSLog(Base):
    __tablename__ = "sms_logs"

    id = Column(Integer, primary_key=True)

    student_id = Column(Integer, ForeignKey("students.id"))

    phone_number = Column(String(20))
    message = Column(String(500))

    status = Column(String(20))

    success = Column(Boolean, default=False)

    sms_provider_id = Column(String(100), nullable=True)

    error_message = Column(String(255), nullable=True)

    sent_at = Column(DateTime, default=datetime.utcnow)
    delivered_at = Column(DateTime, nullable=True)
