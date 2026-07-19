"""Diagnose the 6 failing endpoints."""
import requests, sys, json
sys.stdout.reconfigure(encoding='utf-8')
BASE = "http://localhost:8000/api"

endpoints = [
    ("Model info",    "GET",  "/dashboard/model-info",       None),
    ("ROC curve",     "GET",  "/dashboard/roc-curve",        None),
    ("Calibration",   "GET",  "/dashboard/calibration-curve",None),
    ("Fairness",      "GET",  "/dashboard/fairness",         None),
    ("Batch predict", "POST", "/predictions/batch",          None),
    ("Pilot metrics", "GET",  "/dashboard/pilot-metrics",    None),
]

for name, method, path, body in endpoints:
    try:
        if method == "GET":
            r = requests.get(BASE + path, timeout=10)
        else:
            r = requests.post(BASE + path, json=body, timeout=10)
        print(f"\n[{name}] {r.status_code}")
        try:
            d = r.json()
            if isinstance(d, dict):
                print(f"  Keys: {list(d.keys())[:8]}")
            elif isinstance(d, list):
                print(f"  List of {len(d)} items, first keys: {list(d[0].keys())[:5] if d else []}")
        except:
            print(f"  Body: {r.text[:120]}")
    except Exception as e:
        print(f"\n[{name}] ERROR: {e}")
