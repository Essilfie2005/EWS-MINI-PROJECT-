from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from datetime import datetime
from database.db import Base


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True)

    student_id = Column(Integer, ForeignKey("students.id"))
    anon_id = Column(String(50))

    alert_type = Column(String(50))
    priority = Column(String(20))
    status = Column(String(20))

    message = Column(String(500))

    is_read = Column(Boolean, default=False)
    is_dismissed = Column(Boolean, default=False)

    prediction_id = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
