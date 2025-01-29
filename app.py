"""
Secure Python Code Execution Service

This module provides a Flask-based web service that allows secure execution of Python code
in isolated environments. It implements various security measures including memory limits,
execution timeouts, and module restrictions to prevent malicious code execution.

Key Features:
- Cross-platform compatibility (Windows and Linux)
- Isolated execution environments for each session
- Memory usage monitoring and limits
- Execution timeout controls
- Restricted module imports
- Session management with unique IDs
- Captured stdout/stderr streams

Security Measures:
- Memory limit: 100MB per session
- Execution timeout: 2 seconds
- Restricted system/OS level modules
- Controlled execution environment with limited built-ins
"""

import uuid
import sys
import multiprocessing
import psutil
import io
import threading
import logging
import platform
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from contextlib import redirect_stdout, redirect_stderr
from typing import Dict, Any, Optional, Set, TypedDict
import time

# Configure logging for debugging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Type definitions
class SessionData(TypedDict):
    """Type definition for session storage data"""
    globals: Dict[str, Any]
    queue: multiprocessing.Queue
    terminate_event: multiprocessing.Event
    process: Optional[multiprocessing.Process]

class ExecutionResult(TypedDict, total=False):
    """Type definition for execution results"""
    stdout: str
    stderr: str
    globals: Dict[str, Any]
    error: str

# Global variables
sessions: Dict[str, SessionData] = {}
TIMEOUT: int = 2  # Time limit in seconds
MEMORY_LIMIT_MB: int = 100  # Memory limit in MB
IS_WINDOWS: bool = platform.system() == "Windows"

# Security-critical set of restricted modules
RESTRICTED_MODULES: Set[str] = {
    # Filesystem
    "os", "sys", "shutil", "pathlib", "tempfile",
    # Networking
    "socket", "http", "urllib", "ssl", "requests", "ftplib",
    # System
    "subprocess", "multiprocessing", "ctypes", "threading",
    # Other
    "builtins", "sysconfig"
}

def restricted_import(
    name: str,
    globals: Optional[Dict] = None,
    locals: Optional[Dict] = None,
    fromlist: tuple = (),
    level: int = 0
) -> Any:
    """Custom import function that blocks access to restricted modules."""
    if name in RESTRICTED_MODULES:
        raise PermissionError(f"Importing '{name}' is restricted for security reasons.")
    return __builtins__["__import__"](name, globals, locals, fromlist, level)

def restricted_environment() -> Dict[str, Any]:
    """Create a restricted execution environment with limited built-in functions."""
    safe_builtins = {
        # Mathematical operations
        "abs": abs, "divmod": divmod, "pow": pow, "round": round,
        # Type conversions
        "bool": bool, "int": int, "float": float, "str": str,
        # Data structures
        "list": list, "dict": dict, "set": set, "tuple": tuple,
        # Iterables and sequences
        "enumerate": enumerate, "filter": filter, "map": map, "zip": zip,
        "range": range, "reversed": reversed, "sorted": sorted,
        # Other safe operations
        "len": len, "max": max, "min": min, "sum": sum,
        "print": print, "isinstance": isinstance,
        # Custom restricted import
        "__import__": restricted_import
    }
    return {"__builtins__": safe_builtins}

def force_terminate_process(pid: int) -> None:
    """Force terminate a process using psutil."""
    try:
        process = psutil.Process(pid)
        if IS_WINDOWS:
            process.terminate()  # Use terminate() on Windows
        else:
            process.kill()      # Use kill() on Unix-like systems
    except psutil.NoSuchProcess:
        pass
    except Exception as e:
        logger.error(f"Error terminating process {pid}: {e}")

def cleanup_session(session_id: str) -> None:
    """Clean up session resources safely."""
    if session_id in sessions:
        try:
            session = sessions[session_id]
            session["terminate_event"].set()

            if session.get("process"):
                process = session["process"]
                if process and process.is_alive():
                    pid = process.pid
                    process.terminate()
                    # Give it a short time to terminate gracefully
                    time.sleep(0.1)
                    if process.is_alive():
                        force_terminate_process(pid)
                    process.join(timeout=0.5)
        except Exception as e:
            logger.error(f"Error cleaning up session {session_id}: {e}")
        finally:
            if session_id in sessions:
                del sessions[session_id]

