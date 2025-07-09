import gc
import sys
import tracemalloc
import time

class GarbageCollectorMetrics:
    @staticmethod
    def get_metrics():
        # Trigger GC manually and time it
        start = time.perf_counter()
        collected = gc.collect()
        elapsed = round((time.perf_counter() - start) * 1000, 2)

        # Enable tracemalloc if not already active
        if not tracemalloc.is_tracing():
            tracemalloc.start()

        # Snapshot for memory allocation info
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics("lineno")

        return {
            "gc_enabled": gc.isenabled(),
            "collected_objects": collected,
            "unreachable_objects": len(gc.garbage),
            "gc_duration_ms": elapsed,
            "garbage_threshold": gc.get_threshold(),
            "generation_counts": gc.get_count(),
            "gc_stats": gc.get_stats(),
            "total_tracked_objects": len(gc.get_objects()),
            "top_memory_lines": [
                {
                    "file": str(stat.traceback[0].filename),
                    "line": stat.traceback[0].lineno,
                    "size_kb": round(stat.size / 1024, 2),
                    "count": stat.count
                }
                for stat in top_stats[:10]
            ],
            "tracemalloc_peak_kb": round(tracemalloc.get_traced_memory()[1] / 1024, 2)
        }




# import gc

# class GarbageCollectorMetrics:
#     @staticmethod
#     def get_metrics():
#         gc.collect()  # Trigger garbage collection
#         return {
#             "collected_objects": gc.collect(),
#             "garbage_threshold": gc.get_threshold(),
#         }
