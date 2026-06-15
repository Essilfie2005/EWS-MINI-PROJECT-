from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.dialects.mysql import JSON
from datetime import datetime
from database.db import Base


class Intervention(Base):
    __tablename__ = "interventions"

    id = Column(Integer, primary_key=True)

    student_id = Column(Integer, ForeignKey("students.id"))
    anon_id = Column(String(50))

    intervention_type = Column(String(20))
    description = Column(String(500))

    status = Column(String(20))
    outcome = Column(String(1000))

    handled_by = Column(String(100))

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
