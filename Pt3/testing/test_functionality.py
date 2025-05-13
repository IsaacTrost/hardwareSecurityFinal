import requests
import uuid
import time

API_BASE_URL = "https://10.128.0.25/records"

# Allow self-signed certificates
REQUESTS_VERIFY = False

# Generate a random record
user_id = f"test_{uuid.uuid4().hex[:8]}"
record = {
    "user_id": user_id,
    "timestamp": int(time.time()),
    "heart_rate": 72,
    "blood_pressure": "120/80",
    "notes": "simple test"
}

# 1. Create a record
resp = requests.post(API_BASE_URL, json=record, verify=REQUESTS_VERIFY)
print("POST status:", resp.status_code, resp.text)

# 2. Retrieve the record
resp = requests.get(f"{API_BASE_URL}/{user_id}", verify=REQUESTS_VERIFY)
print("GET status:", resp.status_code, resp.text)