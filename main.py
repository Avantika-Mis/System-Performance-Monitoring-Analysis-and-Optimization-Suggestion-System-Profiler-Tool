import os
import logging
from flask import Flask,request, render_template, jsonify
from threading import Lock
from MLLayer.feeder import ProcessMonitor
from metrics.metric_manager import MetricManager
from analyzer import Analyzer
import atexit
import psutil
import time
import platform
import subprocess
import pandas as pd
import distro
import wmi
from datetime import datetime


w = wmi.WMI()

# Set up logging
logging.basicConfig(level=logging.INFO)

# Create Flask app
app = Flask(__name__)

# Initialize MetricManager with environment-based configuration
memory_threshold = float(os.getenv("MEMORY_THRESHOLD", "5.0"))
metrics_file_name = os.getenv("METRICS_FILE_PATH", "system_metrics.json")
auto_save_interval = int(os.getenv("AUTO_SAVE_INTERVAL", "60"))  # Default every 60s

# Ensure the log directory exists before initializing MetricManager
# Convert the file path to absolute path first, then extract the directory
log_dir = os.path.dirname(os.path.abspath(metrics_file_name))

# Check if directory exists, create if not
if not os.path.exists(log_dir):
    try:
        os.makedirs(log_dir)  # Create the necessary parent directories
        logging.info(f"Created log directory: {log_dir}")
    except Exception as e:
        logging.error(f"Error creating log directory {log_dir}: {e}")
        raise

# Combine the log directory and the file name to get the full path
metrics_file_path = os.path.join(log_dir, metrics_file_name)

metric_manager = MetricManager(
    memory_threshold=memory_threshold,
    metrics_file_path=metrics_file_path,
    auto_save_interval=auto_save_interval
)

# Start background auto-saving
metric_manager.start_auto_save()

# Initialize Analyzer
analyzer = Analyzer()

monitor = ProcessMonitor()
monitor.start_background()  # ✅ Start background feeder loop

# Lock to ensure thread-safety for metrics access
metrics_lock = Lock()

@app.route("/")
def index():
    """Render the real-time metrics dashboard."""
    return render_template("index.html")

@app.route("/metrics", methods=["GET"])
def get_metrics():
    """Return the latest system metrics to the frontend."""
    try:
        #with metrics_lock:
        metrics = metric_manager.get_all_metrics()
        return jsonify(metrics)
    except Exception as e:
        logging.error(f"Error fetching metrics: {e}")
        return jsonify({"error": f"Failed to fetch metrics: {str(e)}"}), 500


@app.route("/overview", methods=["GET"])
def get_overView():
    """Analyze the stored metrics and return detected performance issues."""
    try:
        issues = analyzer.performanceOverview()
        return jsonify({"performance_issues": issues or []})
    except Exception as e:
        logging.error(f"Error analyzing metrics: {e}")
        return jsonify({"error": f"Failed to analyze metrics: {str(e)}"}), 500


@app.route("/aisummary", methods=["GET"])
def get_summary():
    """Analyze the stored metrics and return thread-level summaries (optionally by PID)."""
    try:
        pid = request.args.get("pid", type=int)  # Get optional ?pid=1234
        logging.info(f"pid received for getting details: {pid}")
        issues = analyzer.load_thread_summaries(pid=pid)
        if not issues:
            return jsonify({"performance_issues": []}), 404
        return jsonify({"performance_issues": issues})
    except Exception as e:
        logging.error(f"Error analyzing summaries: {e}")
        return jsonify({"error": f"Failed to analyze summaries: {str(e)}"}), 500


@app.route("/analyze", methods=["GET"])
def analyze_metrics():
    """Analyze the stored metrics and return detected performance issues."""
    try:
        issues = analyzer.generate_report()
        return jsonify({"performance_issues": issues or []})
    except Exception as e:
        logging.error(f"Error analyzing metrics: {e}")
        return jsonify({"error": f"Failed to analyze metrics: {str(e)}"}), 500

@app.route("/ThreadInfo", methods=["GET"])
def SummaryInfo():
    """Analyze the stored metrics and return detected performance issues."""
    try:
        issues = analyzer.get_blocking_threads_info()
        return jsonify({"performance_issues": issues or []})
    except Exception as e:
        logging.error(f"Error analyzing metrics: {e}")
        return jsonify({"error": f"Failed to analyze metrics: {str(e)}"}), 500


@app.route("/memoryInfo", methods=["GET"])
def MemoryProfileInfo():
    """Analyze the stored metrics and return detected performance issues."""
    try:
        issues = analyzer.get_memory_leak_suspects()
        return jsonify({"performance_issues": issues or []})
    except Exception as e:
        logging.error(f"Error analyzing metrics: {e}")
        return jsonify({"error": f"Failed to analyze metrics: {str(e)}"}), 500


