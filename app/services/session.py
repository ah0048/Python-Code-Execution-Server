import uuid
import multiprocessing
from typing import Dict, Any, Optional, TypedDict

class SessionData(TypedDict):
    """Type definition for session storage data"""
    globals: Dict[str, Any]
    queue: multiprocessing.Queue
    terminate_event: multiprocessing.Event
    process: Optional[multiprocessing.Process]

# Global sessions storage
sessions: Dict[str, SessionData] = {}

def create_session() -> str:
    """Create a new session and return its ID."""
    from app.services.security import create_restricted_environment
    
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "globals": create_restricted_environment(),
        "queue": multiprocessing.Queue(),
        "terminate_event": multiprocessing.Event(),
        "process": None
    }
    return session_id

def get_session(session_id: str) -> Optional[SessionData]:
    """Retrieve a session by ID."""
    return sessions.get(session_id)
