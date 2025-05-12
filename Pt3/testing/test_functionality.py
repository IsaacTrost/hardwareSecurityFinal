import requests
import uuid
import time

API_BASE_URL = "http://34.60.88.79:3000/records"

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
resp = requests.post(API_BASE_URL, json=record)
print("POST status:", resp.status_code, resp.text)

# 2. Retrieve the record
resp = requests.get(f"{API_BASE_URL}/{user_id}")
print("GET status:", resp.status_code, resp.text)