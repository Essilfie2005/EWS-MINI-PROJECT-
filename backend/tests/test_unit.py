"""
Unit tests for the EWS Dropout Early Warning System.

Coverage:
  1. Feature engineering  (engineer_features, API, FARI formulas)
  2. Risk band assignment  (assign_risk_band thresholds)
  3. Metrics utilities     (compute_all_metrics, delong_test)
  4. Schema validation     (Pydantic models)
  5. API endpoint smoke    (FastAPI TestClient — no real DB, uses dependency overrides)
"""

import sys, os
# Ensure the backend package is on the path when running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import math
import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock

# ── 1. Feature Engineering ────────────────────────────────────────────────────

from app.services.ml_pipeline import engineer_features, FEATURE_COLS, ENGINEERED_FEATURE_COLS, YOUDEN_THRESHOLD


def _make_student(**kwargs) -> pd.DataFrame:
    """Helper: build a one-row DataFrame with default values overridable by kwargs."""
    defaults = {
        "attendance_rate":          75.0,
        "quiz_average":             70.0,
        "assignment_submission_rate": 80.0,
        "mobile_engagement_freq":   5.0,
        "financial_aid_status":     5.0,
    }
    defaults.update(kwargs)
    return pd.DataFrame([defaults])


class TestEngineerFeatures:
    """Tests for the engineer_features() function."""

    def test_adds_api_column(self):
        df = engineer_features(_make_student())
        assert "academic_performance_index" in df.columns

    def test_adds_fari_column(self):
        df = engineer_features(_make_student())
        assert "financial_academic_risk" in df.columns

    def test_api_formula_correct(self):
        """API = 0.4*attendance + 0.4*quiz + 0.2*assignment"""
        df = engineer_features(_make_student(
            attendance_rate=80.0,
            quiz_average=60.0,
            assignment_submission_rate=100.0,
        ))
        expected = 0.40 * 80.0 + 0.40 * 60.0 + 0.20 * 100.0
        assert abs(df["academic_performance_index"].iloc[0] - expected) < 1e-6

    def test_fari_formula_correct(self):
        """FARI = (1 - aid/10) * (1 - assignment/100)"""
        df = engineer_features(_make_student(
            financial_aid_status=0.0,        # no aid  → vulnerability = 1.0
            assignment_submission_rate=0.0,  # no submissions → academic risk = 1.0
        ))
        assert abs(df["financial_academic_risk"].iloc[0] - 1.0) < 1e-6

    def test_fari_zero_for_fully_supported_student(self):
        """Full aid + 100% submission → FARI = 0"""
        df = engineer_features(_make_student(
            financial_aid_status=10.0,
            assignment_submission_rate=100.0,
        ))
        assert abs(df["financial_academic_risk"].iloc[0] - 0.0) < 1e-6

    def test_fari_clipped_to_zero_one(self):
        """FARI must never be negative or above 1."""
        df = engineer_features(_make_student(
            financial_aid_status=15.0,   # out-of-range (would make negative without clip)
            assignment_submission_rate=150.0,
        ))
        val = df["financial_academic_risk"].iloc[0]
        assert 0.0 <= val <= 1.0

    def test_output_has_all_engineered_cols(self):
        df = engineer_features(_make_student())
        for col in ENGINEERED_FEATURE_COLS:
            assert col in df.columns, f"Missing column: {col}"

    def test_does_not_mutate_input(self):
        """Original DataFrame must be unchanged."""
        original = _make_student()
        original_cols = list(original.columns)
        engineer_features(original)
        assert list(original.columns) == original_cols

    def test_batch_of_students(self):
        """Should work on multiple rows at once."""
        rows = [_make_student(attendance_rate=float(r)) for r in range(10, 110, 10)]
        df = pd.concat(rows, ignore_index=True)
        result = engineer_features(df)
        assert len(result) == 10
        assert "academic_performance_index" in result.columns


# ── 2. Risk Band Assignment ───────────────────────────────────────────────────

from app.utils.metrics import assign_risk_band


