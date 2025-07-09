import psutil

class CPUMetrics:
    @staticmethod
    def get_metrics(memory_threshold=1.0):
        """
        Get system CPU metrics and filter critical processes based on high memory consumption.
        
        :param memory_threshold: float - The minimum memory percentage to qualify as 'high' (default is 5%).
        :return: dict - Metrics including filtered critical processes and the CPU percentage of the top process.
        """
        critical_processes = []
        top_process_cpu_percent = 0.0  # Variable to store the top process CPU percentage
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                if proc.info['memory_percent'] > memory_threshold:
                    critical_processes.append(proc.info)
                    
                    # Track the process with the highest CPU usage
                    if proc.info['cpu_percent'] > top_process_cpu_percent:
                        top_process_cpu_percent = proc.info['cpu_percent']
            except psutil.NoSuchProcess:
                pass

        return {
            "cpu_usage_percent": psutil.cpu_percent(interval=0.5),
            "cpu_count": psutil.cpu_count(logical=True),
            "cpu_frequency": psutil.cpu_freq().current if psutil.cpu_freq() else None,
            "critical_processes": critical_processes,
            "top_process_cpu_percent": top_process_cpu_percent  # Add top process CPU percentage
        }
