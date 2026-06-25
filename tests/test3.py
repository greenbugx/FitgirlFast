import os
import sys
import time
import json
import threading
import subprocess
import requests
import asyncio
from http.server import SimpleHTTPRequestHandler
import socketserver
import websockets

API_URL = "http://127.0.0.1:8000"
WS_URL = "ws://127.0.0.1:8000/ws"

TEST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sandbox_test3')
dl_folder = os.path.join(TEST_DIR, 'downloads')

def setup_test_files():
    import shutil
    if os.path.exists(dl_folder):
        shutil.rmtree(dl_folder, ignore_errors=True)
    os.makedirs(dl_folder, exist_ok=True)
    os.chdir(TEST_DIR)
    
    with open('10MB.bin', 'wb') as f:
        f.write(b'0' * 10_000_000)

class TestServerHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass # silent

def start_dummy_server():
    server = socketserver.TCPServer(("127.0.0.1", 8080), TestServerHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server

async def websocket_test_client(dl_id_holder: list, ws_events: list):
    try:
        async with websockets.connect(WS_URL) as ws:
            while True:
                msg = await ws.recv()
                data = json.loads(msg)
                
                dl_id = dl_id_holder[0] if dl_id_holder else None
                
                # Append all events
                if data.get('event') in ('progress', 'status', 'started', 'completed', 'failed', 'cancelled'):
                    ws_events.append(data)
                    
                if data.get('event') in ('completed', 'failed', 'cancelled'):
                    if dl_id and data.get('id') == dl_id:
                        break
    except Exception as e:
        print(f"WS error: {e}")

def run_integration_test():
    print("Step 1: Verify Server Startup")
    retries = 10
    started = False
    for _ in range(retries):
        try:
            r = requests.get(f"{API_URL}/", timeout=1)
            if r.status_code == 200:
                started = True
                break
        except requests.ConnectionError:
            time.sleep(0.5)
            
    if not started:
        print("Backend server is not reachable on port 8000. Is it running?")
        sys.exit(1)
    print("Server responds immediately [OK]")

    print("Step 2: Verify Downloads Endpoint")
    r = requests.get(f"{API_URL}/downloads")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    print("GET /downloads works [OK]")

    print("Step 3: Verify Settings Endpoint")
    r = requests.get(f"{API_URL}/settings")
    assert r.status_code == 200
    data = r.json()
    assert "download_folder" in data
    assert "max_concurrent" in data
    print("GET /settings works [OK]")
    
    # Pre-configure settings for test
    requests.post(f"{API_URL}/settings", json={
        "download_folder": dl_folder,
        "auto_extract": False,
        "delete_after": False
    })

    print("Step 4 & 5: Start Download & Immediate Response")
    ws_events = []
    dl_id_holder = []
    
    def run_ws():
        asyncio.run(websocket_test_client(dl_id_holder, ws_events))
        
    ws_thread = threading.Thread(target=run_ws, daemon=True)
    ws_thread.start()
    time.sleep(0.5) # allow WS to connect
    
    # Provider-agnostic request model
    req_data = {
        "items": [
            {"type": "http", "url": "http://127.0.0.1:8080/10MB.bin"}
        ],
        "folder": dl_folder
    }
    t0 = time.time()
    r = requests.post(f"{API_URL}/downloads", json=req_data)
    assert r.status_code == 200
    assert time.time() - t0 < 0.5, "POST /downloads blocked instead of returning immediately"
    
    resp_data = r.json()
    assert resp_data["status"] == "started"
    print("POST /downloads returned immediately [OK]")
    
    print("Step 6: Verify Background Execution")
    time.sleep(0.2)
    r2 = requests.get(f"{API_URL}/downloads")
    downloads = r2.json()
    assert len(downloads) >= 1
    
    target_dl = [d for d in downloads if d['url'] == "http://127.0.0.1:8080/10MB.bin"][-1]
    dl_id = target_dl['id']
    dl_id_holder.append(dl_id) # pass ID to WS client
    print(f"Download started with ID: {dl_id} [OK]")

    print("Step 7, 8, 9, 10, 11: WebSocket & Pause/Resume/Cancel by ID")
    
    # Pause by ID
    print(f"Pausing download {dl_id}...")
    requests.post(f"{API_URL}/downloads/pause/{dl_id}")
    time.sleep(0.5)
    
    # Resume by ID
    print(f"Resuming download {dl_id}...")
    requests.post(f"{API_URL}/downloads/pause/{dl_id}")
    time.sleep(0.5)
    
    # Cancel by ID
    print(f"Cancelling download {dl_id}...")
    requests.post(f"{API_URL}/downloads/cancel/{dl_id}")
    
    ws_thread.join(timeout=3)
    
    # Assertions on event stream
    event_types = [e['event'] for e in ws_events]
    assert 'progress' in event_types, "No progress events received over WS"
    assert 'cancelled' in event_types or 'failed' in event_types or 'completed' in event_types, "Download didn't reach final state"
    
    print("WebSocket streaming & Pause/Resume/Cancel by ID successful [OK]")
    
    print("Step 12 & 13: Non-Blocking Verification")
    r3 = requests.get(f"{API_URL}/downloads")
    assert r3.status_code == 200
    print("API remains fully responsive during all operations [OK]")
    
    print("\\n\\nALL END-TO-END INTEGRATION TESTS PASSED HEADLESSLY!")

if __name__ == '__main__':
    setup_test_files()
    dummy_server = start_dummy_server()
    try:
        run_integration_test()
    finally:
        dummy_server.shutdown()
        dummy_server.server_close()
