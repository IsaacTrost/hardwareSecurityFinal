import asyncio
import aiohttp
import random
import time
import uuid
import os
import json
from collections import defaultdict

# --- Configuration ---
API_BASE_URL = "http://localhost:3000/records" # Change if your service runs elsewhere
INITIAL_RECORDS_TO_LOAD = 1000
MIXED_OPERATIONS_COUNT = 10000
WRITE_PERCENTAGE = 0.10 # 10% writes
MAX_CONCURRENT_REQUESTS = 50 # Adjust based on your server's capacity and client machine

# --- Data Generation ---
def generate_random_string(length=10):
    return ''.join(random.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for _ in range(length))

def generate_record_data(user_id=None):
    """Generates random data for a record based on the RecordEntry schema."""
    if user_id is None:
        user_id = uuid.uuid4().hex  # Corresponds to user_id: string
    
    # Generate a random length for notes, hex encode to make it a string
    # This simulates some variability in BLOB size and sends a string,
    # which is compatible with the 'notes?: Buffer | string' schema field.
    notes_length_bytes = random.randint(25, 128) 
    notes_content = os.urandom(notes_length_bytes).hex() # Corresponds to notes: string

    return {
        "user_id": user_id,
        "timestamp": int(time.time()) - random.randint(0, 86400 * 30), # Corresponds to timestamp: number
        "heart_rate": random.randint(50, 120), # Corresponds to heart_rate: number
        "blood_pressure": f"{random.randint(90, 140)}/{random.randint(60, 90)}", # Corresponds to blood_pressure: string
        "notes": notes_content 
    }

# --- HTTP Request Functions ---
async def make_request(session, method, url, data=None, operation_type="unknown"):
    """Makes an HTTP request and measures latency."""
    start_time = time.perf_counter()
    try:
        async with session.request(method, url, json=data) as response:
            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000
            response_body = {}
            try:
                if response.content_type == 'application/json':
                    response_body = await response.json()
            except json.JSONDecodeError:
                pass # Ignore if not JSON or empty
            except Exception: # Catch any other parsing errors
                pass

            return {
                "type": operation_type,
                "status": response.status,
                "latency_ms": latency_ms,
                "url": str(response.url),
                "user_id": data.get("user_id") if data else url.split("/")[-1] if method == "GET" else None,
                "response_body": response_body
            }
    except aiohttp.ClientError as e:
        end_time = time.perf_counter()
        latency_ms = (end_time - start_time) * 1000
        print(f"ClientError during {operation_type} to {url}: {e}")
        return {
            "type": operation_type,
            "status": "ClientError",
            "latency_ms": latency_ms,
            "url": url,
            "user_id": data.get("user_id") if data else None,
            "error": str(e)
        }
    except Exception as e: # Catch any other unexpected errors
        end_time = time.perf_counter()
        latency_ms = (end_time - start_time) * 1000
        print(f"Unexpected error during {operation_type} to {url}: {e}")
        return {
            "type": operation_type,
            "status": "Exception",
            "latency_ms": latency_ms,
            "url": url,
            "user_id": data.get("user_id") if data else None,
            "error": str(e)
        }


