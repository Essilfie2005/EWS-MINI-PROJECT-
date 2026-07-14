"""
V3 Training + Analytics Runner
Run after backend is up: backend\venv\Scripts\python.exe run_v3_training.py
"""
import sys, time, json
sys.stdout.reconfigure(encoding='utf-8')
import requests

BASE = "http://localhost:8000/api"

def wait_ready(timeout=30):
    for i in range(timeout):
        try:
            r = requests.get(f"{BASE}/dashboard/health", timeout=3)
            if r.status_code == 200:
                print(f"Backend ready ({i+1}s)")
                return True
        except Exception:
            pass
        time.sleep(1)
    print("Backend not ready")
    return False

if not wait_ready():
    sys.exit(1)

print()
print("=" * 55)
print("   V3 TRAINING PIPELINE")
print("=" * 55)

# 1. Trigger ensemble training (background task)
print("\n[1/4] Starting ensemble training (background)...")
r = requests.post(f"{BASE}/predictions/train-ensemble", timeout=10)
print(f"  Status: {r.status_code}")
if r.status_code == 200:
    d = r.json()
    print(f"  n_samples={d.get('n_samples')}, learners={d.get('base_learners')}")
else:
    print(f"  Error: {r.text[:100]}")

# 2. Run CV (synchronous, takes ~60s)
print("\n[2/4] Running 5-fold cross-validation (~60s)...")
r = requests.post(f"{BASE}/dashboard/compute-cv", timeout=120)
print(f"  Status: {r.status_code}")
if r.status_code == 200:
    d = r.json()
    m = d.get("metrics", {})
    print(f"  AUC  = {m.get('auc',{}).get('mean',0):.4f} +/- {m.get('auc',{}).get('std',0):.4f}")
    print(f"  F1   = {m.get('f1',{}).get('mean',0):.4f} +/- {m.get('f1',{}).get('std',0):.4f}")
    print(f"  Prec = {m.get('precision',{}).get('mean',0):.4f} +/- {m.get('precision',{}).get('std',0):.4f}")
else:
    print(f"  Error: {r.text[:100]}")

# 3. Run PDP (synchronous, takes ~30s)
print("\n[3/4] Computing Partial Dependence Plots (~30s)...")
r = requests.post(f"{BASE}/dashboard/compute-pdp", timeout=90)
print(f"  Status: {r.status_code}")
if r.status_code == 200:
    d = r.json()
    feats = list(d.get("features", {}).keys())
    print(f"  PDP computed for: {feats}")
else:
    print(f"  Error: {r.text[:100]}")

# 4. Run learning curve (~60s)
print("\n[4/4] Computing learning curve (~60s)...")
r = requests.post(f"{BASE}/dashboard/compute-learning-curve", timeout=120)
print(f"  Status: {r.status_code}")
if r.status_code == 200:
    d = r.json()
    curve = d.get("curve", [])
    if curve:
        first = curve[0]
        last  = curve[-1]
        print(f"  10% training: AUC={first.get('test_auc')}, F1={first.get('test_f1')}")
        print(f"  100% training: AUC={last.get('test_auc')}, F1={last.get('test_f1')}")
else:
    print(f"  Error: {r.text[:100]}")

# 5. Wait for ensemble then check results
print("\n[Waiting 3min for background ensemble training to complete...]")
time.sleep(180)
r = requests.get(f"{BASE}/dashboard/ensemble-metrics", timeout=10)
print(f"\n[Ensemble results] Status: {r.status_code}")
if r.status_code == 200:
    d = r.json()
    em = d.get("ensemble_metrics", {})
    imp = d.get("improvement_over_v2_pct", {})
    print(f"  Ensemble AUC   = {em.get('auc')}")
    print(f"  Ensemble F1    = {em.get('f1')}")
    print(f"  Ensemble Kappa = {em.get('kappa')}")
    print()
    print(f"  Improvement over V2 XGBoost:")
    for k, v in imp.items():
        sign = "+" if v >= 0 else ""
        print(f"    {k}: {sign}{v}%")
    print()
    ind = d.get("individual_metrics", {})
    print("  Individual base learner AUCs:")
    for name, metrics in ind.items():
        print(f"    {name}: AUC={metrics.get('auc')}, F1={metrics.get('f1')}")
else:
    print(f"  {r.text[:150]}")

print()
print("=" * 55)
print("   V3 TRAINING COMPLETE")
print("=" * 55)
