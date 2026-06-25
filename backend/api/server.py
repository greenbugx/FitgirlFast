from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio
import threading
from typing import List
import dataclasses
from backend.main import BackendApp
from backend.api.schemas import DownloadRequest, SettingsUpdate

app = FastAPI(title="FitGirlFast Local API")

backend_app = BackendApp()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()
loop = None

@app.on_event("startup")
def on_startup():
    global loop
    loop = asyncio.get_running_loop()

def broadcast_sync(message: dict):
    if loop is not None and loop.is_running():
        asyncio.run_coroutine_threadsafe(manager.broadcast(message), loop)

def on_started(id):
    broadcast_sync({"event": "started", "id": id})

def on_progress(id, done, total, speed, eta):
    pct = (done / total * 100) if total > 0 else 0
    broadcast_sync({
        "event": "progress",
        "id": id,
        "progress": round(pct, 1),
        "downloaded": done,
        "total": total,
        "speed": speed,
        "eta": eta
    })

def on_status(msg):
    broadcast_sync({"event": "status", "message": msg})

def on_completed(id):
    broadcast_sync({"event": "completed", "id": id})

def on_failed(id, err):
    broadcast_sync({"event": "failed", "id": id, "error": str(err)})

backend_app.event_bus.download_started.connect(on_started)
backend_app.event_bus.download_progress.connect(on_progress)
backend_app.event_bus.status_changed.connect(on_status)
backend_app.event_bus.download_completed.connect(on_completed)
backend_app.event_bus.download_failed.connect(on_failed)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/")
def health_check():
    return {"status": "ok"}

@app.get("/settings")
def get_settings():
    return dataclasses.asdict(backend_app.config_manager.settings)

@app.post("/settings")
def update_settings(update: SettingsUpdate):
    cfg = backend_app.config_manager.settings
    if update.download_folder is not None: cfg.download_folder = update.download_folder
    if update.max_concurrent is not None: cfg.max_concurrent = update.max_concurrent
    if update.auto_extract is not None: cfg.auto_extract = update.auto_extract
    if update.delete_after is not None: cfg.delete_after = update.delete_after
    backend_app.config_manager.save_config()
    return {"status": "success", "settings": dataclasses.asdict(cfg)}

@app.get("/downloads")
def get_downloads():
    return [dataclasses.asdict(dl) for dl in backend_app.stats_manager.downloads.values()]

@app.post("/downloads")
def start_download(req: DownloadRequest):
    folder = req.folder or backend_app.config_manager.settings.download_folder
    items = [dict(type=item.type, url=item.url) for item in req.items]
    t = threading.Thread(target=backend_app.start_download, args=(items, folder), daemon=True)
    t.start()
    return {"status": "started", "items": items}

@app.post("/downloads/pause")
def toggle_pause():
    backend_app.pause_manager.toggle_pause()
    return {"status": "toggled_pause"}

@app.post("/downloads/pause/{id:path}")
def toggle_pause_one(id: str):
    backend_app.pause_manager.toggle_pause_one(id)
    return {"status": "toggled_pause_one"}

@app.post("/downloads/cancel")
def cancel_all():
    backend_app.cancel_manager.cancel_all()
    return {"status": "cancelled_all"}

@app.post("/downloads/cancel/{id:path}")
def cancel_one(id: str):
    backend_app.cancel_manager.cancel_one(id)
    return {"status": "cancelled_one"}
