import psutil
from datetime import datetime
from typing import Dict, Any


class DiskDeepMetrics:
    @staticmethod
    def _safe_disk_usage(mountpoint: str):
        """
        Try psutil.disk_usage(mountpoint). Return None if inaccessible.
        """
        try:
            return psutil.disk_usage(mountpoint)
        except (PermissionError, FileNotFoundError, OSError):
            return None

    @staticmethod
    def get_metrics() -> Dict[str, Any]:
        """
        Collect deep disk metrics. Handles unavailable drives gracefully.

        :return: dict - Disk usage, I/O stats, per-partition info, and latency.
        """
        try:
            # Step 1: Choose a primary mountpoint
            candidates = ["/"]
            for p in psutil.disk_partitions(all=False):
                if "fixed" in p.opts:
                    candidates.insert(0, p.mountpoint)
                else:
                    candidates.append(p.mountpoint)

            primary_usage = None
            for mp in candidates:
                primary_usage = DiskDeepMetrics._safe_disk_usage(mp)
                if primary_usage:
                    break

            if not primary_usage:
                return {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "error": "No accessible disks found (drives may not be ready or are restricted)."
                }

            disk_usage_info = {
                "mountpoint": mp,
                "total": primary_usage.total,
                "used": primary_usage.used,
                "free": primary_usage.free,
                "percent": primary_usage.percent
            }

            # Step 2: Disk I/O stats
            disk_io = psutil.disk_io_counters()
            disk_io_info = {
                "read_count": disk_io.read_count,
                "write_count": disk_io.write_count,
                "read_bytes": disk_io.read_bytes,
                "write_bytes": disk_io.write_bytes,
                "read_time_ms": disk_io.read_time,
                "write_time_ms": disk_io.write_time
            }

            # Step 3: Per-partition usage
            partitions_info = []
            for part in psutil.disk_partitions(all=False):
                usage = DiskDeepMetrics._safe_disk_usage(part.mountpoint)
                if usage:
                    partitions_info.append({
                        "device": part.device,
                        "mountpoint": part.mountpoint,
                        "fstype": part.fstype,
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free,
                        "percent": usage.percent
                    })

            # Step 4: Latency
            read_latency = (disk_io.read_time or 0) / 1000.0
            write_latency = (disk_io.write_time or 0) / 1000.0

            return {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "disk_usage": disk_usage_info,
                "disk_io": disk_io_info,
                "disk_partitions": partitions_info,
                "disk_latency": {
                    "read_latency_seconds": read_latency,
                    "write_latency_seconds": write_latency
                }
            }

        except Exception as e:
            return {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "error": f"Failed to collect deep disk metrics: {str(e)}"
            }
