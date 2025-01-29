from flask import Blueprint, jsonify, request, render_template
import multiprocessing
import logging
from app.services.session import create_session, get_session, sessions
from app.services.code_executor import execute_with_memory_check
from app.utils.monitoring import force_terminate_process
from app.config import Config
import time

logger = logging.getLogger(__name__)
main_bp = Blueprint('main', __name__)

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
                    time.sleep(0.1)
                    if process.is_alive():
                        force_terminate_process(pid)
                    process.join(timeout=0.5)
        except Exception as e:
            logger.error(f"Error cleaning up session {session_id}: {e}")
        finally:
            if session_id in sessions:
                del sessions[session_id]

@main_bp.route('/')
def home():
    """Serve the home page."""
    return render_template('index.html')

@main_bp.route('/execute', methods=['POST'])
def execute_code():
    """Handle code execution requests."""
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid JSON payload"}), 400

    code = data.get('code', '')
    session_id = data.get('id')

    if not code or not isinstance(code, str) or not code.strip():
        return jsonify({"error": "Code must be a non-empty string"}), 400

    # Create or validate session
    if session_id is None:
        session_id = create_session()
    elif session_id not in sessions:
        return jsonify({"error": f"No session found with ID {session_id}"}), 400

    session = sessions[session_id]

    try:
        # Clean up existing process if needed
        if session.get("process") and session["process"].is_alive():
            cleanup_session(session_id)
            session_id = create_session()
            session = sessions[session_id]

        # Execute code in separate process
        process = multiprocessing.Process(
            target=execute_with_memory_check,
            args=(code, session["globals"], session["queue"], session["terminate_event"])
        )
        session["process"] = process
        process.start()

        # Wait for completion or timeout
        process.join(timeout=Config.TIMEOUT)

        if process.is_alive():
            logger.error(f"Execution timeout after {Config.TIMEOUT} seconds")
            cleanup_session(session_id)
            return jsonify({
                "id": session_id,
                "error": "Execution timeout. Session terminated."
            }), 500

        if session["terminate_event"].is_set():
            cleanup_session(session_id)
            return jsonify({
                "id": session_id,
                "error": "Memory limit exceeded. Session terminated."
            }), 500

        if not session["queue"].empty():
            result = session["queue"].get()

            if "error" in result:
                cleanup_session(session_id)
                return jsonify({
                    "id": session_id,
                    "error": result["error"]
                }), 500

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
