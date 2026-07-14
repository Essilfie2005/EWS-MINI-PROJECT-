"""
EWS V2 — Full End-to-End Test Suite
======================================
Tests every endpoint (original + v2) and reports pass/fail.
Run from the project root after the backend is up on port 8000.

    backend\\venv\\Scripts\\python.exe full_test_v2.py
"""

import sys, json, time
sys.stdout.reconfigure(encoding='utf-8')

import requests

BASE = "http://localhost:8000/api"
RESULTS = []

def test(name, method, path, payload=None, expect_status=200, check_keys=None):
    url = BASE + path
    try:
        if method == "GET":
            r = requests.get(url, timeout=20)
        elif method == "POST":
            r = requests.post(url, json=payload or {}, timeout=20)
        elif method == "DELETE":
            r = requests.delete(url, timeout=20)
        else:
            r = requests.request(method, url, json=payload, timeout=20)

        ok = r.status_code == expect_status
        detail = ""

        if ok and check_keys and "application/json" in r.headers.get("content-type", ""):
            d = r.json()
            for k in check_keys:
                if k not in (d if isinstance(d, dict) else {}):
                    ok = False
                    detail = f"missing key '{k}'"
                    break
            if ok and isinstance(d, dict) and check_keys:
                first_val = d.get(check_keys[0])
                detail = f"{check_keys[0]}={json.dumps(first_val)[:60]}"

        elif ok and "application/pdf" in r.headers.get("content-type", ""):
            detail = f"PDF {len(r.content)} bytes"

        elif not ok:
            detail = r.text[:80]

        RESULTS.append((ok, name, r.status_code, detail))

    except Exception as e:
        RESULTS.append((False, name, "ERR", str(e)[:80]))


# ── Wait for server ─────────────────────────────────────────────────────────
print("Waiting for backend to be ready...")
for i in range(20):
    try:
        requests.get(BASE + "/dashboard/health", timeout=3)
        print(f"  Backend ready after {i+1}s")
        break
    except:
        time.sleep(1)
else:
    print("  Backend did not respond in 20s — aborting")
    sys.exit(1)

print()
print("=" * 65)
print("   EWS V2 — FULL ENDPOINT TEST SUITE")
print("=" * 65)

# ── V1 core endpoints ────────────────────────────────────────────────────────
print("\n[CORE ENDPOINTS]")
test("Health Check",           "GET",  "/dashboard/health",        check_keys=["status"])
test("Dashboard Summary",      "GET",  "/dashboard/summary",       check_keys=["total_students"])
test("Risk Distribution",      "GET",  "/dashboard/risk-distribution")
test("Model Metrics",          "GET",  "/dashboard/model-metrics")
test("Feature Importance",     "GET",  "/dashboard/feature-importance", check_keys=["feature_importance"])
test("Student List",           "GET",  "/students/",               check_keys=["students"])
test("Student Detail (id=1)",  "GET",  "/students/1",              check_keys=["id"])
test("Prediction (student 1)", "POST", "/predictions/predict",     payload={"student_id": 1}, check_keys=["risk_score"])
test("Interventions List",     "GET",  "/interventions/",          check_keys=["interventions"])
test("Alerts List",            "GET",  "/alerts/",                 check_keys=["alerts"])

# ── V2 analytics endpoints ───────────────────────────────────────────────────
print("\n[V2 ANALYTICS ENDPOINTS]")
test("Confusion Matrix",       "GET",  "/dashboard/confusion-matrix",  check_keys=["tp", "fp", "tn", "fn"])
test("Calibration Curve",      "GET",  "/dashboard/calibration-curve", check_keys=["mean_predicted"])
test("Fairness Analysis",      "GET",  "/dashboard/fairness",          check_keys=["bands"])
test("CTGAN Quality",          "GET",  "/dashboard/ctgan-quality",     check_keys=["ks_complement", "correlation_similarity"])
test("DeLong Test",            "GET",  "/dashboard/delong-test",       check_keys=["xgb_auc", "lr_auc", "p_value"])
test("Cohort Comparison",      "GET",  "/dashboard/cohort-comparison", check_keys=["current", "previous", "change_pct"])
test("Drift Status",           "GET",  "/dashboard/drift",             check_keys=["current_status"])

# ── V2 prediction endpoints ──────────────────────────────────────────────────
print("\n[V2 PREDICTION ENDPOINTS]")
test("Risk Trajectory (s=1)",  "GET",  "/predictions/trajectory/1",   check_keys=["trajectory", "youden_threshold"])
test("Count at Threshold",     "GET",  "/predictions/count-at-threshold?tau=0.4432", check_keys=["flagged", "total", "pct_flagged"])
test("PDF Brief (s=1)",        "GET",  "/predictions/pdf/1",          expect_status=200)

# ── V2 SMS endpoint ──────────────────────────────────────────────────────────
print("\n[V2 SMS / ALERTS]")
test("Send SMS Alert",         "POST", "/alerts/send-sms",
     payload={"student_id": 1, "phone_numbers": ["+233241234567"]},
     check_keys=["message", "sms_result"])

# ── SHAP explanation ─────────────────────────────────────────────────────────
print("\n[SHAP EXPLANATION]")
test("Predict + SHAP (s=1)",   "POST", "/predictions/predict",
     payload={"student_id": 1},
     check_keys=["shap_values"])

# ── Print results ─────────────────────────────────────────────────────────────
print()
print("=" * 65)
print("   RESULTS")
print("=" * 65)
passed = failed = 0
for ok, name, status, detail in RESULTS:
    icon = "PASS" if ok else "FAIL"
    print(f"  [{icon}] {name:<35} HTTP {status}  {detail}")
    if ok:
        passed += 1
    else:
        failed += 1

print()
print(f"  {passed}/{passed+failed} passed  |  {failed} failed")
print("=" * 65)

if failed > 0:
    sys.exit(1)
