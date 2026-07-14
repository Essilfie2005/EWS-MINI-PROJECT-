import requests, sys
sys.stdout.reconfigure(encoding='utf-8')

base = 'http://localhost:8000/api'
tests = [
    ('GET', '/dashboard/confusion-matrix',   'Confusion Matrix'),
    ('GET', '/dashboard/calibration-curve',  'Calibration Curve'),
    ('GET', '/dashboard/fairness',           'Fairness Analysis'),
    ('GET', '/dashboard/ctgan-quality',      'CTGAN Quality'),
    ('GET', '/dashboard/delong-test',        'DeLong Test'),
    ('GET', '/predictions/trajectory/1',     'Risk Trajectory'),
    ('GET', '/predictions/count-at-threshold?tau=0.4432', 'Count At Threshold'),
    ('GET', '/predictions/pdf/1',            'PDF Brief'),
]
print('=== V2 Endpoint Smoke Test ===')
all_pass = True
for method, path, name in tests:
    try:
        r = requests.request(method, base + path, timeout=15)
        ok = r.status_code == 200
        if not ok:
            all_pass = False
        if ok:
            ct = r.headers.get('content-type','')
            if 'json' in ct:
                d = r.json()
                fk = list(d.keys())[0] if isinstance(d, dict) and d else str(d)[:40]
            else:
                fk = f'binary ({len(r.content)} bytes)'
        else:
            fk = r.text[:60]
        label = 'OK  ' if ok else 'FAIL'
        print(f'[{label}] {name}: HTTP {r.status_code}  => {fk}')
    except Exception as e:
        all_pass = False
        print(f'[ERR ] {name}: {e}')

print()
print('ALL PASSED' if all_pass else 'SOME FAILED - check above')
