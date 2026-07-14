"""
V3 Risk Forecasting Service
==============================
Forecasts a student's dropout risk 4 weeks into the future using
exponential smoothing trend analysis on their historical risk scores.

When a student has ≥3 prediction history points, uses real trend data.
Otherwise synthesises a plausible trajectory from current features.

Note: Prophet is used when available (best quality), with a lightweight
exponential smoothing fallback when Prophet is not installed.
"""

from __future__ import annotations

import json
import logging
import math
from datetime import datetime, timezone, timedelta
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


def _exponential_smoothing_forecast(
    scores: list[float],
    n_ahead: int = 4,
    alpha: float = 0.4,
) -> list[float]:
    """
    Simple exponential smoothing with trend correction.
    alpha = smoothing factor (0=slow, 1=reactive)
    """
    if not scores:
        return []

    # Level + trend initialisation
    level = scores[0]
    trend = 0.0
    beta  = 0.3  # trend smoothing

    if len(scores) >= 2:
        trend = scores[1] - scores[0]

    # Run through history to get final level + trend
    for s in scores[1:]:
        new_level = alpha * s + (1 - alpha) * (level + trend)
        new_trend = beta * (new_level - level) + (1 - beta) * trend
        level, trend = new_level, new_trend

    # Project forward
    forecasts = []
    for h in range(1, n_ahead + 1):
        f = level + h * trend
        f = max(0.0, min(1.0, f))  # clamp to [0,1]
        forecasts.append(round(f, 4))

    return forecasts


def _prophet_forecast(
    dates: list[datetime],
    scores: list[float],
    n_ahead: int = 4,
    period_days: int = 7,
) -> list[float]:
    """
    Use Facebook Prophet for trend + seasonality forecasting.
    Falls back to exponential smoothing if Prophet unavailable.
    """
    try:
        from prophet import Prophet
        import pandas as pd

        df = pd.DataFrame({"ds": dates, "y": scores})
        m = Prophet(
            changepoint_prior_scale=0.3,
            seasonality_mode="additive",
            weekly_seasonality=False,
            daily_seasonality=False,
            yearly_seasonality=False,
        )
        m.fit(df)

        last_date = max(dates)
        future_dates = [last_date + timedelta(days=period_days * (i + 1)) for i in range(n_ahead)]
        future_df = pd.DataFrame({"ds": future_dates})
        forecast  = m.predict(future_df)

        raw = forecast["yhat"].tolist()
        return [round(max(0.0, min(1.0, v)), 4) for v in raw]

    except Exception as exc:
        logger.warning("Prophet forecast failed (%s) — using exponential smoothing", exc)
        return _exponential_smoothing_forecast(scores, n_ahead)


def forecast_student_risk(
    student_id: int,
    current_score: float,
    prediction_history: list[dict],          # [{"risk_score": float, "created_at": str}, ...]
    n_weeks_ahead: int = 4,
) -> dict:
    """
    Forecast a student's risk score for the next N weeks.

    Parameters
    ----------
    student_id        : int
    current_score     : float — latest known risk score
    prediction_history: list of historical predictions (ordered by date)
    n_weeks_ahead     : how many weeks to forecast

    Returns
    -------
    dict with historical trajectory + forecast + trend interpretation
    """
    # ── Parse history ─────────────────────────────────────────────────────
    historical_scores = []
    historical_dates  = []

    if prediction_history:
        for p in prediction_history[-12:]:  # last 12 weeks max
            try:
                score = float(p.get("risk_score", current_score))
                dt_str = p.get("created_at", "")
                if dt_str:
                    dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                    historical_dates.append(dt)
                    historical_scores.append(score)
            except Exception:
                continue

    # If no valid history, create a synthetic 6-week history ending at current
    if len(historical_scores) < 2:
        import random
        rng = random.Random(student_id)
        n_hist = 6
        start_offset = rng.uniform(0.05, 0.18)
        start = max(0.05, min(0.95, current_score - start_offset * (1 if current_score > 0.5 else -1)))
        now = datetime.now(timezone.utc)
        for i in range(n_hist):
            t = i / (n_hist - 1)
            s = start + (current_score - start) * (t ** 1.4)
            s += rng.uniform(-0.02, 0.02)
            s = round(max(0.0, min(1.0, s)), 4)
            historical_scores.append(s)
            historical_dates.append(now - timedelta(weeks=(n_hist - 1 - i)))
        synthetic_history = True
    else:
        synthetic_history = False

    # ── Forecast ──────────────────────────────────────────────────────────
    if len(historical_scores) >= 3 and historical_dates:
        forecasted = _prophet_forecast(historical_dates, historical_scores, n_weeks_ahead)
    else:
        forecasted = _exponential_smoothing_forecast(historical_scores, n_weeks_ahead)

    # ── Trend interpretation ───────────────────────────────────────────────
    if len(forecasted) >= 2:
        trend_direction = forecasted[-1] - historical_scores[-1]
    else:
        trend_direction = 0.0

    if trend_direction > 0.05:
        trend_label = "WORSENING"
        trend_description = "Risk is projected to increase significantly over the next 4 weeks."
        trend_color = "#f43f5e"
    elif trend_direction > 0.01:
        trend_label = "SLIGHTLY_WORSENING"
        trend_description = "Risk shows a mild upward trend — monitor closely."
        trend_color = "#f59e0b"
    elif trend_direction < -0.05:
        trend_label = "IMPROVING"
        trend_description = "Risk is projected to decrease — current interventions may be working."
        trend_color = "#10b981"
    elif trend_direction < -0.01:
        trend_label = "SLIGHTLY_IMPROVING"
        trend_description = "Risk shows a mild downward trend."
        trend_color = "#6366f1"
    else:
        trend_label = "STABLE"
        trend_description = "Risk is stable — maintain current monitoring cadence."
        trend_color = "#94a3b8"

    # ── Build response ────────────────────────────────────────────────────
    now = datetime.now(timezone.utc)
    history_out = [
        {"week": f"Wk {i+1}", "risk_score": s, "real": not synthetic_history, "type": "historical"}
        for i, s in enumerate(historical_scores)
    ]
    forecast_out = [
        {
            "week": f"Wk {len(historical_scores) + i + 1}",
            "risk_score": f,
            "real": False,
            "type": "forecast",
            "date": (now + timedelta(weeks=i + 1)).strftime("%d %b"),
        }
        for i, f in enumerate(forecasted)
    ]

    return {
        "student_id":         student_id,
        "current_risk_score": round(current_score, 4),
        "history_weeks":      len(historical_scores),
        "synthetic_history":  synthetic_history,
        "forecast_weeks":     n_weeks_ahead,
        "historical":         history_out,
        "forecast":           forecast_out,
        "combined":           history_out + forecast_out,
        "trend": {
            "label":       trend_label,
            "description": trend_description,
            "color":       trend_color,
            "delta":       round(float(trend_direction), 4),
        },
        "youden_threshold": 0.4432,
        "method": "prophet" if len(historical_scores) >= 3 else "exponential_smoothing",
    }
