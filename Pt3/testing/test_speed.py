import asyncio
import aiohttp
import random
import time
import uuid
import os
import json
import subprocess
import threading
from collections import defaultdict
import argparse

# --- Configuration ---
parser = argparse.ArgumentParser(description="Test speed script")
parser.add_argument("--ip", default="localhost", help="API server IP address (default: localhost)")
parser.add_argument("--port", default="3000", help="API server port (default: 3000)")
parser.add_argument("--duration", type=int, default=120, help="Test duration in seconds (default: 120)")
args, _ = parser.parse_known_args()

API_BASE_URL = f"https://{args.ip}/records"
INITIAL_RECORDS_TO_LOAD = 50000
WRITE_PERCENTAGE = 0.10 # 10% writes
MAX_CONCURRENT_REQUESTS = 1000 # Adjust based on your server's capacity and client machine
INITIAL_WRITE_CONCURRENCY = 1000  # Lower concurrency for initial writes

# --- Data Generation ---
def generate_random_string(length=10):
    return ''.join(random.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for _ in range(length))

def generate_record_data(user_id=None):
    if user_id is None:
        user_id = uuid.uuid4().hex
    notes_length_bytes = random.randint(16, 128)
    notes_content = os.urandom(notes_length_bytes).hex()
    return {
        "user_id": user_id,
        "timestamp": int(time.time()) - random.randint(0, 86400 * 30),
        "heart_rate": random.randint(50, 120),
        "blood_pressure": f"{random.randint(90, 140)}/{random.randint(60, 90)}",
        "notes": notes_content
    }

async def make_request(session, method, url, data=None, operation_type="unknown"):
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
                pass
            except Exception:
                pass
            # Print error details if not 2xx
            if not (200 <= response.status < 300):
                print(f"Error from remote: {response.status} {response.reason} for {url}")
                print(f"Response body: {response_body}")
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
    except Exception as e:
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

async def make_request_batch(session, url, data_list, operation_type="batch_initial_write"):
    start_time = time.perf_counter()
    try:
        async with session.post(url, json=data_list) as response:
            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000
            response_body = {}
            try:
                if response.content_type == 'application/json':
                    response_body = await response.json()
            except json.JSONDecodeError:
                pass
            except Exception:
                pass
            # Print error details if not 2xx
            if not (200 <= response.status < 300):
                print(f"Error from remote (batch): {response.status} {response.reason} for {url}")
                print(f"Response body: {response_body}")
            return {
                "type": operation_type,
                "status": response.status,
                "latency_ms": latency_ms,
                "url": str(response.url),
                "batch_size": len(data_list),
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
            "batch_size": len(data_list),
            "error": str(e)
        }
    except Exception as e:
        end_time = time.perf_counter()
        latency_ms = (end_time - start_time) * 1000
        print(f"Unexpected error during {operation_type} to {url}: {e}")
        return {
            "type": operation_type,
            "status": "Exception",
            "latency_ms": latency_ms,
            "url": url,
            "batch_size": len(data_list),
            "error": str(e)
        }

