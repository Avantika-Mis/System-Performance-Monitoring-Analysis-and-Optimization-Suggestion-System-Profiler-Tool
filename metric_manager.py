import json
import threading
from threading import Lock
import os
import logging
import time
from datetime import datetime

from metrics.cpu_metrics import CPUMetrics
from metrics.memory_metrics import MemoryMetrics
from metrics.disk_metrics import DiskMetrics
from metrics.garbage_collector_metrics import GarbageCollectorMetrics
from metrics.system_info import SystemInfo
from metrics.thread_metrics import ThreadMetrics
from metrics.GPU_Info import GPUMetrics
from metrics.network_metrics import NetworkMetrics
from metrics.power_metrics import PowerMetrics
from metrics.cpu_metrics_deep import CpuDeepMetrics
from metrics.memory_metrics_deep import MemoryDeepMetrics
from metrics.disk_metrics_deep import DiskDeepMetrics
from metrics.alert_manager import AlertManager

from sklearn.ensemble import IsolationForest
import numpy as np

from concurrent.futures import ThreadPoolExecutor, as_completed


class MetricManager:
    def __init__(self, memory_threshold=20.0, disk_threshold=50.0, cpu_freq_threshold=1500.0,
                 metrics_file_path="system_metrics.json", auto_save_interval=30,
                 baseline_data=None, metrics_refresh_interval=120):
        self.metrics = {}
        self.memory_threshold = memory_threshold
        self.disk_threshold = disk_threshold
        self.cpu_freq_threshold = cpu_freq_threshold
        self.metrics_file_path = metrics_file_path
        self.auto_save_interval = auto_save_interval  # in seconds
        self.lock = Lock()
        self.auto_save_thread = None
        self.auto_save_active = False
        self.alert_manager = AlertManager()
        self._setup_logger()
        # Caching related variables
        self._last_metrics = None
        self._last_metrics_time = 0  # epoch time
        self._metrics_refresh_interval = metrics_refresh_interval  # seconds

    def _setup_logger(self):
        log_dir = os.path.dirname(self.metrics_file_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        log_handler = logging.FileHandler('metric_manager.log')
        log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        log_handler.setFormatter(log_formatter)
        logging.getLogger().addHandler(log_handler)
        logging.getLogger().setLevel(logging.INFO)

    
    def collect_metrics(self):
        try:
            self.metrics = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "cpu_metrics": CPUMetrics.get_metrics(),
                "cpu_deep_metrics": CpuDeepMetrics.get_metrics(),
                "cpu_hot_processes": CpuDeepMetrics.get_hot_process_traces(),
                "memory_deep_metrics": MemoryDeepMetrics.get_metrics(),
                "disk_deep_metrics": DiskDeepMetrics.get_metrics(),
                "garbage_collector_metrics": GarbageCollectorMetrics.get_metrics(),
                "system_info": SystemInfo.get_metrics(),
                "thread_metrics": ThreadMetrics.get_metrics(),
                "GPU_Metrics": GPUMetrics.get_metrics(),
                "network_metrics": NetworkMetrics.get_metrics(),
                "power_metrics": PowerMetrics.get_metrics()
            }
            logging.info("Metrics collected successfully.")
        except Exception as e:
            logging.error(f"Error collecting metrics: {e}")


    
    def get_all_metrics(self):
       with self.lock:
        current_time = time.time()

        if (self._last_metrics is None) or (current_time - self._last_metrics_time > self._metrics_refresh_interval):
            self.collect_metrics()
            self._last_metrics = self.metrics
            self._last_metrics_time = current_time
        else:
            logging.info("Returning cached metrics (within 60 seconds window).")

       return self._last_metrics
     

    def save_metrics_to_json(self):
        # with self.lock:
            self.collect_metrics()
            try:
                with open(self.metrics_file_path, "a") as file:
                    json.dump(self.metrics, file)
                    file.write("\n")
                logging.info(f"Metrics saved to {self.metrics_file_path}")
            except Exception as e:
                logging.error(f"Error saving metrics to JSON: {e}")

    def start_auto_save(self):
        def auto_save_worker():
            while self.auto_save_active:
                self.save_metrics_to_json()
                self.analyze_system_performance()
                # self.run_ai_diagnosis()
                time.sleep(self.auto_save_interval+ 60)

        if not self.auto_save_thread:
            self.auto_save_active = True
            self.auto_save_thread = threading.Thread(target=auto_save_worker, daemon=True)
            self.auto_save_thread.start()
            logging.info("Started background auto-save thread.")

    def stop_auto_save(self):
        self.auto_save_active = False
        if self.auto_save_thread:
            self.auto_save_thread.join()
            logging.info("Stopped background auto-save thread.")

    def get_metrics_for_analysis(self):
        try:
            metrics = self.get_all_metrics()
            return metrics
        except Exception as e:
            logging.error(f"Error retrieving metrics for analysis: {e}")
            return None

    def analyze_system_performance(self):
        metrics = self.get_metrics_for_analysis()
        issues = []

        if not metrics:
            issues.append("Error: Metrics could not be retrieved.")
            return issues

        memory_usage = metrics.get("memory_deep_metrics", {}).get("memory_percent", 0)
        if memory_usage > self.memory_threshold:
            issue = f"High memory usage detected: {memory_usage}%"
            issues.append(issue)
            self.alert_manager.trigger_alert(issue)

        cpu_freq = metrics.get("cpu_deep_metrics", {}).get("cpu_freq_current_mhz", 0)
        if cpu_freq < self.cpu_freq_threshold:
            issue = f"CPU frequency below threshold: {cpu_freq} MHz"
            issues.append(issue)
            self.alert_manager.trigger_alert(issue)

        disk_usage = metrics.get("disk_deep_metrics", {}).get("disk_percent", 0)
        if disk_usage > self.disk_threshold:
            issue = f"Disk usage high: {disk_usage}%"
            issues.append(issue)
            self.alert_manager.trigger_alert(issue)

        return issues

   