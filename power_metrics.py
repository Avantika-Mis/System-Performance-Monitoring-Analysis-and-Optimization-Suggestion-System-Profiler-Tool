from datetime import datetime
import psutil

class PowerMetrics:
    @staticmethod
    def get_metrics():
        battery = psutil.sensors_battery()
        return {
            "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "uptime_seconds": psutil.boot_time(),
            "battery_percent": battery.percent if battery else "N/A",
            "power_plugged": battery.power_plugged if battery else "N/A"
        }
