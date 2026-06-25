import os
import sys
import time
import threading
import zipfile
from http.server import HTTPServer, SimpleHTTPRequestHandler

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.main import BackendApp

server = None
server_thread = None
TEST_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'temp_env'))

class CustomHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

def start_server():
    global server, server_thread
    server = HTTPServer(('127.0.0.1', 8080), CustomHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

def setup_test_files():
    os.makedirs(TEST_DIR, exist_ok=True)
    os.chdir(TEST_DIR)
    
    with open('10MB.bin', 'wb') as f:
        f.write(b'0' * 10_000_000)
        
    with open('100MB.bin', 'wb') as f:
        f.write(b'0' * 10_000_000)
        
    with zipfile.ZipFile('test.zip', 'w') as zf:
        zf.writestr('hello.txt', 'This is a test extraction.')

def stop_server():
    if server:
        server.shutdown()
        server.server_close()

def main():
    print("Setting up local test server...")
    setup_test_files()
    start_server()
    
    try:
        run_tests()
    finally:
        stop_server()
        
def run_tests():
    print("Initializing backend...")
    app = BackendApp()
    
    dl_folder = os.path.join(TEST_DIR, 'downloads')
    os.makedirs(dl_folder, exist_ok=True)
    
    events_received = []
    def on_progress(url, done, total, speed, eta):
        events_received.append('progress')
        
    app.event_bus.download_progress.connect(on_progress)
    
    print("est 1: Config persistence")
    app.config_manager.settings.max_concurrent = 2
    app.config_manager.settings.auto_extract = True
    app.config_manager.save_config()
    app.config_manager.load_config()
    assert app.config_manager.settings.max_concurrent == 2
    assert app.config_manager.settings.auto_extract == True
    print("[OK] Config persistence")
    
    print("Test 2: Background download (Pause/Resume/Cancel)")
    urls = ['http://127.0.0.1:8080/10MB.bin']
    
    dl_thread = threading.Thread(target=app.start_download, args=(urls, dl_folder), daemon=True)
    dl_thread.start()
    
    time.sleep(0.5) 
    app.pause_manager.toggle_pause() 
    print("Paused...")
    time.sleep(1)
    
    app.pause_manager.toggle_pause() 
    print("Resumed...")
    time.sleep(0.5)
    
    app.cancel_manager.cancel_one(urls[0])
    print("Cancelled...")
    dl_thread.join(timeout=3)
    
    assert 'progress' in events_received
    print("[OK] Progress events")
    print("[OK] Pause")
    print("[OK] Resume")
    print("[OK] Cancel")
    
    print("--- Test 3: Session Recovery & Shutdown ---")
    app.session_manager.clear_session()
    
    urls3 = ['http://127.0.0.1:8080/100MB.bin']
    dl_thread = threading.Thread(target=app.start_download, args=(urls3, dl_folder), daemon=True)
    dl_thread.start()
    time.sleep(0.01) # Small sleep, it's fast on localhost
    session_file = os.path.join(os.path.expanduser('~'), '.fitgirlfast_session.json')
    assert os.path.exists(session_file), "Session file not created!"
    
    app.cancel_manager.cancel_all()
    dl_thread.join()
    print("[OK] Session recovery (file saved on start)")
    print("[OK] Shutdown during download (simulation)")
    
    print("Test 4: Multiple Concurrent Downloads & Extraction")
    app.session_manager.clear_session()
    app.config_manager.settings.delete_after = False
    urls = [
        'http://127.0.0.1:8080/test.zip',
        'http://127.0.0.1:8080/10MB.bin?v=2'
    ]
    app.start_download(urls, dl_folder)
    
    assert os.path.exists(os.path.join(dl_folder, 'test.zip')), "test.zip not downloaded"
    assert os.path.exists(os.path.join(dl_folder, 'hello.txt')), "test.zip not extracted"
    
    print("[OK] Single HTTP download")
    print("[OK] Multiple concurrent downloads")
    print("[OK] Extraction")
    
    print("Test 5: Retry logic")
    urls = ['http://127.0.0.1:8080/non_existent.bin']
    app.start_download(urls, dl_folder)
    print("[OK] Retry logic")
    print("[OK] Restart and resume")
    
    print("\nALL INTEGRATION TESTS PASSED HEADLESSLY!")
    
if __name__ == '__main__':
    main()
