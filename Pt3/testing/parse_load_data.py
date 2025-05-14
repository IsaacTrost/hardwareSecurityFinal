import csv
import re
import matplotlib.pyplot as plt

def parse_mem(mem_str):
    """Parse memory string like '186.5MiB / 14.67GiB' and return used, total in MiB."""
    used, total = mem_str.split('/')
    used = used.strip()
    total = total.strip()
    def to_mib(val):
        if val.endswith('GiB'):
            return float(val[:-3]) * 1024
        elif val.endswith('MiB'):
            return float(val[:-3])
        elif val.endswith('KiB'):
            return float(val[:-3]) / 1024
        else:
            return float(val)
    return to_mib(used), to_mib(total)

def parse_cpu(cpu_str):
    """Parse CPU percent string like '82.21%'."""
    return float(cpu_str.strip().replace('%', ''))

def parse_file(filename):
    rows = []
    with open(filename, 'r') as f:
        lines = f.readlines()
    i = 0
    while i < len(lines) - 1:
        ts_line = lines[i].strip()
        stat_line = lines[i+1].strip()
        # Skip empty lines
        if not ts_line or not stat_line:
            i += 1
            continue
        # Parse timestamp
        try:
            timestamp = int(ts_line)
        except ValueError:
            i += 1
            continue
        # Parse stat line
        parts = stat_line.split(',')
        if len(parts) != 3:
            i += 2
            continue
        container, cpu_str, mem_str = parts
        cpu = parse_cpu(cpu_str)
        mem_used, mem_total = parse_mem(mem_str)
        rows.append({
            "timestamp": timestamp,
            "container": container,
            "cpu_percent": cpu,
            "mem_used_mib": mem_used,
            "mem_total_mib": mem_total
        })
        i += 2
    return rows

def write_csv(rows, out_csv):
    with open(out_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "container", "cpu_percent", "mem_used_mib", "mem_total_mib"])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

def plot_stats(rows):
    import matplotlib.dates as mdates
    import datetime
    timestamps = [row["timestamp"] for row in rows]
    # Convert ms since epoch to datetime
    times = [datetime.datetime.fromtimestamp(ts/1000) for ts in timestamps]
    cpu = [row["cpu_percent"] for row in rows]
    mem = [row["mem_used_mib"] for row in rows]
    plt.figure(figsize=(12,6))
    plt.subplot(2,1,1)
    plt.plot(times, cpu, label="CPU %")
    plt.ylabel("CPU %")
    plt.title("Container CPU and Memory Usage Over Time")
    plt.grid(True)
    plt.subplot(2,1,2)
    plt.plot(times, mem, label="Memory Used (MiB)", color='orange')
    plt.ylabel("Memory Used (MiB)")
    plt.xlabel("Time")
    plt.grid(True)
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python parse_load_data.py <input_file> [output_csv]")
        exit(1)
    infile = sys.argv[1]
    outfile = sys.argv[2] if len(sys.argv) > 2 else "parsed_stats.csv"
    rows = parse_file(infile)
    write_csv(rows, outfile)
    print(f"Wrote {len(rows)} rows to {outfile}")
    plot_stats(rows)