"""
Baseline models for comparison against XGBoost.

1. Logistic Regression (scikit-learn defaults)
2. Rule-based: flag if attendance < 60% AND quiz_avg < 40%
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


def train_logistic_regression(
    X_train: np.ndarray,
    y_train: np.ndarray,
) -> tuple[LogisticRegression, StandardScaler]:
    """
    Train a Logistic Regression baseline with scikit-learn defaults.

    Returns (fitted_model, fitted_scaler).
    """
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_train)

    model = LogisticRegression(
        max_iter=1000,
        random_state=42,
        solver="lbfgs",
    )
    model.fit(X_scaled, y_train)

    logger.info(
        "Logistic Regression trained: %d samples, %d features",
        X_train.shape[0], X_train.shape[1],
    )

    return model, scaler


def rule_based_predict(
    df: pd.DataFrame,
    attendance_threshold: float = 60.0,
    quiz_threshold: float = 40.0,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Simple rule-based baseline:
      Flag as dropout if attendance_rate < 60% AND quiz_average < 40%.

    Parameters
    ----------
    df : DataFrame with columns 'attendance_rate' and 'quiz_average'
    attendance_threshold : float, threshold for attendance (default 60%)
    quiz_threshold : float, threshold for quiz average (default 40%)

    Returns
    -------
    (y_pred, y_prob) – binary predictions and pseudo-probabilities
    """
    attendance = df["attendance_rate"].values
    quiz = df["quiz_average"].values

    y_pred = ((attendance < attendance_threshold) & (quiz < quiz_threshold)).astype(int)

    # Generate pseudo-probabilities based on how far below thresholds
    attendance_score = np.clip((attendance_threshold - attendance) / attendance_threshold, 0, 1)
    quiz_score = np.clip((quiz_threshold - quiz) / quiz_threshold, 0, 1)
    y_prob = np.clip((attendance_score + quiz_score) / 2, 0, 1)

    # Ensure flagged students get prob >= 0.5
    y_prob = np.where(y_pred == 1, np.maximum(y_prob, 0.5), np.minimum(y_prob, 0.49))

    logger.info(
        "Rule-based: %d flagged out of %d (%.1f%%)",
        y_pred.sum(), len(y_pred), y_pred.mean() * 100,
    )

    return y_pred, y_prob
