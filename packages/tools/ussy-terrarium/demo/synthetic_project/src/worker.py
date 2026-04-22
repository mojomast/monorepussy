"""Background task queue processor."""

import threading
import queue
import time
from typing import Callable, Any

_task_queue = queue.Queue()
_workers: list = []


class TaskWorker(threading.Thread):
    """Worker thread that processes tasks from the queue."""

    def __init__(self, worker_id: int):
        super().__init__(daemon=True)
        self.worker_id = worker_id
        self.running = True

    def run(self):
        while self.running:
            try:
                task = _task_queue.get(timeout=1)
                self.process_task(task)
            except queue.Empty:
                continue

    def process_task(self, task: dict):
        """Process a single task."""
        func = task["func"]
        args = task.get("args", [])
        kwargs = task.get("kwargs", {})

        try:
            result = func(*args, **kwargs)
            if "callback" in task:
                task["callback"](result)
        except Exception as e:
            if "errback" in task:
                task["errback"](e)

    def stop(self):
        self.running = False


def enqueue_task(func: Callable, *args, **kwargs) -> dict:
    """Add a task to the queue."""
    task = {
        "func": func,
        "args": args,
        "kwargs": kwargs,
    }
    _task_queue.put(task)
    return task


def start_workers(count: int = 4):
    """Start the worker threads."""
    for i in range(count):
        worker = TaskWorker(i)
        worker.start()
        _workers.append(worker)


def stop_workers():
    """Stop all worker threads."""
    for worker in _workers:
        worker.stop()
    _workers.clear()
