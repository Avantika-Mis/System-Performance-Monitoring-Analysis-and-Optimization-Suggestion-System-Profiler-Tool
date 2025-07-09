import psutil
from datetime import datetime

class ThreadMetrics:
    @staticmethod
    def get_metrics(max_external_processes=10):
        thread_details = []
        seen_pids = set()
        external_process_count = 0

        current_pid = psutil.Process().pid

        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.pid == current_pid:
                    continue  # Skip current process

                if proc.pid in seen_pids:
                    continue  # Skip duplicates, if any

                if external_process_count >= max_external_processes:
                    break  # Limit reached

                seen_pids.add(proc.pid)
                external_process_count += 1

                for t in proc.threads():
                    thread_details.append({
                        "process_name": proc.info['name'],
                        "pid": proc.pid,
                        "thread_name": f"TID-{t.id}",
                        "ident": t.id,
                        "is_alive": "Unknown",
                        "daemon": "Unknown",
                        "is_blocking": "Unknown",
                        "stack_summary": ["Unavailable for external process"],
                        "user_time": round(t.user_time, 2),
                        "system_time": round(t.system_time, 2),
                        "total_cpu_time": round(t.user_time + t.system_time, 2),
                        "source": "external"
                    })

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # Skip processes we can't access
                continue

        return {
            "collected_at": datetime.now().isoformat(),
            "external_process_count": external_process_count,
            "thread_count": len(thread_details),
            "thread_details": thread_details
        }
