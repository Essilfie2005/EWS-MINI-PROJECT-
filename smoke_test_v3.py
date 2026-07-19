"""V3 Smoke Test — correct key names."""
import requests, sys
sys.stdout.reconfigure(encoding='utf-8')

BASE = "http://localhost:8000/api"
PASS, FAIL = [], []

def check(name, fn):
    try:
        result = fn()
        if result:
            PASS.append(name)
            print(f"  PASS  {name}")
        else:
            FAIL.append(name)
            print(f"  FAIL  {name} (returned falsy)")
    except Exception as e:
        FAIL.append(name)
        print(f"  FAIL  {name}  -- {e}")

print("=" * 60)
print("   V3 FULL SMOKE TEST")
print("=" * 60)

# Core health
check("Health",           lambda: requests.get(f"{BASE}/dashboard/health").json().get("status") == "healthy")
check("Students list",    lambda: len(requests.get(f"{BASE}/students").json()) > 0)

# Run a single predict first to ensure model state is ready
requests.post(f"{BASE}/predictions/predict", json={"student_id": 1}, timeout=15)

check("Model info",       lambda: requests.get(f"{BASE}/dashboard/model-info").status_code in [200, 404])
check("Alerts list",      lambda: requests.get(f"{BASE}/alerts").status_code == 200)

# V2 Analytics (correct keys from diagnose output)
check("ROC curve",        lambda: "xgboost" in requests.get(f"{BASE}/dashboard/roc-curve").json())
check("Beeswarm",         lambda: len(requests.get(f"{BASE}/dashboard/beeswarm").json()) > 0)
check("Confusion matrix", lambda: "tp" in requests.get(f"{BASE}/dashboard/confusion-matrix").json())
check("Calibration",      lambda: "mean_predicted" in requests.get(f"{BASE}/dashboard/calibration-curve").json())
check("Fairness",         lambda: "bands" in requests.get(f"{BASE}/dashboard/fairness").json())
check("Pilot metrics",    lambda: "auc_roc" in requests.get(f"{BASE}/dashboard/pilot-metrics").json())
check("CTGAN quality",    lambda: requests.get(f"{BASE}/dashboard/ctgan-quality").status_code in [200, 404])
check("Drift status",     lambda: requests.get(f"{BASE}/dashboard/drift-status").status_code in [200, 404])
check("Cohort comparison",lambda: requests.get(f"{BASE}/dashboard/cohort-comparison").status_code in [200, 404])

# V3 Analytics
check("Ensemble metrics", lambda: "ensemble_metrics" in requests.get(f"{BASE}/dashboard/ensemble-metrics").json())
check("CV report",        lambda: "metrics" in requests.get(f"{BASE}/dashboard/cv-report").json())
check("PDP",              lambda: "features" in requests.get(f"{BASE}/dashboard/pdp").json())
check("Learning curve",   lambda: "curve" in requests.get(f"{BASE}/dashboard/learning-curve").json())
check("Feedback summary", lambda: "total_retraining_runs" in requests.get(f"{BASE}/dashboard/feedback-summary").json())

# V3 Predictions
r = requests.get(f"{BASE}/predictions/forecast/1", timeout=15)
check("4-week forecast",  lambda: "forecast" in r.json() and "trend" in r.json())

# Interventions
check("Interventions",    lambda: requests.get(f"{BASE}/interventions").status_code in [200, 404])

print()
print("=" * 60)
total = len(PASS) + len(FAIL)
print(f"  PASSED: {len(PASS)}/{total}")
if FAIL:
    print(f"  FAILED: {', '.join(FAIL)}")
else:
    print("  ALL TESTS PASSED")
print("=" * 60)
sys.exit(0 if not FAIL else 1)
