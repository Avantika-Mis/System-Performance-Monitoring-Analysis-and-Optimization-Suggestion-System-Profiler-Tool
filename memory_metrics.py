# metrics/memory_metrics.py
import psutil

class MemoryMetrics:
    @staticmethod
    def get_metrics():
        memory = psutil.virtual_memory()
        top_memory_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'memory_percent']):
            try:
                process_info = {
                    "pid": proc.info['pid'],
                    "name": proc.info['name'],
                    "memory_used": proc.info['memory_info'].rss,  # Resident Set Size
                    "memory_percent": proc.info['memory_percent']
                }
                top_memory_processes.append(process_info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        top_memory_processes = sorted(top_memory_processes, key=lambda x: x['memory_used'], reverse=True)[:10]

        return {
            "total_memory": memory.total,
            "available_memory": memory.available,
            "used_memory": memory.used,
            "memory_usage_percent": memory.percent,
            "swap_memory_percent": psutil.swap_memory().percent,
            "top_memory_consuming_processes": top_memory_processes
        }
