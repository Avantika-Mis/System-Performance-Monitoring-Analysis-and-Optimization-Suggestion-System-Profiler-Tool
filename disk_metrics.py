import psutil

class DiskMetrics:
    @staticmethod
    def get_metrics():
        disk_usage = psutil.disk_usage('/')
        return {
            "total_disk_space": disk_usage.total,
            "used_disk_space": disk_usage.used,
            "free_disk_space": disk_usage.free,
            "disk_usage_percent": disk_usage.percent,
            "disk_io": psutil.disk_io_counters()._asdict()
        }
