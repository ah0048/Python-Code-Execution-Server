import psutil
import time
import logging
import multiprocessing
from app.config import Config

logger = logging.getLogger(__name__)

def force_terminate_process(pid: int) -> None:
    """Force terminate a process using psutil."""
    try:
        process = psutil.Process(pid)
        if Config.IS_WINDOWS:
            process.terminate()
        else:
            process.kill()
    except psutil.NoSuchProcess:
        pass
    except Exception as e:
        logger.error(f"Error terminating process {pid}: {e}")

def monitor_memory(pid: int, terminate_event: multiprocessing.Event, result_queue: multiprocessing.Queue) -> None:
    """Monitor memory usage of a process."""
    try:
        process = psutil.Process(pid)
        while not terminate_event.is_set():
            try:
                if not process.is_running():
                    break
                
                mem_usage = process.memory_info().rss / (1024 * 1024)  # Convert to MB
                if mem_usage > Config.MEMORY_LIMIT_MB:
                    logger.warning(f"Memory limit of {Config.MEMORY_LIMIT_MB}MB exceeded")
                    terminate_event.set()
                    result_queue.put({"error": "Memory limit exceeded"})
                    force_terminate_process(pid)
                    break
                    
                time.sleep(0.1)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break
    except Exception as e:
        logger.error(f"Memory monitoring error: {e}")
        terminate_event.set()
