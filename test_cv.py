import requests, sys, time
sys.stdout.reconfigure(encoding='utf-8')

BASE = "http://localhost:8000/api"

# Wait for backend
for i in range(20):
    try:
        requests.get(BASE + "/dashboard/health", timeout=3)
        print(f"Backend ready ({i+1}s)")
        break
    except:
        time.sleep(1)

print("\nRunning CV report...")
r = requests.post(BASE + "/dashboard/compute-cv", timeout=120)
print("CV Status:", r.status_code)
if r.status_code == 200:
    d = r.json()
    m = d.get("metrics", {})
    auc  = m.get("auc",  {})
    f1   = m.get("f1",   {})
    prec = m.get("precision", {})
    rec  = m.get("recall", {})
    print(f"  AUC       = {auc.get('mean'):.4f}  CI [{auc.get('ci_lower'):.4f}, {auc.get('ci_upper'):.4f}]")
    print(f"  F1        = {f1.get('mean'):.4f}  CI [{f1.get('ci_lower'):.4f}, {f1.get('ci_upper'):.4f}]")
    print(f"  Precision = {prec.get('mean'):.4f}")
    print(f"  Recall    = {rec.get('mean'):.4f}")
    print(f"  Per-fold AUCs: {auc.get('per_fold')}")
    print("\nCV PASS")
else:
    print("Error:", r.text[:300])
    sys.exit(1)
