import threading
import atexit

_thread_local       = threading.local()
_pw_registry        = []          # [(pw, browser), ...]  for atexit cleanup
_pw_registry_lock   = threading.Lock()

def _acquire_browser():
    """Return the calling thread's Edge browser, creating it on first use."""
    if not getattr(_thread_local, 'browser', None):
        from playwright.sync_api import sync_playwright
        pw      = sync_playwright().start()
        browser = pw.chromium.launch(headless=True, channel="msedge")
        _thread_local.pw      = pw
        _thread_local.browser = browser
        with _pw_registry_lock:
            _pw_registry.append((pw, browser))
        print(f"[PW] Edge launched for thread {threading.current_thread().name}")
    return _thread_local.browser

@atexit.register
def _shutdown_all_browsers():
    with _pw_registry_lock:
        for pw, browser in _pw_registry:
            try:
                browser.close()
            except Exception:
                pass
            try:
                pw.stop()
            except Exception:
                pass
        _pw_registry.clear()

