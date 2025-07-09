import psutil
from datetime import datetime
import subprocess

class CpuDeepMetrics:
    @staticmethod
    def get_hot_process_traces(top_n=5):
        processes = sorted(
            psutil.process_iter(['pid', 'name', 'cpu_percent']),
            key=lambda p: p.info['name'],
            reverse=True
        )
        result = []

        for proc in processes[:top_n]:
            try:
                # Get stack trace using py-spy
                trace_output = subprocess.check_output(
                    ["py-spy", "dump", "--pid", str(proc.pid), "--native", "--threads"],
                    stderr=subprocess.DEVNULL
                ).decode()

                # Get handle/fd count
                if platform.system() == "Windows":
                    handle_count = proc.num_handles()
                else:
                    handle_count = proc.num_fds()

                result.append({
                    "timestamp": datetime.now().isoformat(),
                    "pid": proc.pid,
                    "name": proc.name(),
                    "cpu_percent": proc.cpu_percent(),
                    "handle_count": handle_count,
                    "stack_trace": trace_output
                })

            except Exception as e:
                result.append({
                    "timestamp": datetime.now().isoformat(),
                    "pid": proc.pid,
                    "name": proc.name(),
                    "cpu_percent": proc.cpu_percent(),
                    "handle_count": -1,
                    "stack_trace": f"Error: {str(e)}"
                })

        return result

   
    def get_metrics():
        """
        Get detailed CPU metrics including usage per core, frequency, load, 
        context switches, interrupts, and process-level CPU usage.
        
        :return: dict - A dictionary containing various CPU metrics.
        """
        try:
            # Collect CPU usage for each core
            cpu_usage_per_core = psutil.cpu_percent(percpu=True)

            # Collect CPU frequency info (in MHz)
            cpu_freq = psutil.cpu_freq()
            cpu_frequency = {
                'current': cpu_freq.current,
                'min': cpu_freq.min,
                'max': cpu_freq.max
            }

            # Collect system-wide CPU load averages over 1, 5, and 15 minutes
            cpu_load = psutil.getloadavg()

            # Collect the number of context switches (both voluntary and involuntary)
            cpu_context_switches = psutil.cpu_stats().ctx_switches

            # Collect the number of hardware interrupts
            cpu_interrupts = psutil.cpu_stats().interrupts

            # Collect process-level CPU usage (top 5 processes by CPU usage)
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
                processes.append({
                    'pid': proc.info['pid'],
                    'name': proc.info['name'],
                    'cpu_percent': proc.info['cpu_percent']
                })
            processes = sorted(processes, key=lambda x: x['cpu_percent'], reverse=True)[:5]  # Top 5 CPU-consuming processes

            # Return all collected metrics
            return {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "cpu_usage_per_core": cpu_usage_per_core,
                "cpu_frequency": cpu_frequency,
                "cpu_load": cpu_load,
                "cpu_context_switches": cpu_context_switches,
                "cpu_interrupts": cpu_interrupts,
                "top_cpu_processes": processes
            }
        except Exception as e:
            # Log the error if metrics collection fails
            print(f"Error collecting CPU deep metrics: {e}")
            return {"error": "Failed to collect deep CPU metrics."}
