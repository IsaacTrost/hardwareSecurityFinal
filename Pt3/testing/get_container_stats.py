#!/usr/bin/env python3
import time
import os
import argparse
import docker

def get_sched_latency_ns():
    """
    Try to read the CFS bandwidth slice (us) as a proxy for scheduling quantum.
    """
    path = "/proc/sys/kernel/sched_cfs_bandwidth_slice_us"
    try:
        with open(path, "r") as f:
            # Convert microseconds to nanoseconds
            return int(f.read().strip()) * 1000
    except Exception as e:
        print(f"Warning: could not read {path}: {e}")
        return None

def sample_stats(container):
    """
    Fetch a one‐off stats snapshot from Docker and compute:
      - cpu_pct: approximate CPU utilization % since last call
      - mem_usage: current memory usage bytes
      - mem_pct: memory usage % of container’s limit
    """
    stats = container.stats(stream=False)
    # CPU percentage calculation
    cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - \
                stats["precpu_stats"]["cpu_usage"]["total_usage"]
    sys_delta = stats["cpu_stats"]["system_cpu_usage"] - \
                stats["precpu_stats"]["system_cpu_usage"]
    cpu_count = len(stats["cpu_stats"]["cpu_usage"].get("percpu_usage", [])) or 1
    cpu_pct = (cpu_delta / sys_delta) * cpu_count * 100.0 if sys_delta else 0.0

    # Memory usage
    mem_usage = stats["memory_stats"]["usage"]
    mem_limit = stats["memory_stats"]["limit"]
    mem_pct = (mem_usage / mem_limit) * 100.0 if mem_limit else 0.0

    return {
        "timestamp": time.time(),
        "cpu_pct": cpu_pct,
        "mem_usage": mem_usage,
        "mem_pct": mem_pct
    }

def main():
    p = argparse.ArgumentParser(
        description="Sample Docker container CPU/memory every scheduling quantum"
    )
    p.add_argument("container", help="Container ID or name")
    p.add_argument(
        "--duration", "-d",
        type=int, default=60,
        help="Total sampling duration (sec)"
    )
    p.add_argument(
        "--output", "-o",
        default="stats.csv",
        help="Output CSV file"
    )
    args = p.parse_args()

    # Determine quantum (seconds)
    latency_ns = get_sched_latency_ns()
    if latency_ns is None:
        print("Warning: could not read sched_latency_ns; defaulting to 100 ms")
        quantum_s = 0.1
    else:
        quantum_s = latency_ns / 1e9

    # Connect to Docker
    client = docker.from_env()
    try:
        container = client.containers.get(args.container)
    except docker.errors.NotFound:
        print(f"Error: no such container '{args.container}'")
        return

    end = time.time() + args.duration
    with open(args.output, "w") as f:
        f.write("timestamp,cpu_pct,mem_usage,mem_pct\n")
        while time.time() < end:
            stats = sample_stats(container)
            f.write(
                f"{stats['timestamp']:.5f},"
                f"{stats['cpu_pct']:.5f},"
                f"{stats['mem_usage']},"
                f"{stats['mem_pct']:.5f}\n"
            )
            f.flush()
            time.sleep(quantum_s)

    print(f"Done! Stats written to {args.output}")

if __name__ == "__main__":
    main()
