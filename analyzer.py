import json
import psutil
import time
from datetime import datetime
import logging
import os

class Analyzer:
       


    def __init__(self, metrics_file="system_metrics.json", cpu_threshold=1, memory_threshold=5,
                 disk_threshold=5, gc_threshold=1, include_stack_lines=10):
        self.metrics_file = metrics_file
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.disk_threshold = disk_threshold
        self.gc_threshold = gc_threshold
        self.include_stack_lines = include_stack_lines

    def load_metrics_stream(self):
        """Yield each line of the metrics file as a parsed JSON object (for large files)."""
        try:
            with open(self.metrics_file, "r") as file:
                for line in file:
                    try:
                        yield json.loads(line.strip())
                    except json.JSONDecodeError as e:
                        print(f"JSON parse error: {e}")
                        continue
        except Exception as e:
            print(f"Error opening metrics file: {e}")
            return
    
    def get_blocking_threads_info(self):
        """Detect high CPU threads across all processes."""
        thread_info_list = []

        for proc in psutil.process_iter(['pid', 'name']):
            try:
                with proc.oneshot():
                    threads = proc.threads()
                    for thread in threads:
                        total_cpu = thread.user_time + thread.system_time
                        if total_cpu > self.cpu_threshold:
                            thread_info_list.append({
                                "thread_name": f"Thread-{thread.id}",
                                "process_name": proc.name(),
                                "pid": proc.pid,
                                "message": f"Thread {thread.id} in process {proc.name()} (PID: {proc.pid}) exceeded CPU threshold.",
                                "cpu_time": total_cpu,
                                "stack_trace": ["Stack unavailable across processes"],
                                "timestamp": datetime.utcnow().isoformat() + "Z",
                                "type": "HighCPUThread"  # match this with JS issueType
                            })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        return thread_info_list


    def get_memory_leak_suspects(memory_threshold_mb=500):    
        memory_leak_info = []

        for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
            try:
                with proc.oneshot():
                    mem_info = proc.memory_info()
                    mem_usage_mb = mem_info.rss / (1024 * 1024)  # Convert to MB

                    # if mem_usage_mb > memory_threshold_mb:  # This line must use a number
                    memory_leak_info.append({
                        "process_name": proc.name(),
                        "pid": proc.pid,
                        "message": f"Process {proc.name()} (PID: {proc.pid}) is using {mem_usage_mb:.2f} MB, which exceeds threshold.",
                        "memory_usage_mb": round(mem_usage_mb, 2),
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "type": "HighMemoryUsage"
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        return memory_leak_info




    def get_disk_profiler_issues(
        disk_usage_threshold=85,        # %
        disk_io_threshold_mb_s=100,     # MB / second
        sample_seconds=1                # how long to sample I/O
    ):
        """
        Returns a list of dicts describing disk-related performance issues.
        Structure is identical to get_memory_leak_suspects.

        Two detectors run:
          1. HighDiskUsage – partitions whose 'usage.percent' > disk_usage_threshold
          2. HighDiskIO    – physical disks whose Δ(read+write) / seconds > disk_io_threshold_mb_s
        """

        issues = []

        # ---------- 1) Nearly-full partitions ----------------------------------
        for part in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(part.mountpoint)
              
                issues.append({
                    "device": part.device,
                    "mountpoint": part.mountpoint,
                    "total_gb": round(usage.total / (1024**3), 2),
                    "used_gb":  round(usage.used  / (1024**3), 2),
                    "free_gb":  round(usage.free  / (1024**3), 2),
                    "usage_percent": round(usage.percent, 2),
                    "message": (
                        f"Partition {part.device} ({part.mountpoint}) is "
                        f"{usage.percent:.1f}% full – exceeds {disk_usage_threshold}% threshold."
                    ),
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "type": "HighDiskUsage"
                })
            except PermissionError:
                # Ignore CD/DVD or unmounted partitions we can't query
                continue

        # ---------- 2) Heavy I/O on disks --------------------------------------
        io_start = psutil.disk_io_counters(perdisk=True)
        time.sleep(sample_seconds)
        io_end   = psutil.disk_io_counters(perdisk=True)

        for disk_name, s0 in io_start.items():
            s1 = io_end.get(disk_name)
            if not s1:
                continue  # disk disappeared

            # Bytes read+written during the sample window
            delta_bytes = (s1.read_bytes - s0.read_bytes) + (s1.write_bytes - s0.write_bytes)
            mb_per_sec  = (delta_bytes / (1024 * 1024)) / sample_seconds

            if mb_per_sec > disk_io_threshold_mb_s:
                issues.append({
                    "disk": disk_name,
                    "io_mb_per_sec": round(mb_per_sec, 2),
                    "sample_seconds": sample_seconds,
                    "message": (
                        f"Disk {disk_name} sustained {mb_per_sec:.2f} MB/s "
                        f"I/O for {sample_seconds}s – exceeds {disk_io_threshold_mb_s} MB/s threshold."
                    ),
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "type": "HighDiskIO"
                })

        return issues


        



    def analyze_metrics(self):
        """Analyze the metrics stream to detect threshold breaches and extract critical info."""
        performance_issues = []

        for idx, metric in enumerate(self.load_metrics_stream()):
            # Extract timestamp, prefer top-level "timestamp"
            timestamp = metric.get("timestamp") or metric.get("system_info", {}).get("current_time", "Unknown Time")

            # CPU
            cpu_usage = metric.get("cpu_metrics", {}).get("cpu_usage_percent", 0)
            if cpu_usage > self.cpu_threshold:
                performance_issues.append({
                    "type": "CPU",
                    "timestamp": timestamp,
                    "message": f"High CPU usage: {cpu_usage:.2f}%"
                })

            # Memory
            memory_usage = metric.get("memory_metrics", {}).get("memory_usage_percent", 0)
            if memory_usage == 0:
                # fallback to deep memory metrics percent
                memory_usage = metric.get("memory_deep_metrics", {}).get("memory_usage", {}).get("percent", 0)
            if memory_usage > self.memory_threshold:
                performance_issues.append({
                    "type": "Memory",
                    "timestamp": timestamp,
                    "message": f"High memory usage: {memory_usage:.2f}%"
                })

            # Disk
            # disk_usage = metric.get("disk_metrics", {}).get("disk_usage_percent", 0)
            # if disk_usage == 0:
            #     # fallback to deep disk metrics percent
            #     disk_usage = metric.get("disk_deep_metrics", {}).get("disk_usage", {}).get("percent", 0)
            # if disk_usage > self.disk_threshold:
            #     performance_issues.append({
            #         "type": "Disk",
            #         "timestamp": timestamp,
            #         "message": f"High disk usage: {disk_usage:.2f}%"
            #     })

            # Garbage Collection
            # gc_collected = metric.get("garbage_collector_metrics", {}).get("collected_objects", 0)
            # if gc_collected > self.gc_threshold:
            #     performance_issues.append({
            #         "type": "GC",
            #         "timestamp": timestamp,
            #         "message": f"High GC activity: {gc_collected} collected objects"
            #     })

            # Thread contention
            thread_metrics = metric.get("thread_metrics", {})
            for thread in thread_metrics.get("thread_details", []):
                is_blocking = thread.get("is_blocking")
                # Accept True boolean or string "True" (case-insensitive), ignore "Unknown"
                if isinstance(is_blocking, bool) and is_blocking:
                    blocking = True
                elif isinstance(is_blocking, str) and is_blocking.lower() == "true":
                    blocking = True
                else:
                    blocking = False

                if blocking:
                    process_name = thread.get("process_name", "UnknownProcess")
                    thread_name = thread.get("thread_name", "UnknownThread")
                    stack_summary = thread.get("stack_summary", [])
                    # Limit stack trace lines if configured
                    summary = stack_summary[-self.include_stack_lines:] if self.include_stack_lines else stack_summary
                    performance_issues.append({
                        "type": "ThreadContention",
                        "timestamp": timestamp,
                        "process_name": process_name,
                        "thread_name": thread_name,
                        "message": "Blocking thread detected",
                        "stack_summary": summary
                    })

            # Extract top CPU processes if any usage > threshold
            top_cpu_processes = metric.get("cpu_deep_metrics", {}).get("top_cpu_processes", [])
            logging.info(f"Count of the top CPU processes: {len(top_cpu_processes)}")

            for proc in top_cpu_processes:
                logging.info(f"Process Name: {proc.get('name')} with Id {proc.get('pid')}")
                cpu_percent = proc.get("cpu_percent", 0)
                # if cpu_percent > self.cpu_threshold:
                performance_issues.append({
                    "type": "CPUProcess",
                    "timestamp": timestamp,
                    "process_name": proc.get("name", "UnknownProcess"),
                    "pid": proc.get("pid"),
                    "message": f"High CPU process: {proc.get('name')} using {cpu_percent:.2f}% CPU"
                })
           
            

            # Extract top memory processes
            top_memory_processes = metric.get("memory_deep_metrics", {}).get("top_memory_processes", [])
            for proc in top_memory_processes:
                mem_percent = proc.get("memory_percent", 0)
                if mem_percent > self.memory_threshold:
                    performance_issues.append({
                        "type": "MemoryProcess",
                        "timestamp": timestamp,
                        "process_name": proc.get("name", "UnknownProcess"),
                        "pid": proc.get("pid"),
                        "message": f"High Memory process: {proc.get('name')} using {mem_percent:.2f}% Memory"
                    })

            # Disk partitions usage info (warn if any partition exceeds threshold)
            # disk_partitions = metric.get("disk_deep_metrics", {}).get("disk_partitions", [])
            # for partition in disk_partitions:
            #     percent = partition.get("percent", 0)
            #     if percent > self.disk_threshold:
            #         performance_issues.append({
            #             "type": "DiskPartition",
            #             "timestamp": timestamp,
            #             "partition": partition.get("device", "UnknownPartition"),
            #             "message": f"High disk partition usage: {percent:.2f}% on {partition.get('device')}"
            #         })

            # GPU metrics (optional thresholds if needed, here just include info)
            # gpu_metrics = metric.get("GPU_Metrics", [])
            # for gpu in gpu_metrics:
            #     load = gpu.get("load", 0)
            #     if load > 0.9:  # example threshold for GPU load
            #         performance_issues.append({
            #             "type": "GPU",
            #             "timestamp": timestamp,
            #             "gpu_name": gpu.get("name", "UnknownGPU"),
            #             "message": f"High GPU load: {load:.2f}"
            #         })

            # Network metrics (if you want to detect e.g. zero or very high network traffic)
            network_metrics = metric.get("network_metrics", {})
            bytes_sent = network_metrics.get("bytes_sent", 0)
            bytes_received = network_metrics.get("bytes_received", 0)
            if bytes_sent == 0 and bytes_received == 0:
                performance_issues.append({
                    "type": "Network",
                    "timestamp": timestamp,
                    "message": "No network traffic detected"
                })

            # Power metrics info (battery low warning)
            power_metrics = metric.get("power_metrics", {})
            battery_percent = power_metrics.get("battery_percent", 100)
            power_plugged = power_metrics.get("power_plugged", True)
            if battery_percent < 20 and not power_plugged:
                performance_issues.append({
                    "type": "Power",
                    "timestamp": timestamp,
                    "message": f"Low battery: {battery_percent}% and not plugged in"
                })

        return performance_issues
    

    def performanceOverview(file_path="Suggestions/PerformanceOverview.json"):
        file_path = os.path.join("Suggestions", "PerformanceOverview.json")
        print(f"📄 File path for overview: {file_path}")
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
        except FileNotFoundError:
            print(f"❌ File not found: {file_path}")
            return []
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing error: {e}")
            return []

        if not data:
            print("✅ No performance issues detected.")
            return []

        print("🚨 Performance Issues Detected:\n")
        issues = []

        for entry in data:
            pid = entry.get("PID")
            cluster = entry.get("Cluster", "Unknown")
            pattern = entry.get("Pattern", "Unknown")
            summary = entry.get("Summary", "No summary provided.")
            recommendation = entry.get("Recommendation", "No recommendation.")

            print(f"[PID {pid}] - [{cluster}] {pattern}")
            print(f"  ↪ {summary}\n")

            if recommendation != "No action required":
                issues.append({
                    "pid": pid,
                    "cluster": cluster,
                    "pattern": pattern,
                    "summary": summary,
                    "recommendation": recommendation
                })

        return issues



    def load_thread_summaries(self, pid: int = None, directory="Suggestions"):
        summaries = []

        logging.info("load_thread_summaries called...")
        if not os.path.isdir(directory):
            logging.warning(f"❌ Directory not found: {directory}")
            return []

        for filename in os.listdir(directory):
            logging.info(f"Filename for process listing: {filename}")
            if filename.lower().startswith("summary_") and filename.endswith(".json"):
                if pid:
                    if not filename.endswith(f"{pid}.json"):
                        continue

                file_path = os.path.join(directory, filename)
                try:
                    with open(file_path, "r") as f:
                        data = json.load(f)
                        summaries.append(data)
                except Exception as e:
                    logging.error(f"⚠️ Failed to read {filename}: {e}")

        logging.info(f"📦 Loaded {len(summaries)} summary file(s).")
        return summaries



    def generate_report(self):
        """Print or return a detailed report based on detected issues."""
        issues = self.analyze_metrics()

        if not issues:
            print("✅ No performance issues detected.")
            return []

        print("🚨 Performance Issues Detected:\n")
        for issue in issues:
            print(f"[{issue['timestamp']}] - [{issue['type']}] {issue['message']}")
            if issue["type"] == "ThreadContention":
                print(f"    Process: {issue['process_name']}")
                print(f"    Thread : {issue['thread_name']}")
                print(f"    Stack  :")
                for frame in issue["stack_summary"]:
                    print(f"        {frame}")
                print()

        return issues
