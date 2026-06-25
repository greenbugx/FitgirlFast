import os
import time
from collections import deque
import requests
from backend.utils.network import SESSION
from backend.utils.filename import _sanitize_fname
from backend.utils.retry import _backoff_delay

MAX_RETRIES = 3
SPEED_WINDOW = 10

class RetryableError(Exception): pass
class CancelledError(Exception): pass

class HttpDownloader:
    def __init__(self, pause_manager, cancel_manager, stats_manager, event_bus):
        self.pause_manager = pause_manager
        self.cancel_manager = cancel_manager
        self.stats_manager = stats_manager
        self.event_bus = event_bus
        
    def download(self, original_url: str, direct_url: str, folder: str):
        last_err = None
        for attempt in range(MAX_RETRIES):
            if self.cancel_manager.is_cancelled(original_url):
                raise CancelledError()
            try:
                self._download_attempt(original_url, direct_url, folder, attempt)
                return
            except CancelledError:
                raise
            except RetryableError as e:
                last_err = e
                if attempt < MAX_RETRIES - 1:
                    delay = _backoff_delay(attempt)
                    self.event_bus.status_changed.emit(f"Retry {attempt+2}/{MAX_RETRIES} in {delay}s for {original_url}")
                    time.sleep(delay)
        raise Exception(f"All {MAX_RETRIES} attempts failed. Last error: {last_err}")
        
    def _download_attempt(self, original_url, direct_url, folder, attempt):
        fname = _sanitize_fname(original_url.split('#')[-1] if '#' in original_url else direct_url.split('/')[-1].split('?')[0])
        fpath = os.path.join(folder, fname)
        part = fpath + '.part'
        
        if os.path.exists(fpath):
            self.stats_manager.update_progress(original_url, 0, 100, 100, 0, 0)
            return 
            
        resume_from = os.path.getsize(part) if os.path.exists(part) else 0
        hdrs = dict(SESSION.headers)
        if resume_from:
            hdrs['Range'] = f'bytes={resume_from}-'
            
        self.event_bus.status_changed.emit(f"Connecting to {direct_url}...")
        
        try:
            with SESSION.get(direct_url, stream=True, headers=hdrs, timeout=30) as r:
                if r.status_code == 429 or r.status_code >= 500:
                    raise RetryableError(f"HTTP {r.status_code}")
                r.raise_for_status()
                
                ct = r.headers.get('content-type', '')
                if 'text/html' in ct.lower():
                    raise RetryableError("Response was HTML")
                    
                total = int(r.headers.get('content-length', 0)) + resume_from
                done = resume_from
                speed_samples = deque(maxlen=SPEED_WINDOW)
                speed_samples.append((time.monotonic(), done))
                
                with open(part, 'ab' if resume_from else 'wb') as f:
                    for chunk in r.iter_content(chunk_size=512*1024):
                        self.pause_manager.wait(original_url)
                        if self.cancel_manager.is_cancelled(original_url):
                            raise CancelledError()
                            
                        if chunk:
                            f.write(chunk)
                            done += len(chunk)
                            now = time.monotonic()
                            speed_samples.append((now, done))
                            
                            t0, b0 = speed_samples[0]
                            dt = now - t0
                            speed = (done - b0) / dt if dt > 0.1 else 0
                            eta = (total - done) / speed if speed > 0 else 0
                            
                            self.stats_manager.update_progress(original_url, len(chunk), total, done, speed, eta)
        except (RetryableError, CancelledError):
            raise
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 416: pass
            elif e.response is not None and e.response.status_code in (429, 500, 502, 503, 504): raise RetryableError(str(e))
            else: raise
        except (requests.ConnectionError, requests.Timeout) as e:
            raise RetryableError(str(e))
            
        if os.path.exists(part):
            file_size = os.path.getsize(part)
            if file_size < 50000:
                with open(part, 'rb') as check_f:
                    head = check_f.read(512)
                if b'<html' in head.lower():
                    os.remove(part)
                    raise RetryableError("HTML downloaded instead of file")
                    
        if os.path.exists(part):
            os.replace(part, fpath)
