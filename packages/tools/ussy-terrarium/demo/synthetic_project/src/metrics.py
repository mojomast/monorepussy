"""Metrics collection and reporting."""

import time
from typing import Dict, List
from collections import defaultdict


class MetricsCollector:
    """Collect application metrics."""

    def __init__(self):
        self.counters: Dict[str, int] = defaultdict(int)
        self.timers: Dict[str, List[float]] = defaultdict(list)
        self.gauges: Dict[str, float] = {}

    def increment(self, name: str, value: int = 1):
        """Increment a counter."""
        self.counters[name] += value

    def timing(self, name: str, value: float):
        """Record a timing."""
        self.timers[name].append(value)

    def gauge(self, name: str, value: float):
        """Set a gauge."""
        self.gauges[name] = value

    def get_report(self) -> dict:
        """Generate a metrics report."""
        report = {
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "timers": {},
        }

        for name, values in self.timers.items():
            if values:
                report["timers"][name] = {
                    "count": len(values),
                    "mean": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                }

        return report


def timed(metric_name: str):
    """Decorator to time a function."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            elapsed = time.time() - start

            # In a real app, this would use a singleton collector
            print(f"[METRIC] {metric_name}: {elapsed:.4f}s")

            return result

        return wrapper

    return decorator


# Global metrics instance
metrics = MetricsCollector()
