import subprocess
from flask import Flask, request, jsonify

app = Flask(__name__)

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

        stdout, stderr = process.communicate(input=code, timeout=5)

        if stdout and stderr:
            return jsonify({
                "stdout": stdout,
                "stderr": stderr
            })
        elif stdout:
            return jsonify({"stdout": stdout})
        elif stderr:
            return jsonify({"stderr": stderr})
        else:
            return jsonify({})

    except subprocess.TimeoutExpired:
        process.kill()
        return jsonify({"error": "Code execution timed out"}), 500

    except Exception:
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
