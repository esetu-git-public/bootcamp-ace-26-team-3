import time
import urllib.request
import urllib.parse
import json

def make_request(url, method="GET", headers=None, data=None, content_type=None):
    if headers is None:
        headers = {}
    # Force connection close to prevent single-threaded server blocking
    headers["Connection"] = "close"
    
    if data is not None:
        if content_type == "application/json":
            data = json.dumps(data).encode("utf-8")
            headers["Content-Type"] = "application/json"
        else:
            data = urllib.parse.urlencode(data).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"
    
    req = urllib.request.Request(url, method=method, headers=headers, data=data)
    with urllib.request.urlopen(req) as response:
        return response.status, response.read().decode("utf-8")

# 1. Login to get token (using JSON payload)
status, response_text = make_request(
    "http://localhost:8000/api/v1/auth/login",
    method="POST",
    data={"username": "admin", "password": "admin123"},
    content_type="application/json"
)
token = json.loads(response_text)["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 2. General CSV Export
start = time.time()
status, text = make_request("http://localhost:8000/api/v1/reports/export?format=csv", headers=headers)
duration = time.time() - start
print(f"General CSV export took: {duration:.4f}s, status: {status}, rows: {len(text.splitlines())}")

# 3. High-Risk CSV Export
start = time.time()
status, text = make_request("http://localhost:8000/api/v1/reports/export?format=csv&risk_category=High", headers=headers)
duration = time.time() - start
print(f"High-Risk CSV export took: {duration:.4f}s, status: {status}, rows: {len(text.splitlines())}")
