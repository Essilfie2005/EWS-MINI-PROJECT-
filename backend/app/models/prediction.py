from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from sqlalchemy.dialects.mysql import JSON
from datetime import datetime
from database.db import Base


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True)

    student_id = Column(Integer, ForeignKey("students.id"))
    anon_id = Column(String(50))

    risk_score = Column(Float)
    confidence_score = Column(Float)

    risk_band = Column(String(20))

    model_version = Column(String(50))
    explanation_version = Column(String(50))

    shap_values = Column(JSON)
    top_factors = Column(JSON)
    recommended_actions = Column(JSON)

    waterfall_plot_url = Column(String(255))

    status = Column(String(20))

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow,
                        onupdate=datetime.datetime.utcnow)
