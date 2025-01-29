import uuid
import sys
import multiprocessing
import psutil
import io
import traceback
import threading
import logging
from flask import Flask, request, jsonify
from contextlib import redirect_stdout, redirect_stderr
from typing import Dict, Any

# Configure logging for debugging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Dictionary to store session data
sessions: Dict[str, Dict[str, Any]] = {}
TIMEOUT: int = 2  # Time limit in seconds
MEMORY_LIMIT_MB: int = 100  # Memory limit in MB

# List of restricted modules to prevent unauthorized access
RESTRICTED_MODULES = {"os", "sys", "socket", "subprocess", "shutil", "pathlib", "open"}

def restricted_import(name: str, globals=None, locals=None, fromlist=(), level=0):
    """Custom import function that blocks restricted modules."""
    if name in RESTRICTED_MODULES:
        raise PermissionError(f"Importing '{name}' is restricted.")
    return __builtins__["__import__"](name, globals, locals, fromlist, level)

def restricted_environment() -> Dict[str, Any]:
    """Return a restricted execution environment with limited built-ins."""
    return {
        "__builtins__": {
            "abs": abs, "all": all, "any": any, "bin": bin, "bool": bool, "chr": chr,
            "divmod": divmod, "enumerate": enumerate, "filter": filter, "float": float,
            "format": format, "hash": hash, "hex": hex, "int": int, "isinstance": isinstance,
            "issubclass": issubclass, "len": len, "list": list, "map": map, "max": max,
            "min": min, "next": next, "pow": pow, "range": range, "repr": repr, "reversed": reversed,
            "round": round, "set": set, "slice": slice, "sorted": sorted, "str": str,
            "sum": sum, "tuple": tuple, "zip": zip, "print": print,
            "__import__": restricted_import  # Override import to block restricted modules
        }
    }

def execute_with_memory_check(code: str, globals_dict: Dict[str, Any], result_queue: multiprocessing.Queue, terminate_event: multiprocessing.Event) -> None:
    """Execute code in a session with memory monitoring."""
    def monitor_memory():
        """Monitor memory usage and terminate if limit is exceeded."""
        try:
            process = psutil.Process()
            while not terminate_event.is_set():
                mem_usage = process.memory_info().rss / (1024 * 1024)  # Convert to MB
                if mem_usage > MEMORY_LIMIT_MB:
                    logger.warning("Memory limit exceeded. Terminating process.")
                    terminate_event.set()  # Signal to terminate the process
                    result_queue.put({"error": "Memory limit exceeded"})
                    process.kill()
                    break
        except psutil.NoSuchProcess:
            pass  # Process already terminated

    # Start memory monitoring thread
    memory_thread = threading.Thread(target=monitor_memory, daemon=True)
    memory_thread.start()

    try:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exec(code, globals_dict)
        result_queue.put({
            "stdout": stdout.getvalue(),
            "stderr": stderr.getvalue(),
            "globals": globals_dict
        })
    except Exception as e:
        # Create simplified traceback format
        error_type = type(e).__name__
        error_message = str(e)
        simplified_traceback = (
            f"Traceback (most recent call last):\n"
            f" File \"<stdin>\", line 1, in <module>\n"
            f"{error_type}: {error_message}\n"
        )
        result_queue.put({
            "stderr": simplified_traceback,
            "globals": globals_dict
        })

    # Check if terminate event is set (due to memory limit)
    if terminate_event.is_set():
        logger.warning("Process was terminated due to memory limit.")

@app.route('/execute', methods=['POST'])
def execute_code():
    """API endpoint to execute Python code in a controlled environment."""
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid JSON payload"}), 400

    code = data.get('code')
    session_id = data.get('id')  # Optional session ID

    if not code or not isinstance(code, str) or not code.strip():
        return jsonify({"error": "Code must be a non-empty string"}), 400

    # Handle new session creation
    if session_id is None:
        session_id = str(uuid.uuid4())
        globals_dict = restricted_environment()  # Use restricted environment
        result_queue = multiprocessing.Queue()
        terminate_event = multiprocessing.Event()
        sessions[session_id] = {"globals": globals_dict, "queue": result_queue, "terminate_event": terminate_event}

    # Handle existing session
    if session_id not in sessions:
        return jsonify({"error": f"No session found with ID {session_id}"}), 400

    session = sessions[session_id]
    globals_dict = session["globals"]
    result_queue = session["queue"]
    terminate_event = session["terminate_event"]

    # Execute code in the existing session
    process = multiprocessing.Process(target=execute_with_memory_check, args=(code, globals_dict, result_queue, terminate_event))
    process.start()

    process.join(timeout=TIMEOUT)

    # Check if timeout occurred
    if process.is_alive():
        logger.error("Execution timeout. Terminating session.")
        terminate_event.set()
        process.terminate()
        del sessions[session_id]
        return jsonify({"id": session_id, "error": "Execution timeout. Session terminated."}), 500

    # Check if memory limit was exceeded
    if terminate_event.is_set():
        logger.warning("Memory limit exceeded. Terminating session.")
        process.terminate()
        del sessions[session_id]
        return jsonify({"id": session_id, "error": "Memory limit exceeded. Session terminated."}), 500

    # Get execution results
    if not result_queue.empty():
        result = result_queue.get()
        if "error" in result:
            del sessions[session_id]
            return jsonify({"id": session_id, "error": result["error"]}), 500
        sessions[session_id]["globals"] = result.get("globals", globals_dict)
        if "stderr" in result and result["stderr"]:
            return jsonify({"id": session_id, "stderr": result["stderr"]})
        return jsonify({"id": session_id, "stdout": result.get("stdout", "")})

    # If no output is captured, delete the session
    del sessions[session_id]
    return jsonify({"id": session_id, "error": "Unexpected error. Session terminated."}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
