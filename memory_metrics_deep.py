import psutil
from datetime import datetime

class MemoryDeepMetrics:
    @staticmethod
    def get_metrics():
        """
        Get detailed memory metrics including physical memory usage, swap memory,
        memory stats, and memory usage per process.
        
        :return: dict - A dictionary containing various memory metrics.
        """
        try:
            # Collect virtual memory usage (total, available, used, etc.)
            memory = psutil.virtual_memory()
            memory_usage = {
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
                "free": memory.free,
                "percent": memory.percent,
                # Check if 'active' and 'inactive' exist in the psutil version
                "active": getattr(memory, 'active', None),  # Return None if attribute doesn't exist
                "inactive": getattr(memory, 'inactive', None),  # Return None if attribute doesn't exist                
                
            }

            # Collect swap memory usage
            swap = psutil.swap_memory()
            swap_usage = {
                "total": swap.total,
                "used": swap.used,
                "free": swap.free,
                "percent": swap.percent,
                "sin": swap.sin,  # Amount of memory swapped in from disk
                "sout": swap.sout  # Amount of memory swapped out to disk
            }

            # Collect memory stats (like page faults, number of free pages, etc.)
            memory_stats = psutil.virtual_memory()._asdict()  # Collects various OS-level memory stats
            
            # Collect memory usage by top N processes
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
                processes.append({
                    'pid': proc.info['pid'],
                    'name': proc.info['name'],
                    'memory_percent': proc.info['memory_info'].rss / psutil.virtual_memory().total * 100  # Memory in RSS
                })
            processes = sorted(processes, key=lambda x: x['memory_percent'], reverse=True)[:5]  # Top 5 memory-consuming processes

            # Return all collected memory metrics
            return {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "memory_usage": memory_usage,
                "swap_usage": swap_usage,
                "memory_stats": memory_stats,
                "top_memory_processes": processes
            }

        except Exception as e:
            # Log the error if metrics collection fails
            print(f"Error collecting memory deep metrics: {e}")
            return {"error": "Failed to collect deep memory metrics."}