@app.route("/threadProfilerInfo", methods=["GET"])
def thread_profiler_info():
    """Analyze the stored metrics and return per-thread CPU trend per PID."""
    try:        
        file_path = os.path.join("Suggestions", "process_thread_metrics.csv")
        if not os.path.exists(file_path):
            return jsonify({"error": "Metrics file not found."}), 404

        # Define columns
        columns = [
            "Timestamp", "ProcessName", "PID", "HandleCount", "ThreadCount", "ThreadID",
            "CpuTimeMs", "MemoryMB", "ReadBytes", "WriteBytes", "InLockContention",
            "PossibleRaceProne", "ThreadStartTime", "ThreadState", "WaitReason",
            "UserTimeMs", "KernelTimeMs", "Priority", "ContextSwitches"
        ]

        # Read & clean data
        df = pd.read_csv(file_path, names=columns, header=0, parse_dates=["Timestamp"], low_memory=False)
        df["CpuTimeMs"] = pd.to_numeric(df["CpuTimeMs"], errors='coerce')
        df["PID"] = pd.to_numeric(df["PID"], errors='coerce')
        df["ThreadID"] = pd.to_numeric(df["ThreadID"], errors='coerce')

        # Build trend series
        thread_trend = (
            df.groupby(["PID", "ThreadID", "Timestamp"])["CpuTimeMs"]
            .sum()
            .reset_index()
            .sort_values(["PID", "ThreadID", "Timestamp"])
        )

        result = []

        for pid, group in thread_trend.groupby("PID"):
            process_entry = {
                "pid": int(pid),
                "threads": []
            }

            for tid, tgroup in group.groupby("ThreadID"):
                process_entry["threads"].append({
                    "thread_id": int(tid),
                    "timestamps": tgroup["Timestamp"].dt.strftime('%Y-%m-%d %H:%M:%S').tolist(),
                    "cpu_time": tgroup["CpuTimeMs"].tolist()
                })

            result.append(process_entry)

        return jsonify({"performance_issues": result})

    except Exception as e:
        logging.error(f"Error analyzing metrics: {e}")
        return jsonify({"error": f"Failed to analyze metrics: {str(e)}"}), 500


@app.route("/diskInfo", methods=["GET"])
def disk_profile_info():
    try:
        issues = analyzer.get_disk_profiler_issues()          # default thresholds
        # Or customise: get_disk_profiler_issues(disk_usage_threshold=90, disk_io_threshold_mb_s=150)
        return jsonify({"performance_issues": issues or []})
    except Exception as e:
        logging.error(f"Error analyzing disk metrics: {e}")
        return jsonify({"error": f"Failed to analyze disk metrics: {str(e)}"}), 500


@app.route("/api/run-diagnosis", methods=["GET"])
def run_diagnosis():
    result = metric_manager.run_ai_diagnosis()
    if result is None:
        return jsonify({"error": "Diagnosis failed"}), 500
    return jsonify(result)

# Gracefully stop auto-save when Flask is stopped
def shutdown():
    logging.info("Shutting down Flask app...")
    metric_manager.stop_auto_save()
    logging.info("Auto-save stopped gracefully.")

# Register the shutdown function to be called on app termination
atexit.register(shutdown)


@app.route('/optimize-locks', methods=['POST'])
def optimize_locks():
    try:
        issues = request.get_json()
        if not issues:
            return jsonify(status="error", message="No data received"), 400

        if not isinstance(issues, list):
            issues = [issues]

        all_suggestions = []

        for issue in issues:
            issue_type = issue.get("type", "Unknown")
            timestamp = issue.get("timestamp", "Unknown")
            process_name = issue.get("process_name", "Unknown")
            pid = issue.get("pid", "Unknown")
            cpu_message = issue.get("message", "No message provided.")

            if issue_type == "CPUProcess":
                optimization_message = (
                    f"Optimization suggestion: Investigate high CPU usage by process '{process_name}' "
                    f"(PID: {pid}). Consider checking for inefficient loops, stuck threads, or runaway processes."
                )
                all_suggestions.append({
                    "status": "success",
                    "message": optimization_message,
                    "details": {
                        "process_name": process_name,
                        "pid": pid,
                        "timestamp": timestamp,
                        "original_message": cpu_message
                    }
                })

            elif issue_type == "HighCPUThread":
                thread_name = issue.get("thread_name", "Unknown")
                optimization_message = (
                    f"Optimization suggestion: Detected locked thread '{thread_name}'. "
                    f"Safely abort or debug the issue causing thread in process '{process_name}'."
                )
                all_suggestions.append({
                    "status": "success",
                    "message": optimization_message,
                    "details": {
                        "thread_name": thread_name,
                        "process_name": process_name,
                        "timestamp": timestamp,
                        "original_message": cpu_message
                    }
                })

            else:
                all_suggestions.append({
                    "status": "error",
                    "message": f"Unhandled issue type: {issue_type}",
                    "details": {
                        "issue_type": issue_type,
                        "timestamp": timestamp
                    }
                })

        return jsonify(all_suggestions), 200

    except Exception as e:
        return jsonify(status="error", message=str(e)), 500


