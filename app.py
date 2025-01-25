import subprocess
import psutil
import threading
from flask import Flask, request, jsonify

app = Flask(__name__)

TIMEOUT = 2  # Time limit in seconds
MEMORY_LIMIT_MB = 100  # Memory limit in MB


def monitor_memory(proc, memory_error_flag):
    """Monitor memory usage and terminate the process if it exceeds the limit."""
    try:
        process = psutil.Process(proc.pid)
        while proc.poll() is None:  # While the process is still running
            mem_usage = process.memory_info().rss / (1024 * 1024)  # Convert to MB
            if mem_usage > MEMORY_LIMIT_MB:
                proc.kill()
                memory_error_flag["error"] = "Memory limit exceeded"
                break
    except psutil.NoSuchProcess:
        pass  # Process already terminated


@app.route('/execute', methods=['POST'])
def execute_code():
    # Parse the JSON payload, but do not raise exceptions for invalid JSON
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid JSON payload"}), 400

    if 'code' not in data:
        return jsonify({"error": "Missing 'code' in request"}), 400

    code = data['code']

    if not isinstance(code, str):
        return jsonify({"error": "Code must be a string"}), 400

    if not code.strip():
        return jsonify({"error": "Code cannot be empty"}), 400

    try:
        process = subprocess.Popen(
            ['python3'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Memory monitoring in a separate thread
        memory_error_flag = {"error": None}
        memory_thread = threading.Thread(target=monitor_memory, args=(process, memory_error_flag))
        memory_thread.start()

        # Wait for the process to complete or timeout
        try:
            stdout, stderr = process.communicate(input=code, timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            process.kill()
            return jsonify({"error": "execution timeout"}), 500

        # Join the memory monitoring thread
        memory_thread.join()

        # Check for memory limit errors
        if memory_error_flag["error"]:
            return jsonify({"error": memory_error_flag["error"]}), 500

        # Handle output
        if stdout and stderr:
            return jsonify({"stdout": stdout, "stderr": stderr})
        elif stdout:
            return jsonify({"stdout": stdout})
        elif stderr:
            return jsonify({"stderr": stderr})
        else:
            return jsonify({})

    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
