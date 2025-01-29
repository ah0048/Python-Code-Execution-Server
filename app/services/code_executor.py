import io
import threading
import multiprocessing
from contextlib import redirect_stdout, redirect_stderr
from typing import Dict, Any
from app.utils.monitoring import monitor_memory
from app.config import Config

def execute_with_memory_check(
    code: str,
    globals_dict: Dict[str, Any],
    result_queue: multiprocessing.Queue,
    terminate_event: multiprocessing.Event
) -> None:
    """Execute code in a monitored environment with memory limits."""
    # Start memory monitoring in a separate thread
    memory_thread = threading.Thread(
        target=monitor_memory,
        args=(multiprocessing.current_process().pid, terminate_event, result_queue),
        daemon=True
    )
    memory_thread.start()

    try:
        stdout = io.StringIO()
        stderr = io.StringIO()
        
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exec(code, globals_dict)

        if not terminate_event.is_set():
            result_queue.put({
                "stdout": stdout.getvalue(),
                "stderr": stderr.getvalue(),
                "globals": globals_dict
            })
    except Exception as e:
        if not terminate_event.is_set():
            error_msg = (
                f"Traceback (most recent call last):\n"
                f" File \"<stdin>\", line 1, in <module>\n"
                f"{type(e).__name__}: {str(e)}\n"
            )
            result_queue.put({
                "stderr": error_msg,
                "globals": globals_dict
            })