@app.route("/terminate-process", methods=["POST"])
def terminate_process():
    data = request.get_json()
    pid = data.get("pid")
    if not pid:
        return jsonify({"status": "error", "message": "pid is required"}), 400

    try:
        proc = psutil.Process(int(pid))
        proc.terminate()
        try:
            proc.wait(timeout=5)
            if proc.is_running():
                return jsonify({"status": "error", "message": f"Process PID {pid} did not terminate."}), 500
        except psutil.TimeoutExpired:
            proc.kill()
            if proc.is_running():
                return jsonify({"status": "error", "message": f"Process PID {pid} could not be killed."}), 500

        return jsonify({"status": "success", "message": f"Process PID {pid} terminated."})

    except psutil.NoSuchProcess:
        return jsonify({"status": "error", "message": f"No process with PID {pid} found."}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500



@app.route("/shutdown-system", methods=["POST"])
def shutdown_system():
    data = request.get_json()
    reason = data.get("reason", "Shutdown requested by user")

    try:
        system = platform.system()

        if system == "Windows":
            # Force shutdown with message
            subprocess.run(["shutdown", "/s", "/t", "0"], check=True)
        elif system == "Linux" or system == "Darwin":  # macOS is Darwin
            # Use shutdown command (requires sudo)
            subprocess.run(["shutdown", "-h", "now"], check=True)
        else:
            return jsonify({"status": "error", "message": f"Unsupported platform: {system}"}), 400

        return jsonify({"status": "success", "message": f"System shutdown initiated. Reason: {reason}"})
    except subprocess.CalledProcessError as e:
        return jsonify({"status": "error", "message": f"Failed to shutdown system: {e}"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/get-osInfo', methods=['GET'])
def get_os_info():
    os_info = {
        "OS": platform.system(),
        "Release": platform.release(),
        "Version": platform.version(),
        "Machine": platform.machine(),
        "Processor": platform.processor(),
        "Architecture": platform.architecture()[0]
    }

    # Add Linux-specific distro info if available
    if os_info["OS"] == "Linux":
        os_info.update({
            "DistroName": distro.name(),
            "DistroVersion": distro.version(),
            "DistroID": distro.id()
        })

    return jsonify(os_info)



# Get Thread details for the faulty process detected


# @app.route("/threadtimeline")
# def thread_timeline():
#     tid = request.args.get("tid", type=int)
#     print(f"[INFO] Thread timeline request received for TID: {tid}")

#     if not tid:
#         print("[ERROR] Missing thread ID in request")
#         return jsonify({"error": "Missing thread ID (tid)"}), 400

#     try:
#         found_thread = None
#         proc_name = None

#         print("[INFO] Enumerating all processes and threads...")
#         for proc in w.Win32_Process():
#             pid = proc.ProcessId
#             try:
#                 for thread in w.Win32_Thread(ProcessHandle=str(pid)):
#                     if int(thread.Handle) == tid:
#                         found_thread = thread
#                         proc_name = proc.Name
#                         print(f"[SUCCESS] Found thread {tid} in process {proc_name} (PID: {pid})")
#                         break
#             except Exception as thread_err:
#                 print(f"[WARN] Could not read threads of PID {pid}: {thread_err}")
#             if found_thread:
#                 break

#         if not found_thread:
#             print(f"[ERROR] Thread ID {tid} not found in any running process")
#             return jsonify({"error": f"Thread ID {tid} not found"}), 404

#         snapshot = {
#             "timestamp": datetime.now().isoformat(),
#             "ThreadId": tid,
#             "ProcessId": found_thread.ProcessHandle,
#             "ProcessName": proc_name,
#             "ThreadState": found_thread.ThreadState,
#             "WaitReason": found_thread.ThreadWaitReason,
#             "Priority": found_thread.Priority,
#             "UserModeTimeMs": int(found_thread.UserModeTime) // 10_000,
#             "KernelModeTimeMs": int(found_thread.KernelModeTime) // 10_000,
#             "StartAddress": found_thread.StartAddress,
#         }

#         print(f"[INFO] Thread snapshot generated:\n{json.dumps(snapshot, indent=2)}")
#         return jsonify(snapshot)

    # except Exception as ex:
    #     print(f"[EXCEPTION] An error occurred while fetching thread timeline: {ex}")
    #     return jsonify({"error": str(ex)}), 500




@app.route("/cpu-profiler", methods=["GET"])
def cpu_profiler():
    # Initialize CPU usage for all processes
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            proc.cpu_percent(interval=None)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    time.sleep(1.0)  # Wait so we get real values

    return jsonify(get_cpu_data())


def run_monitor():
    monitor = ProcessMonitor()
    monitor.start_background();
    while True:
        monitor.collect_metrics()
        monitor.suggest_patterns()
        monitor.analyze_json_and_generate_summary()
        time.sleep(30)

if __name__ == "__main__":
    try:
        # Start the Flask app
        app.run(debug=True, host="0.0.0.0", port=8000)
        run_monitor()
    except KeyboardInterrupt:
        # On graceful shutdown (Ctrl+C)
        shutdown()
        logging.info("Flask app stopped. Auto-save stopped gracefully.")
