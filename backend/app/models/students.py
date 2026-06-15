from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean
from datetime import datetime
from database.db import Base


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    anon_id = Column(String(50), unique=True, index=True)

    attendance_rate = Column(Float)
    quiz_average = Column(Float)
    assignment_submission_rate = Column(Float)
    mobile_engagement_freq = Column(Float)
    financial_aid_status = Column(Float)

    phone_number = Column(String(20), nullable=True)

    risk_score = Column(Float, nullable=True)
    risk_band = Column(String(20), nullable=True)

    is_flagged = Column(Boolean, default=False)

    dropout_label = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
