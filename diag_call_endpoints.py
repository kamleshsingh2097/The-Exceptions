import requests, json, sys

endpoints = [
    ("/stress-test", 'POST'),
    ("/regime-analysis", 'POST'),
    ("/backtest", 'POST')
]
base = 'http://localhost:8000'

for path, method in endpoints:
    url = base + path
    print('\nCALLING', url)
    try:
        if method == 'POST':
            r = requests.post(url, json={}, timeout=600)
        else:
            r = requests.get(url, timeout=60)
        print('Status:', r.status_code)
        try:
            body = r.json()
            s = json.dumps(body, indent=2)
            print(s[:4000])
        except Exception:
            print('Non-JSON response (truncated):')
            print(r.text[:4000])
    except Exception as e:
        print('Request failed:', e)
        sys.exit(1)
print('\nALL DONE')
