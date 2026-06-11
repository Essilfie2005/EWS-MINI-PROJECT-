"""
Evaluation metrics used across ML pipelines and API responses.
"""

from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    cohen_kappa_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    auc as sklearn_auc,
)


def compute_all_metrics(y_true: np.ndarray, y_pred: np.ndarray, y_prob: np.ndarray) -> dict:
    """
    Compute the full suite of classification metrics.

    Parameters
    ----------
    y_true : array-like of int  – ground-truth labels (0/1).
    y_pred : array-like of int  – predicted labels (0/1).
    y_prob : array-like of float – predicted probabilities for class 1.

    Returns
    -------
    dict with keys: auc_roc, f1_score, pr_auc, cohen_kappa,
                    accuracy, precision, recall, confusion_matrix.
    """
    y_true = np.asarray(y_true, dtype=int)
    y_pred = np.asarray(y_pred, dtype=int)
    y_prob = np.asarray(y_prob, dtype=float)

    prec_curve, rec_curve, _ = precision_recall_curve(y_true, y_prob)
    pr_auc_val = sklearn_auc(rec_curve, prec_curve)

    cm = confusion_matrix(y_true, y_pred).tolist()

    return {
        "auc_roc": float(roc_auc_score(y_true, y_prob)),
        "f1_score": float(f1_score(y_true, y_pred, pos_label=1)),
        "pr_auc": float(pr_auc_val),
        "cohen_kappa": float(cohen_kappa_score(y_true, y_pred)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, pos_label=1, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, pos_label=1, zero_division=0)),
        "confusion_matrix": cm,
    }


def delong_test(y_true: np.ndarray, y_prob_a: np.ndarray, y_prob_b: np.ndarray) -> dict:
    """
    DeLong's test for comparing two AUC-ROC scores.

    Implements the fast algorithm from Sun & Xu (2014).

    Returns
    -------
    dict with keys: auc_a, auc_b, z_statistic, p_value.
    """
    from scipy import stats

    y_true = np.asarray(y_true, dtype=int)
    y_prob_a = np.asarray(y_prob_a, dtype=float)
    y_prob_b = np.asarray(y_prob_b, dtype=float)

    # Split into positive and negative groups
    pos_idx = np.where(y_true == 1)[0]
    neg_idx = np.where(y_true == 0)[0]
    n_pos = len(pos_idx)
    n_neg = len(neg_idx)

    if n_pos == 0 or n_neg == 0:
        return {"auc_a": 0.0, "auc_b": 0.0, "z_statistic": 0.0, "p_value": 1.0}

    def _structural_components(y_prob: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Compute placement values (structural components) for DeLong."""
        pos_scores = y_prob[pos_idx]
        neg_scores = y_prob[neg_idx]

        # V10: for each positive, fraction of negatives it beats
        v10 = np.array([
            np.mean((neg_scores < ps).astype(float) + 0.5 * (neg_scores == ps).astype(float))
            for ps in pos_scores
        ])

        # V01: for each negative, fraction of positives it loses to
        v01 = np.array([
            np.mean((pos_scores > ns).astype(float) + 0.5 * (pos_scores == ns).astype(float))
            for ns in neg_scores
        ])

        return v10, v01

    v10_a, v01_a = _structural_components(y_prob_a)
    v10_b, v01_b = _structural_components(y_prob_b)

    auc_a = np.mean(v10_a)
    auc_b = np.mean(v10_b)

    # Covariance matrix of the two AUC estimates
    s10 = np.cov(v10_a, v10_b)
    s01 = np.cov(v01_a, v01_b)

    # Handle scalar case for np.cov
    if s10.ndim == 0:
        s10 = np.array([[float(s10)]])
    if s01.ndim == 0:
        s01 = np.array([[float(s01)]])

    s = s10 / n_pos + s01 / n_neg

    # Difference
    diff = auc_a - auc_b
    var_diff = s[0, 0] + s[1, 1] - 2 * s[0, 1]

    if var_diff <= 0:
        return {"auc_a": float(auc_a), "auc_b": float(auc_b), "z_statistic": 0.0, "p_value": 1.0}

    z = diff / np.sqrt(var_diff)
    p_value = 2 * stats.norm.sf(abs(z))

    return {
        "auc_a": float(auc_a),
        "auc_b": float(auc_b),
        "z_statistic": float(z),
        "p_value": float(p_value),
    }


def assign_risk_band(score: float, threshold: float = 0.5) -> str:
    """Map a probability score to LOW / MEDIUM / HIGH band."""
    if score >= threshold:
        return "HIGH"
    elif score >= threshold * 0.6:
        return "MEDIUM"
    else:
        return "LOW"