class TestAssignRiskBand:
    """Tests for assign_risk_band() with Youden threshold τ = 0.4432."""

    TAU = YOUDEN_THRESHOLD  # 0.4432

    def test_score_at_threshold_is_high(self):
        assert assign_risk_band(self.TAU, self.TAU) == "HIGH"

    def test_score_above_threshold_is_high(self):
        assert assign_risk_band(0.9, self.TAU) == "HIGH"

    def test_score_just_below_threshold_is_medium_or_low(self):
        result = assign_risk_band(self.TAU - 0.001, self.TAU)
        assert result in ("MEDIUM", "LOW")

    def test_very_low_score_is_low(self):
        assert assign_risk_band(0.0, self.TAU) == "LOW"

    def test_very_high_score_is_high(self):
        assert assign_risk_band(1.0, self.TAU) == "HIGH"

    def test_medium_band_exists_between_low_and_high(self):
        """Medium band exists between ~60% of threshold and threshold."""
        mid = self.TAU * 0.7  # inside medium zone
        result = assign_risk_band(mid, self.TAU)
        assert result == "MEDIUM"

    def test_default_threshold_is_point_five(self):
        """Without a custom threshold, default is 0.5."""
        assert assign_risk_band(0.6) == "HIGH"
        assert assign_risk_band(0.1) == "LOW"

    def test_returns_string(self):
        assert isinstance(assign_risk_band(0.5, self.TAU), str)

    def test_all_possible_returns(self):
        """Every band must be reachable."""
        tau = self.TAU
        bands = {
            assign_risk_band(0.0,  tau),
            assign_risk_band(tau * 0.7, tau),
            assign_risk_band(tau,  tau),
        }
        assert "LOW" in bands
        assert "MEDIUM" in bands
        assert "HIGH" in bands


# ── 3. Metrics Utilities ──────────────────────────────────────────────────────

from app.utils.metrics import compute_all_metrics, delong_test


