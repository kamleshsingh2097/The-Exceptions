import requests, json, sys

try:
    r = requests.post('http://localhost:8000/stress-test', json={}, timeout=120)
    print('STATUS_CODE:', r.status_code)
    try:
        j = r.json()
        print('JSON_KEYS:', list(j.keys()))
        print('JSON_PREVIEW:')
        print(json.dumps(j, indent=2)[:10000])
    except Exception:
        print('TEXT_PREVIEW:')
        print(repr(r.text)[:10000])
except Exception as e:
    print('EXCEPTION:')
    import traceback
    traceback.print_exc()
    sys.exit(2)
