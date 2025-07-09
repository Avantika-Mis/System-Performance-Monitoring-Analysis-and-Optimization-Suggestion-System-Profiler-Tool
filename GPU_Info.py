try:
    import GPUtil
except ImportError:
    GPUtil = None

class GPUMetrics:
    @staticmethod
    def get_metrics():
        if GPUtil is None:
            return {"error": "GPUtil not installed"}
        gpus = GPUtil.getGPUs()
        return [{
            "id": gpu.id,
            "name": gpu.name,
            "load": gpu.load,
            "memory_used": gpu.memoryUsed,
            "memory_total": gpu.memoryTotal,
            "temperature": gpu.temperature
        } for gpu in gpus]