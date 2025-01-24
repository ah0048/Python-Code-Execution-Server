import io
from contextlib import redirect_stdout, redirect_stderr
from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route('/execute', methods=['POST'], strict_slashes=False)
def execute():
    try:
        data = request.get_json()
        code  = data.get('code', '')
        if not code:
            return jsonify({"error": "you need to provide code for the execution server"}), 400

        stdout = io.StringIO()
        stderr = io.StringIO()

        with redirect_stdout(stdout), redirect_stderr(stderr):
            exec(code)
        
        output = stdout.getvalue()
        errors = stderr.getvalue()

        if errors:
            return jsonify({"stderr": errors})
        else:
            return jsonify({"stdout": output})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
