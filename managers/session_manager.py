import uuid
from datetime import datetime

class SessionManager:
    def __init__(self):
        self.sessions = {}

    async def create_session(self, session_id: str = None):
        sid = session_id or str(uuid.uuid4())
        self.sessions[sid] = {
            "created_at": datetime.utcnow().isoformat(),
            "messages": [],
            "active_model": None
        }
        return sid

    async def add_message(self, session_id: str, message: dict):
        if session_id in self.sessions:
            self.sessions[session_id]["messages"].append(message)
            self.sessions[session_id]["last_activity"] = datetime.utcnow().isoformat()
            return True
        return False

    async def get_session(self, session_id: str):
        return self.sessions.get(session_id)