# --- Main Test Scenario ---
async def run_test_scenario():
    latencies = []
    created_user_ids = []
    initial_write_semaphore = asyncio.Semaphore(INITIAL_WRITE_CONCURRENCY)
    mixed_semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        # 1. Initial Data Loading (batch 100 at a time)
        print(f"--- Starting Initial Data Load: {INITIAL_RECORDS_TO_LOAD} records (batching 100 at a time) ---")
        initial_load_tasks = []
        initial_start = time.time()
        BATCH_SIZE = 5

        # Generate incrementing user IDs
        all_user_ids = [f"user_{i+1}" for i in range(INITIAL_RECORDS_TO_LOAD)]
        created_user_ids = all_user_ids.copy()  # Save for mixed workload

        batches = [
            [generate_record_data(user_id=all_user_ids[i * BATCH_SIZE + j]) for j in range(min(BATCH_SIZE, INITIAL_RECORDS_TO_LOAD - i * BATCH_SIZE))]
            for i in range((INITIAL_RECORDS_TO_LOAD + BATCH_SIZE - 1) // BATCH_SIZE)
        ]

        for i, batch in enumerate(batches):
            task = asyncio.ensure_future(make_request_batch(session, API_BASE_URL, batch, "batch_initial_write"))
            initial_load_tasks.append(task)
            print(f"  Scheduled batch {i+1}/{len(batches)} ({len(batch)} records)")

        initial_results = await asyncio.gather(*initial_load_tasks)
        initial_end = time.time()
        initial_duration = initial_end - initial_start
        for res in initial_results:
            latencies.append(res)
            # Optionally, extract created user_ids from response_body if your API returns them

        total_created = sum(res.get("batch_size", 0) for res in initial_results if res["status"] == 201)
        print(f"--- Initial Data Load Complete. {total_created} records successfully created. ---")
        print(f"Initial write throughput: {total_created/initial_duration:.2f} ops/sec over {initial_duration:.2f} seconds")

        if total_created == 0:
            print("No records were created in the initial load. Aborting mixed workload.")
            return latencies, total_created, initial_duration, 0, 0

        # 2. Mixed Workload for a fixed duration
        print(f"\n--- Starting Mixed Workload: running for {args.duration} seconds (100% reads) ---")
        mixed_workload_tasks = []
        start_time = time.time()
        op_count = 0

        async def mixed_worker():
            nonlocal op_count
            while time.time() - start_time < args.duration:
                await mixed_semaphore.acquire()
                # Only do mixed reads
                random_user_id = random.choice(created_user_ids)
                task = asyncio.ensure_future(make_request(session, "GET", f"{API_BASE_URL}/{random_user_id}", operation_type="mixed_read"))
                task.add_done_callback(lambda t: mixed_semaphore.release())
                mixed_workload_tasks.append(task)
                op_count += 1

        # Launch workers up to MAX_CONCURRENT_REQUESTS
        workers = [asyncio.create_task(mixed_worker()) for _ in range(MAX_CONCURRENT_REQUESTS)]
        await asyncio.gather(*workers)
        await asyncio.gather(*mixed_workload_tasks)
        mixed_end = time.time()
        mixed_duration = mixed_end - start_time
        print(f"--- Mixed Workload Complete ({op_count} operations in {mixed_duration:.2f} seconds) ---")
        print(f"Mixed workload throughput: {op_count/mixed_duration:.2f} ops/sec over {mixed_duration:.2f} seconds")

        latencies.extend([t.result() for t in mixed_workload_tasks if t.done() and t.exception() is None])

    total_ops = len(initial_results) + op_count
    total_duration = initial_duration + mixed_duration
    return latencies, len(initial_results), initial_duration, op_count, mixed_duration, total_ops, total_duration

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
            if record["status"] == 409:
                if "conflicts" not in stats[op_type]:
                    stats[op_type]["conflicts"] = 0
                stats[op_type]["conflicts"] += 1

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

def main():
    print(f"\n=== Test Run ===")
    stats_list = []
    stop_event = threading.Event()
    attestation_start = time.time()
    start = time.time()
    loop = asyncio.get_event_loop()
    latencies, initial_ops, initial_duration, mixed_ops, mixed_duration, total_ops, total_duration = loop.run_until_complete(run_test_scenario())
    end = time.time()
    stop_event.set()
    print(f"Run duration: {end-start:.2f} seconds")
    calculate_statistics(latencies)
    print(f"\nInitial write throughput: {initial_ops/initial_duration:.2f} ops/sec over {initial_duration:.2f} seconds")
    print(f"Mixed workload throughput: {mixed_ops/mixed_duration:.2f} ops/sec over {mixed_duration:.2f} seconds")
    print(f"Overall throughput: {total_ops/total_duration:.2f} ops/sec over {total_duration:.2f} seconds")
    print("\nSampled container stats (timestamp, CPU%, Mem):")
    for ts, stat in stats_list[:5]:
        print(f"{ts}: {stat}")
    print("...")

if __name__ == "__main__":
    main()