def monitor_memory(pid: int, terminate_event: multiprocessing.Event, result_queue: multiprocessing.Queue) -> None:
    """Cross-platform memory monitoring function."""
    try:
        process = psutil.Process(pid)
        while not terminate_event.is_set():
            try:
                if not process.is_running():
                    break
                mem_usage = process.memory_info().rss / (1024 * 1024)  # Convert to MB
                if mem_usage > MEMORY_LIMIT_MB:
                    logger.warning(f"Memory limit of {MEMORY_LIMIT_MB}MB exceeded")
                    terminate_event.set()
                    result_queue.put({"error": "Memory limit exceeded"})
                    force_terminate_process(pid)
                    break
                time.sleep(0.1)  # Reduce CPU usage
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break
    except Exception as e:
        logger.error(f"Memory monitoring error: {e}")
        terminate_event.set()

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
        # Capture stdout and stderr
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

@app.route('/execute', methods=['POST'])
def execute_code() -> tuple[Any, int]:
    """Flask endpoint for executing Python code in a secure environment."""
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid JSON payload"}), 400

    code: str = data.get('code', '')
    session_id: Optional[str] = data.get('id')

    if not code or not isinstance(code, str) or not code.strip():
        return jsonify({"error": "Code must be a non-empty string"}), 400

    # Create or validate session
    if session_id is None:
        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            "globals": restricted_environment(),
            "queue": multiprocessing.Queue(),
            "terminate_event": multiprocessing.Event(),
            "process": None
        }
    elif session_id not in sessions:
        return jsonify({"error": f"No session found with ID {session_id}"}), 400

    session = sessions[session_id]

    try:
        # Clean up any existing process
        if session.get("process") and session["process"].is_alive():
            cleanup_session(session_id)
            sessions[session_id] = {
                "globals": restricted_environment(),
                "queue": multiprocessing.Queue(),
                "terminate_event": multiprocessing.Event(),
                "process": None
            }
            session = sessions[session_id]

        # Execute code in separate process
        process = multiprocessing.Process(
            target=execute_with_memory_check,
            args=(code, session["globals"], session["queue"], session["terminate_event"])
        )
        session["process"] = process
        process.start()

        # Wait for completion or timeout
        process.join(timeout=TIMEOUT)

        # Handle timeout
        if process.is_alive():
            logger.error(f"Execution timeout after {TIMEOUT} seconds")
            cleanup_session(session_id)
            return jsonify({
                "id": session_id,
                "error": "Execution timeout. Session terminated."
            }), 500

        # Handle memory limit exceeded
        if session["terminate_event"].is_set():
            cleanup_session(session_id)
            return jsonify({
                "id": session_id,
                "error": "Memory limit exceeded. Session terminated."
            }), 500

        # Process execution results
        if not session["queue"].empty():
            result: ExecutionResult = session["queue"].get()

            if "error" in result:
                cleanup_session(session_id)
                return jsonify({
                    "id": session_id,
                    "error": result["error"]
                }), 500

            # Update session globals and return results
            sessions[session_id]["globals"] = result.get("globals", session["globals"])
            if "stderr" in result and result["stderr"]:
                return jsonify({
                    "id": session_id,
                    "stderr": result["stderr"]
                })
            return jsonify({
                "id": session_id,
                "stdout": result.get("stdout", "")
            })

        # Handle unexpected errors
        cleanup_session(session_id)
        return jsonify({
            "id": session_id,
            "error": "Unexpected error. Session terminated."
        }), 500

    except Exception as e:
        logger.error(f"Execution error: {e}")
        cleanup_session(session_id)
        return jsonify({
            "id": session_id,
            "error": "Internal server error"
        }), 500

@app.route('/')
def home():
    """Serve the home HTML page."""
    return render_template('index.html')

if __name__ == '__main__':
    multiprocessing.freeze_support()  # Required for Windows
    app.run(host='0.0.0.0', port=5000, debug=True)
