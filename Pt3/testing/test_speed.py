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
parser.add_argument("--initial-load", action="store_true", help="If set, perform initial record creation (writes)")
args, _ = parser.parse_known_args()

API_BASE_URL = f"https://{args.ip}/records"
INITIAL_RECORDS_TO_LOAD = 100000
WRITE_PERCENTAGE = 0.10 # 10% writes
MAX_CONCURRENT_REQUESTS = 200 # Adjust based on your server's capacity and client machine
INITIAL_WRITE_CONCURRENCY = 200  # Lower concurrency for initial writes

# --- Data Generation ---
def generate_random_string(length=10):
    return ''.join(random.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for _ in range(length))

def generate_record_data(user_id=None):
    if user_id is None:
        user_id = uuid.uuid4().hex
    notes_length_bytes = 10
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
        # 1. Initial Data Loading (single writes)
        if args.initial_load:
            print(f"--- Starting Initial Data Load: {INITIAL_RECORDS_TO_LOAD} records (single writes, concurrency {INITIAL_WRITE_CONCURRENCY}) ---")
            initial_load_tasks = []
            initial_start = time.time()

            # Generate incrementing user IDs
            all_user_ids = [f"user_{i+1}" for i in range(INITIAL_RECORDS_TO_LOAD)]
            created_user_ids = all_user_ids.copy()  # Save for mixed workload

            async def single_write(user_id):
                async with initial_write_semaphore:
                    record = generate_record_data(user_id=user_id)
                    result = await make_request(session, "POST", API_BASE_URL, data=record, operation_type="initial_write")
                    return result

            for user_id in all_user_ids:
                task = asyncio.ensure_future(single_write(user_id))
                initial_load_tasks.append(task)
                if len(initial_load_tasks) % 1000 == 0:
                    print(f"  Scheduled {len(initial_load_tasks)}/{INITIAL_RECORDS_TO_LOAD} records")

            initial_results = await asyncio.gather(*initial_load_tasks)
            initial_end = time.time()
            initial_duration = initial_end - initial_start
            for res in initial_results:
                latencies.append(res)

            total_created = sum(1 for res in initial_results if res["status"] == 201)
            print(f"--- Initial Data Load Complete. {total_created} records successfully created. ---")
            print(f"Initial write throughput: {total_created/initial_duration:.2f} ops/sec over {initial_duration:.2f} seconds")

            if total_created == 0:
                print("No records were created in the initial load. Aborting mixed workload.")
                return latencies, total_created, initial_duration, 0, 0, total_created, initial_duration
        else:
            # If not doing initial load, try to get user_ids from somewhere else or skip creation
            print("--- Skipping Initial Data Load (no --initial-load flag) ---")
            # Optionally, you could load user_ids from a file or another source here
            created_user_ids = [f"user_{i+1}" for i in range(INITIAL_RECORDS_TO_LOAD)]

        # 2. Mixed Workload for a fixed duration (100 max in-flight requests)
        print(f"\n--- Starting Mixed Workload: running for {args.duration} seconds (90% reads, max {MAX_CONCURRENT_REQUESTS} in flight) ---")
        mixed_workload_tasks = set()
        mixed_results = []
        start_time = time.time()
        op_count = 0

        def on_done(task):
            try:
                mixed_results.append(task.result())
            except Exception:
                pass
            mixed_workload_tasks.discard(task)

        async def schedule_next():
            nonlocal op_count
            if time.time() - start_time >= args.duration:
                return
            if random.random() < 0.9:  # 90% reads
                random_user_id = random.choice(created_user_ids)
                coro = make_request(session, "GET", f"{API_BASE_URL}/{random_user_id}", operation_type="mixed_read")
            else:  # 10% writes
                random_user_id = random.choice(created_user_ids)
                record = generate_record_data(user_id=random_user_id)
                coro = make_request(session, "POST", API_BASE_URL, data=record, operation_type="mixed_write")
            task = asyncio.create_task(coro)
            mixed_workload_tasks.add(task)
            op_count += 1
            task.add_done_callback(on_done)

        # Prime the pool
        for _ in range(MAX_CONCURRENT_REQUESTS):
            await schedule_next()

        # Continue scheduling as tasks finish, until time is up
        while time.time() - start_time < args.duration:
            if len(mixed_workload_tasks) < MAX_CONCURRENT_REQUESTS:
                await schedule_next()
            else:
                # Wait for any task to finish before scheduling more
                done, _ = await asyncio.wait(mixed_workload_tasks, return_when=asyncio.FIRST_COMPLETED)
                # Results are handled by add_done_callback

        # Wait for all in-flight tasks to finish
        if mixed_workload_tasks:
            await asyncio.gather(*mixed_workload_tasks)

        mixed_end = time.time()
        mixed_duration = mixed_end - start_time
        print(f"--- Mixed Workload Complete ({op_count} operations in {mixed_duration:.2f} seconds) ---")
        print(f"Mixed workload throughput: {op_count/mixed_duration:.2f} ops/sec over {mixed_duration:.2f} seconds")

        # Collect results
        latencies.extend(mixed_results)

    total_ops = (total_created if args.initial_load else 0) + op_count
    total_duration = (initial_duration if args.initial_load else 0) + mixed_duration
    return latencies, (total_created if args.initial_load else 0), (initial_duration if args.initial_load else 0), op_count, mixed_duration, total_ops, total_duration

# --- Statistics Calculation ---
def calculate_statistics(latencies_data, mixed_ops=0, mixed_duration=0):
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

    # Print summary for reads and writes
    for label, op_types in [
        ("READS", ["mixed_read"]),
        ("WRITES", ["mixed_write", "initial_write"])
    ]:
        latencies = []
        for op in op_types:
            latencies.extend(stats[op]["latencies"])
        if latencies:
            avg = sum(latencies) / len(latencies)
            print(f"\n{label} - Avg Latency: {avg:.2f} ms, Min: {min(latencies):.2f} ms, Max: {max(latencies):.2f} ms")
        else:
            print(f"\n{label} - No latency data.")

    # Print mixed workload throughput if available
    if mixed_ops and mixed_duration:
        print(f"\nMixed workload throughput: {mixed_ops/mixed_duration:.2f} ops/sec over {mixed_duration:.2f} seconds")

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
    calculate_statistics(latencies, mixed_ops, mixed_duration)
    print(f"\nInitial write throughput: {initial_ops/initial_duration:.2f} ops/sec over {initial_duration:.2f} seconds")
    print(f"Mixed workload throughput: {mixed_ops/mixed_duration:.2f} ops/sec over {mixed_duration:.2f} seconds")
    print(f"Overall throughput: {total_ops/total_duration:.2f} ops/sec over {total_duration:.2f} seconds")
    print("\nSampled container stats (timestamp, CPU%, Mem):")
    for ts, stat in stats_list[:5]:
        print(f"{ts}: {stat}")
    print("...")

if __name__ == "__main__":
    main()