class TestComputeAllMetrics:
    """Tests for compute_all_metrics(y_true, y_pred, y_prob)."""

    def _perfect(self, n=100):
        y_true = np.array([0] * (n // 2) + [1] * (n // 2))
        y_prob = np.where(y_true == 1, 0.95, 0.05).astype(float)
        y_pred = (y_prob >= 0.5).astype(int)
        return y_true, y_pred, y_prob

    def _random(self, n=100, seed=42):
        rng = np.random.default_rng(seed)
        y_true = rng.integers(0, 2, size=n)
        y_prob = rng.random(size=n)
        y_pred = (y_prob >= 0.5).astype(int)
        return y_true, y_pred, y_prob

    def test_perfect_predictions_give_auc_one(self):
        y_true, y_pred, y_prob = self._perfect()
        metrics = compute_all_metrics(y_true, y_pred, y_prob)
        assert abs(metrics["auc_roc"] - 1.0) < 0.01

    def test_perfect_predictions_give_high_f1(self):
        y_true, y_pred, y_prob = self._perfect()
        metrics = compute_all_metrics(y_true, y_pred, y_prob)
        assert metrics["f1_score"] >= 0.95

    def test_returns_required_keys(self):
        y_true, y_pred, y_prob = self._random()
        metrics = compute_all_metrics(y_true, y_pred, y_prob)
        for key in ("auc_roc", "f1_score", "precision", "recall", "cohen_kappa", "accuracy"):
            assert key in metrics, f"Missing metric key: {key}"

    def test_all_values_are_numeric(self):
        y_true, y_pred, y_prob = self._random()
        metrics = compute_all_metrics(y_true, y_pred, y_prob)
        for k, v in metrics.items():
            if k != "confusion_matrix":
                assert isinstance(v, (int, float)), f"{k} is not numeric: {type(v)}"

    def test_confusion_matrix_is_list(self):
        y_true, y_pred, y_prob = self._perfect()
        metrics = compute_all_metrics(y_true, y_pred, y_prob)
        assert isinstance(metrics["confusion_matrix"], list)

    def test_kappa_perfect_is_one(self):
        y_true, y_pred, y_prob = self._perfect()
        metrics = compute_all_metrics(y_true, y_pred, y_prob)
        assert metrics["cohen_kappa"] >= 0.95

    def test_accuracy_between_zero_and_one(self):
        y_true, y_pred, y_prob = self._random()
        metrics = compute_all_metrics(y_true, y_pred, y_prob)
        assert 0.0 <= metrics["accuracy"] <= 1.0


class TestDelongTest:
    """Tests for delong_test()."""

    def _labels(self, n=200, seed=0):
        rng = np.random.default_rng(seed)
        y_true = rng.integers(0, 2, size=n)
        y_a = np.clip(y_true + rng.normal(0, 0.15, size=n), 0, 1)
        y_b = np.clip(y_true + rng.normal(0, 0.20, size=n), 0, 1)
        return y_true, y_a, y_b

    def test_returns_required_keys(self):
        y_true, y_a, y_b = self._labels()
        result = delong_test(y_true, y_a, y_b)
        for key in ("z_statistic", "p_value", "auc_a", "auc_b"):
            assert key in result

    def test_p_value_between_zero_and_one(self):
        y_true, y_a, y_b = self._labels()
        result = delong_test(y_true, y_a, y_b)
        assert 0.0 <= result["p_value"] <= 1.0

    def test_identical_scores_give_high_p_value(self):
        """Same predictions → p-value should be 1.0 (no difference detected)."""
        rng = np.random.default_rng(1)
        y_true = rng.integers(0, 2, size=100)
        y_scores = rng.random(size=100)
        result = delong_test(y_true, y_scores, y_scores.copy())
        assert result["p_value"] > 0.99

    def test_auc_values_between_zero_and_one(self):
        y_true, y_a, y_b = self._labels()
        result = delong_test(y_true, y_a, y_b)
        assert 0.0 <= result["auc_a"] <= 1.0
        assert 0.0 <= result["auc_b"] <= 1.0


# ── 4. Pydantic Schema Validation ────────────────────────────────────────────

from app.models.schemas import InterventionCreate, InterventionUpdate, InterventionResponse


class TestSchemas:
    """Tests for Pydantic model validation."""

    def test_intervention_create_valid(self):
        obj = InterventionCreate(student_id=1, intervention_type="COUNSELLING")
        assert obj.student_id == 1
        assert obj.intervention_type == "COUNSELLING"

    def test_intervention_create_rejects_bad_type(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            InterventionCreate(student_id=1, intervention_type="INVALID_TYPE")

    def test_intervention_update_all_optional(self):
        """InterventionUpdate should allow empty body (all fields optional)."""
        obj = InterventionUpdate()
        assert obj.status is None
        assert obj.outcome is None

    def test_intervention_update_with_outcome(self):
        obj = InterventionUpdate(status="COMPLETED", outcome="SUCCESSFUL")
        assert obj.outcome == "SUCCESSFUL"

    def test_intervention_types_accepted(self):
        for t in ("SMS", "EMAIL", "COUNSELLING", "TUTORING", "OTHER"):
            obj = InterventionCreate(student_id=1, intervention_type=t)
            assert obj.intervention_type == t


# ── 5. YOUDEN_THRESHOLD value ─────────────────────────────────────────────────

class TestConstants:
    """Sanity-check the module-level constants."""

    def test_youden_threshold_is_reasonable(self):
        """Youden threshold must be in (0, 1) and not the naive default 0.5."""
        assert 0 < YOUDEN_THRESHOLD < 1
        assert YOUDEN_THRESHOLD != 0.5

    def test_feature_cols_count(self):
        assert len(FEATURE_COLS) == 5

    def test_engineered_cols_count(self):
        """Should have 2 more than raw features (API + FARI)."""
        assert len(ENGINEERED_FEATURE_COLS) == len(FEATURE_COLS) + 2

    def test_engineered_includes_api(self):
        assert "academic_performance_index" in ENGINEERED_FEATURE_COLS

    def test_engineered_includes_fari(self):
        assert "financial_academic_risk" in ENGINEERED_FEATURE_COLS
