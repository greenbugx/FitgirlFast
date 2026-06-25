import os
import json

SESSION_FILE = os.path.join(os.path.expanduser('~'), '.fitgirlfast_session.json')

class SessionManager:
    def __init__(self, event_bus):
        self.event_bus = event_bus
        
    def save_session(self, urls: list, folder: str):
        file_status = {u: 'pending' for u in urls}
        data = {
            'version': 1,
            'folder': folder,
            'urls': urls,
            'selected': list(range(len(urls))),
            'file_status': file_status
        }
        try:
            with open(SESSION_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.event_bus.status_changed.emit(f"Failed to save session: {e}")
            
    def update_session_progress(self, url: str, status: str):
        if not os.path.exists(SESSION_FILE): return
        try:
            with open(SESSION_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            data.setdefault('file_status', {})[url] = status
            with open(SESSION_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception: pass
        
    def clear_session(self):
        try:
            if os.path.exists(SESSION_FILE):
                os.remove(SESSION_FILE)
        except Exception: pass