# --- Main Test Scenario ---
async def run_test_scenario():
    latencies = []
    created_user_ids = []
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    async with aiohttp.ClientSession() as session:
        # 1. Initial Data Loading
        print(f"--- Starting Initial Data Load: {INITIAL_RECORDS_TO_LOAD} records ---")
        initial_load_tasks = []
        for i in range(INITIAL_RECORDS_TO_LOAD):
            record_data = generate_record_data()
            # Use semaphore to limit concurrency
            await semaphore.acquire()
            task = asyncio.ensure_future(make_request(session, "POST", API_BASE_URL, record_data, "initial_write"))
            task.add_done_callback(lambda t: semaphore.release())
            initial_load_tasks.append(task)
            if (i + 1) % 100 == 0:
                print(f"  Scheduled {i+1}/{INITIAL_RECORDS_TO_LOAD} initial records...")
        
        initial_results = await asyncio.gather(*initial_load_tasks)
        for res in initial_results:
            print("res", res)
            latencies.append(res)
            if res["status"] == 201 and res["user_id"]:
                created_user_ids.append(res["user_id"])
        
        print(f"--- Initial Data Load Complete. {len(created_user_ids)} records successfully created. ---")

        if not created_user_ids:
            print("No records were created in the initial load. Aborting mixed workload.")
            return latencies

        # 2. Mixed Workload
        print(f"\n--- Starting Mixed Workload: {MIXED_OPERATIONS_COUNT} operations ({WRITE_PERCENTAGE*100}% writes) ---")
        mixed_workload_tasks = []
        for i in range(MIXED_OPERATIONS_COUNT):
            await semaphore.acquire()
            if random.random() < WRITE_PERCENTAGE: # Write operation
                record_data = generate_record_data()
                task = asyncio.ensure_future(make_request(session, "POST", API_BASE_URL, record_data, "mixed_write"))
            else: # Read operation
                random_user_id = random.choice(created_user_ids)
                task = asyncio.ensure_future(make_request(session, "GET", f"{API_BASE_URL}/{random_user_id}", operation_type="mixed_read"))
            
            task.add_done_callback(lambda t: semaphore.release())
            mixed_workload_tasks.append(task)
            if (i + 1) % (MIXED_OPERATIONS_COUNT // 10 if MIXED_OPERATIONS_COUNT >=10 else 1) == 0:
                 print(f"  Scheduled {i+1}/{MIXED_OPERATIONS_COUNT} mixed operations...")


        mixed_results = await asyncio.gather(*mixed_workload_tasks)
        latencies.extend(mixed_results)
        print("--- Mixed Workload Complete ---")

    return latencies

# --- Statistics Calculation ---
def calculate_statistics(latencies_data):
    stats = defaultdict(lambda: {"count": 0, "total_latency": 0, "latencies": [], "errors": 0, "success": 0})
    
    for record in latencies_data:
        op_type = record["type"]
        stats[op_type]["count"] += 1
        stats[op_type]["total_latency"] += record["latency_ms"]
        stats[op_type]["latencies"].append(record["latency_ms"])
        if isinstance(record["status"], int) and 200 <= record["status"] < 300:
            stats[op_type]["success"] += 1
        else:
            stats[op_type]["errors"] += 1
            if record["status"] == 409: # Specific check for conflicts (e.g. duplicate user_id on POST)
                 if "conflicts" not in stats[op_type]:
                    stats[op_type]["conflicts"] = 0
                 stats[op_type]["conflicts"] +=1


    print("\n--- Test Results ---")
    for op_type, data in stats.items():
        print(f"\nOperation Type: {op_type}")
        print(f"  Total Requests: {data['count']}")
        print(f"  Successful:     {data['success']}")
        print(f"  Errors:         {data['errors']}")
        if "conflicts" in data:
            print(f"    Conflicts (409): {data['conflicts']}")

        if data["latencies"]:
            avg_latency = data["total_latency"] / data["count"]
            min_latency = min(data["latencies"])
            max_latency = max(data["latencies"])
            
            sorted_latencies = sorted(data["latencies"])
            p50_latency = sorted_latencies[int(len(sorted_latencies) * 0.5)]
            p90_latency = sorted_latencies[int(len(sorted_latencies) * 0.9)]
            p95_latency = sorted_latencies[int(len(sorted_latencies) * 0.95)]
            p99_latency = sorted_latencies[int(len(sorted_latencies) * 0.99)]

            print(f"  Avg Latency:    {avg_latency:.2f} ms")
            print(f"  Min Latency:    {min_latency:.2f} ms")
            print(f"  Max Latency:    {max_latency:.2f} ms")
            print(f"  Median (P50):   {p50_latency:.2f} ms")
            print(f"  P90 Latency:    {p90_latency:.2f} ms")
            print(f"  P95 Latency:    {p95_latency:.2f} ms")
            print(f"  P99 Latency:    {p99_latency:.2f} ms")
        else:
            print("  No latency data recorded (all requests might have failed before sending).")

if __name__ == "__main__":
    start_overall_time = time.time()
    
    loop = asyncio.get_event_loop()
    all_latencies = loop.run_until_complete(run_test_scenario())
    
    end_overall_time = time.time()
    total_duration_seconds = end_overall_time - start_overall_time
    
    calculate_statistics(all_latencies)
    
    print(f"\nTotal test duration: {total_duration_seconds:.2f} seconds")
    total_requests = len(all_latencies)
    if total_duration_seconds > 0:
        rps = total_requests / total_duration_seconds
        print(f"Overall RPS (Requests Per Second): {rps:.2f}")