#!/usr/bin/env python3
"""
Fitgirl FuckingFast Multi-Downloader
Supports: PrivateBin paste URL auto-fetch, file selection, concurrent downloads, resume (.part files)
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import requests
import os
import re
import time
import json
import base64
import zlib
import atexit
from collections import deque

# Retry / backoff config

MAX_RETRIES    = 3          # total attempts per operation
BACKOFF_BASE_S = 2          # first retry waits 2s, then 4s, then 8s
SPEED_WINDOW   = 10         # number of chunks used for rolling speed average

def _backoff_delay(attempt: int) -> float:
    return BACKOFF_BASE_S * (2 ** attempt)   # 2, 4, 8, …

def _fmt_eta(seconds: float) -> str:
    """Format seconds into a human-readable ETA string."""
    if seconds < 0 or seconds > 359_999:     # > ~100 hours
        return '—'
    s = int(seconds)
    if s < 60:
        return f'{s}s'
    m, s = divmod(s, 60)
    if m < 60:
        return f'{m}m {s:02d}s'
    h, m = divmod(m, 60)
    return f'{h}h {m:02d}m'

def _clean_url(u: str) -> str:
    # Remove literal escape sequences (\n, \r, \t) and anything after them
    u = re.sub(r'\\[nrt].*$', '', u)
    # Strip remaining trailing chars that aren't part of valid URLs
    u = u.rstrip('.,;)"\'> \\-')
    return u

def _sanitize_fname(raw: str) -> str:
    # Remove: \ / : * ? " < > | and control chars
    cleaned = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '', raw)
    # Strip leading/trailing whitespace, dots, dashes
    cleaned = cleaned.strip().strip('.-')
    return cleaned if cleaned else 'unnamed_download'

# PrivateBin Decryption

BASE58_ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'

def base58_decode(s):
    num = 0
    for char in s:
        if char not in BASE58_ALPHABET:
            raise ValueError(f"Invalid base58 char: {char}")
        num = num * 58 + BASE58_ALPHABET.index(char)
    return num.to_bytes((num.bit_length() + 7) // 8, 'big') if num else b'\x00'

def _pad_b64(s):
    return s + '=' * (-len(s) % 4)

def decrypt_privatebin_v2(paste_data, key_str):
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    key_bytes = base58_decode(key_str)
    adata     = paste_data['adata']
    ct_b64    = paste_data['ct']

    iv_b64, salt_b64, iterations, keylen_bits = adata[0][:4]
    compression = adata[0][7] if len(adata[0]) > 7 else 'zlib'

    iv   = base64.b64decode(_pad_b64(iv_b64))
    salt = base64.b64decode(_pad_b64(salt_b64))
    ct   = base64.b64decode(_pad_b64(ct_b64))

    kdf         = PBKDF2HMAC(algorithm=hashes.SHA256(), length=keylen_bits // 8,
                              salt=salt, iterations=iterations)
    derived_key = kdf.derive(key_bytes)
    aesgcm      = AESGCM(derived_key)
    aad         = json.dumps(adata, separators=(',', ':')).encode()
    plaintext   = aesgcm.decrypt(iv, ct, aad)

    if compression == 'zlib':
        plaintext = zlib.decompress(plaintext, -15)
    return plaintext.decode('utf-8')

def fetch_privatebin_paste(full_url):
    if '#' not in full_url:
        raise ValueError("URL has no key fragment (#...)")

    base_url, key_str = full_url.split('#', 1)
    headers = {'X-Requested-With': 'JSONHttpRequest', 'User-Agent': 'Mozilla/5.0'}

    resp = requests.get(base_url, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    if 'status' in data and data['status'] != 0:
        raise RuntimeError(f"Paste server error: {data.get('message', data['status'])}")

    if data.get('v', 1) == 2:
        return decrypt_privatebin_v2(data, key_str)

    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    spec     = data['data']
    iv_b64   = spec[0]
    salt_b64 = spec[1]
    its      = spec[2]
    klen     = spec[3]
    ct_b64   = data['data'][-1] if isinstance(data['data'], list) else data['ct']

    key_bytes   = base58_decode(key_str)
    iv          = base64.b64decode(_pad_b64(iv_b64))
    salt        = base64.b64decode(_pad_b64(salt_b64))
    ct          = base64.b64decode(_pad_b64(ct_b64))
    kdf         = PBKDF2HMAC(algorithm=hashes.SHA256(), length=klen // 8, salt=salt, iterations=its)
    derived_key = kdf.derive(key_bytes)
    aesgcm      = AESGCM(derived_key)
    aad         = json.dumps(data['adata'], separators=(',', ':')).encode() if 'adata' in data else b''
    plain       = aesgcm.decrypt(iv, ct, aad)
    return zlib.decompress(plain, -15).decode('utf-8')

# HTTP session

SESSION = requests.Session()
SESSION.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/124.0.0.0 Safari/537.36'
})

# Playwright browser pool (one Edge instance per thread, lazily created)

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

# Method 1 — HTTP scrape: GET the file page, extract window.open URL from JS

def _extract_dl_url_from_html(html: str) -> str | None:
    """
    Parse the fuckingfast file page HTML and extract the real download URL
    from the download() JavaScript function.

    The page contains something like:
        function download() {
            ...
            window.open("https://dl.fuckingfast.co/dl/TOKEN...")
            ...
        }
    """
    # Primary: look for the window.open URL pointing to the CDN
    m = re.search(
        r'window\.open\(\s*"(https?://dl[^"]*\.fuckingfast\.co/dl/[^"]+)"',
        html,
    )
    if m:
        return m.group(1)

    # Fallback: any dl.fuckingfast.co URL anywhere in the page
    m = re.search(r'https?://dl[^"\s\'<>]*\.fuckingfast\.co/dl/[^"\s\'<>]+', html)
    if m:
        return m.group(0)

    return None


def get_direct_url_http(ff_url: str) -> str | None:
    """GET the file page with requests and regex-extract the download URL.
    Fast but may fail if Cloudflare serves a challenge page."""
    base = ff_url.split('#')[0]
    try:
        r = SESSION.get(base, timeout=15, allow_redirects=True)
        r.raise_for_status()
    except Exception as e:
        print(f"[HTTP] GET failed for {base}: {e}")
        return None

    url = _extract_dl_url_from_html(r.text)
    if url:
        print(f"[HTTP] Found download URL in page source")
        return url

    # Check if we got a Cloudflare challenge instead of the real page
    if 'challenge-platform' in r.text or 'Just a moment' in r.text:
        print(f"[HTTP] Cloudflare challenge detected — need Playwright")
    else:
        print(f"[HTTP] No download URL found in page source")

    return None

# Method 2 — Playwright: load page in Edge, extract URL from rendered source

def get_direct_url_playwright(ff_url: str) -> str | None:
    """
    Load the fuckingfast page in headless Edge (bypasses Cloudflare),
    then extract the download URL from the page's JavaScript.
    """

    base = ff_url.split('#')[0]

    browser = _acquire_browser()
    context = browser.new_context(
        user_agent=SESSION.headers['User-Agent'],
        accept_downloads=True,
    )

    try:
        page = context.new_page()
        page.goto(base, wait_until='networkidle', timeout=30_000)

        # Strategy 1: extract the URL from the page source
        html = page.content()
        url  = _extract_dl_url_from_html(html)
        if url:
            print(f"[PW] Found download URL in page source: {url[:120]}")
            return url

        # Strategy 2: evaluate JS to call the download function logic
        # Extract the URL that download() would window.open()
        try:
            url = page.evaluate("""() => {
                // Look through all script elements for the window.open URL
                for (const s of document.querySelectorAll('script')) {
                    if (!s.textContent) continue;
                    const m = s.textContent.match(
                        /window\\.open\\("(https?:\\/\\/dl[^"]*\\.fuckingfast\\.co\\/dl\\/[^"]+)"/
                    );
                    if (m) return m[1];
                }
                return null;
            }""")
            if url:
                print(f"[PW] Found download URL via JS evaluation: {url[:120]}")
                return url
        except Exception as e:
            print(f"[PW] JS evaluation failed: {e}")

        # Strategy 3: click DOWNLOAD and capture the popup URL
        print(f"[PW] URL not in source — clicking DOWNLOAD button…")
        captured = []

        def _on_popup(popup):
            try:
                popup_url = popup.url
                if popup_url and 'fuckingfast.co/dl/' in popup_url:
                    captured.append(popup_url)
                    print(f"[PW] Captured popup URL: {popup_url[:120]}")
                popup.close()
            except Exception:
                pass

        # Intercept requests going to the CDN
        def _on_request(request):
            if captured:
                return
            if re.search(r'dl\d*\.fuckingfast\.co/dl/', request.url):
                captured.append(request.url)
                print(f"[PW] Captured CDN request: {request.url[:120]}")

        page.on('popup', _on_popup)
        page.on('request', _on_request)

        # Click the download button
        for selector in (
            'button:has-text("DOWNLOAD")',
            'a:has-text("DOWNLOAD")',
            '.gay-button',
            '.link-button',
            'text=DOWNLOAD',
        ):
            try:
                page.click(selector, timeout=5_000)
                break
            except Exception:
                continue

        # Wait for a capture
        deadline = time.time() + 10
        while not captured and time.time() < deadline:
            page.wait_for_timeout(300)

        return captured[0] if captured else None

    except Exception as e:
        print(f"[PW] Error on {base}: {e}")
        return None
    finally:
        try:
            context.close()
        except Exception:
            pass

# Unified resolver —> tries all methods in order with retry + backoff

def _resolve_once(ff_url: str) -> str | None:
    for label, fn in (
        ('HTTP',       get_direct_url_http),
        ('Playwright', get_direct_url_playwright),
    ):
        try:
            url = fn(ff_url)
            if url:
                print(f"[URL] Resolved via {label}: {url}")
                return url
        except Exception as e:
            print(f"[URL] {label} raised: {e}")
    return None

def resolve_download_url(ff_url: str, status_cb=None) -> str | None:
    """
    Resolve the direct download URL for a fuckingfast page
    Retries up to MAX_RETRIES times with exponential backoff when all
    methods fail (transient Cloudflare blocks, rate-limits, etc)

    status_cb(msg)  —> optional callback to report retry status to the UI
    """
    for attempt in range(MAX_RETRIES):
        url = _resolve_once(ff_url)
        if url:
            return url

        if attempt < MAX_RETRIES - 1:
            delay = _backoff_delay(attempt)
            tag   = f"[URL] Attempt {attempt + 1}/{MAX_RETRIES} failed"
            print(f"{tag} for {ff_url} — retrying in {delay:.0f}s…")
            if status_cb:
                status_cb(f"Retry {attempt + 2}/{MAX_RETRIES} in {delay:.0f}s…")
            time.sleep(delay)

    print(f"[URL] All {MAX_RETRIES} attempts exhausted for {ff_url}")
    return None

# GUI

class DownloaderApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("FitGirlFast - fuckingfast.co")
        self.root.geometry("980x740")
        self.root.minsize(700, 500)

        self.download_folder = tk.StringVar(value=os.path.expanduser("~/Downloads"))
        self.max_concurrent  = tk.IntVar(value=3)
        self.urls:       list[str]          = []
        self.file_vars:  list[tk.BooleanVar] = []
        self.prog_bars:  dict[str, ttk.Progressbar] = {}
        self.stat_labels: dict[str, ttk.Label]       = {}
        self.cancel_btns: dict[str, ttk.Button]      = {} 
        self._lock    = threading.Lock()
        self.completed = 0
        self.total_sel = 0

        # Pause / Cancel state
        self._cancel_events: dict[str, threading.Event] = {} 
        self._pause_event = threading.Event()                
        self._pause_event.set()                               
        self._downloading = False                             

        self._build_ui()

    def _build_ui(self):
        frm_paste = ttk.LabelFrame(self.root, text="Load file list", padding=8)
        frm_paste.pack(fill=tk.X, padx=10, pady=(8, 4))

        row = ttk.Frame(frm_paste)
        row.pack(fill=tk.X)
        ttk.Label(row, text="PrivateBin / paste URL:").pack(side=tk.LEFT)
        self.var_paste_url = tk.StringVar()
        ttk.Entry(row, textvariable=self.var_paste_url, width=65).pack(side=tk.LEFT, padx=6)
        ttk.Button(row, text="Fetch & Decrypt", command=self._fetch_paste).pack(side=tk.LEFT)

        ttk.Separator(frm_paste, orient='horizontal').pack(fill=tk.X, pady=6)
        ttk.Label(frm_paste, text="— or paste URLs directly (one per line) —").pack(anchor=tk.W)
        self.txt_urls = scrolledtext.ScrolledText(frm_paste, height=4, wrap=tk.NONE)
        self.txt_urls.pack(fill=tk.X)
        ttk.Button(frm_paste, text="Load from text box ↓", command=self._load_from_text)\
            .pack(anchor=tk.E, pady=(4, 0))

        frm_set = ttk.LabelFrame(self.root, text="Settings", padding=8)
        frm_set.pack(fill=tk.X, padx=10, pady=4)

        r1 = ttk.Frame(frm_set); r1.pack(fill=tk.X)
        ttk.Label(r1, text="Save to:").pack(side=tk.LEFT)
        ttk.Entry(r1, textvariable=self.download_folder, width=55).pack(side=tk.LEFT, padx=6)
        ttk.Button(r1, text="Browse…", command=self._browse).pack(side=tk.LEFT)

        r2 = ttk.Frame(frm_set); r2.pack(fill=tk.X, pady=(4, 0))
        ttk.Label(r2, text="Parallel downloads:").pack(side=tk.LEFT)
        ttk.Spinbox(r2, from_=1, to=5, textvariable=self.max_concurrent, width=4)\
            .pack(side=tk.LEFT, padx=6)
        ttk.Label(r2, text="(keep ≤ 3 to avoid rate-limits)", foreground='gray').pack(side=tk.LEFT)

        frm_files = ttk.LabelFrame(self.root, text="Step 3 – Select files", padding=8)
        frm_files.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)

        btn_row = ttk.Frame(frm_files); btn_row.pack(fill=tk.X)
        ttk.Button(btn_row, text="✔ All",    command=self._sel_all  ).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="✘ None",   command=self._sel_none ).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="⇌ Invert", command=self._sel_inv  ).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="Range…",   command=self._sel_range).pack(side=tk.LEFT, padx=2)
        self.lbl_count = ttk.Label(btn_row, text="", foreground='gray')
        self.lbl_count.pack(side=tk.RIGHT)

        outer = ttk.Frame(frm_files); outer.pack(fill=tk.BOTH, expand=True, pady=(4, 0))
        self.canvas = tk.Canvas(outer, highlightthickness=0)
        vsb = ttk.Scrollbar(outer, orient='vertical', command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.inner = ttk.Frame(self.canvas)
        self._canvas_win = self.canvas.create_window((0, 0), window=self.inner, anchor='nw')
        self.inner.bind('<Configure>',
                        lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.bind('<Configure>',
                         lambda e: self.canvas.itemconfig(self._canvas_win, width=e.width))
        self.canvas.bind_all('<MouseWheel>',
                             lambda e: self.canvas.yview_scroll(-1 * (e.delta // 120), 'units'))

        frm_bot = ttk.Frame(self.root); frm_bot.pack(fill=tk.X, padx=10, pady=(0, 8))
        self.btn_start = ttk.Button(frm_bot, text="▶  Start Download",
                                    command=self._start, style='Accent.TButton')
        self.btn_start.pack(side=tk.RIGHT, padx=(6, 0))

        self.btn_pause = ttk.Button(frm_bot, text="⏸ Pause",
                                    command=self._toggle_pause, state='disabled')
        self.btn_pause.pack(side=tk.RIGHT, padx=(4, 0))

        self.btn_cancel_all = ttk.Button(frm_bot, text="⏹ Cancel All",
                                         command=self._cancel_all, state='disabled')
        self.btn_cancel_all.pack(side=tk.RIGHT, padx=(4, 0))

        self.var_status = tk.StringVar(value="Ready — load a paste or paste URLs above.")
        ttk.Label(frm_bot, textvariable=self.var_status, anchor=tk.W).pack(side=tk.LEFT)
        self.prog_overall = ttk.Progressbar(frm_bot, mode='determinate', length=200)
        self.prog_overall.pack(side=tk.RIGHT, padx=6)

    # helpers 

    def _set_status(self, msg):
        self.root.after(0, lambda: self.var_status.set(msg))

    def _browse(self):
        d = filedialog.askdirectory(initialdir=self.download_folder.get())
        if d:
            self.download_folder.set(d)

    def _sel_all(self):
        for v in self.file_vars: v.set(True)

    def _sel_none(self):
        for v in self.file_vars: v.set(False)

    def _sel_inv(self):
        for v in self.file_vars: v.set(not v.get())

    def _sel_range(self):
        if not self.urls:
            return
        dlg = tk.Toplevel(self.root)
        dlg.title("Select Range")
        dlg.geometry("280x130")
        dlg.resizable(False, False)
        ttk.Label(dlg, text="From part #:").grid(row=0, column=0, padx=10, pady=8, sticky=tk.W)
        fv = tk.IntVar(value=1)
        ttk.Spinbox(dlg, from_=1, to=len(self.urls), textvariable=fv, width=8).grid(row=0, column=1)
        ttk.Label(dlg, text="To part #:").grid(row=1, column=0, padx=10, sticky=tk.W)
        tv = tk.IntVar(value=len(self.urls))
        ttk.Spinbox(dlg, from_=1, to=len(self.urls), textvariable=tv, width=8).grid(row=1, column=1)

        def apply():
            self._sel_none()
            for i in range(fv.get() - 1, tv.get()):
                if i < len(self.file_vars):
                    self.file_vars[i].set(True)
            dlg.destroy()

        ttk.Button(dlg, text="Apply", command=apply).grid(row=2, column=0, columnspan=2, pady=10)

    # loading 

    def _fetch_paste(self):
        url = self.var_paste_url.get().strip()
        if not url:
            messagebox.showerror("Error", "Enter a paste URL first.")
            return
        self._set_status("Fetching & decrypting paste…")
        threading.Thread(target=self._fetch_paste_bg, args=(url,), daemon=True).start()

    def _fetch_paste_bg(self, url):
        try:
            text = fetch_privatebin_paste(url)
            urls = re.findall(r'https://fuckingfast\.co/\S+', text)
            urls = [_clean_url(u) for u in urls if u]
            if not urls:
                self.root.after(0, lambda: messagebox.showwarning(
                    "Warning", "Paste decrypted but no fuckingfast.co URLs found.\n"
                               "Check the paste URL or paste URLs manually."))
                self._set_status("No URLs found in paste.")
                return
            self.root.after(0, lambda: self._load_urls(urls))
            self.root.after(0, lambda: self.txt_urls.delete('1.0', tk.END))
            self.root.after(0, lambda: self.txt_urls.insert('1.0', '\n'.join(urls)))
        except ImportError:
            self.root.after(0, lambda: messagebox.showerror(
                "Missing library",
                "Install cryptography:\n  pip install cryptography\nThen retry."))
            self._set_status("cryptography library missing.")
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Fetch error", str(e)))
            self._set_status(f"Error: {e}")

    def _load_from_text(self):
        raw  = self.txt_urls.get('1.0', tk.END)
        urls = re.findall(r'https://fuckingfast\.co/\S+', raw)
        urls = [_clean_url(u) for u in urls if u]
        if not urls:
            messagebox.showerror("Error", "No fuckingfast.co URLs found in the text box.")
            return
        self._load_urls(urls)

    def _load_urls(self, urls: list[str]):
        self.urls        = urls
        self.file_vars   = []
        self.prog_bars   = {}
        self.stat_labels = {}
        self.cancel_btns = {}

        for w in self.inner.winfo_children():
            w.destroy()

        hdr = ttk.Frame(self.inner); hdr.pack(fill=tk.X, pady=(0, 2))
        ttk.Label(hdr, text=" #",       width=4,  anchor=tk.W).pack(side=tk.LEFT)
        ttk.Label(hdr, text="Filename", width=42, anchor=tk.W).pack(side=tk.LEFT)
        ttk.Label(hdr, text="Progress", width=16, anchor=tk.CENTER).pack(side=tk.LEFT)
        ttk.Label(hdr, text="Status",   width=35, anchor=tk.W).pack(side=tk.LEFT)
        ttk.Separator(self.inner, orient='horizontal').pack(fill=tk.X)

        for i, url in enumerate(urls):
            fname = _sanitize_fname(url.split('#')[-1] if '#' in url else url.split('/')[-1])
            var   = tk.BooleanVar(value=True)
            self.file_vars.append(var)

            row = ttk.Frame(self.inner); row.pack(fill=tk.X, pady=1)
            ttk.Checkbutton(row, variable=var).pack(side=tk.LEFT)
            ttk.Label(row, text=f"{i + 1:03d}. {fname}", width=42, anchor=tk.W).pack(side=tk.LEFT)

            pb = ttk.Progressbar(row, length=150, mode='determinate', maximum=100)
            pb.pack(side=tk.LEFT, padx=4)
            self.prog_bars[url] = pb

            sl = ttk.Label(row, text="Waiting", width=35, anchor=tk.W)
            sl.pack(side=tk.LEFT)
            self.stat_labels[url] = sl

            cb = ttk.Button(row, text="✕", width=3,
                            command=lambda u=url: self._cancel_one(u))
            cb.pack(side=tk.RIGHT, padx=6)
            cb.config(state='disabled')   # enabled when download starts
            self.cancel_btns[url] = cb

        self.lbl_count.config(text=f"{len(urls)} files loaded")
        self._set_status(f"Loaded {len(urls)} files. Select files and click Start.")

    # pause / cancel controls

    def _toggle_pause(self):
        if self._pause_event.is_set():
            self._pause_event.clear()         # pause
            self.btn_pause.config(text="▶ Resume")
            self._set_status("⏸ Paused — click Resume to continue.")
        else:
            self._pause_event.set()            # resume
            self.btn_pause.config(text="⏸ Pause")
            self._set_status(f"Resumed — downloading {self.total_sel} file(s)…")

    def _cancel_one(self, url: str):
        """Signal a single download to abort."""
        ev = self._cancel_events.get(url)
        if ev:
            ev.set()
            self._upd_stat(url, "⏹ Cancelling", 'gray')

    def _cancel_all(self):
        for ev in self._cancel_events.values():
            ev.set()
        # also un-pause so threads can notice the cancel flag
        self._pause_event.set()
        self.btn_pause.config(text="⏸ Pause")
        self._set_status("⏹ Cancelling all downloads…")

    def _is_cancelled(self, url: str) -> bool:
        ev = self._cancel_events.get(url)
        return ev is not None and ev.is_set()

    # downloading

    def _start(self):
        selected = [(url, i) for i, (url, var)
                    in enumerate(zip(self.urls, self.file_vars)) if var.get()]
        if not selected:
            messagebox.showwarning("Nothing selected", "Check at least one file.")
            return

        folder = self.download_folder.get()
        os.makedirs(folder, exist_ok=True)

        self.completed               = 0
        self.total_sel               = len(selected)
        self.prog_overall['maximum'] = self.total_sel
        self.prog_overall['value']   = 0
        self._downloading            = True
        self._pause_event.set()                        # ensure unpaused
        self._cancel_events.clear()
        for url, _ in selected:
            self._cancel_events[url] = threading.Event()  # per-file cancel flag
            btn = self.cancel_btns.get(url)
            if btn:
                btn.config(state='normal')

        self.btn_start.config(state='disabled')
        self.btn_pause.config(state='normal', text="⏸ Pause")
        self.btn_cancel_all.config(state='normal')
        self._set_status(f"Starting {self.total_sel} download(s)…")

        threading.Thread(target=self._run_downloads, args=(selected, folder), daemon=True).start()

    def _run_downloads(self, selected, folder):
        sem     = threading.Semaphore(self.max_concurrent.get())
        threads = [threading.Thread(target=self._dl_one, args=(url, folder, sem), daemon=True)
                   for url, _ in selected]
        for t in threads: t.start()
        for t in threads: t.join()

        self._downloading = False
        self._set_status(f"✔ Done — {self.total_sel} file(s) processed.")
        self.root.after(0, lambda: self.btn_start.config(state='normal'))
        self.root.after(0, lambda: self.btn_pause.config(state='disabled'))
        self.root.after(0, lambda: self.btn_cancel_all.config(state='disabled'))
        # disable all cancel buttons
        for btn in self.cancel_btns.values():
            self.root.after(0, lambda b=btn: b.config(state='disabled'))
        self.root.after(0, lambda: messagebox.showinfo(
            "Finished", f"All {self.total_sel} downloads finished!\nSaved to:\n{folder}"))

    def _upd_stat(self, url, text, color='black'):
        lbl = self.stat_labels.get(url)
        if lbl:
            self.root.after(0, lambda l=lbl, t=text, c=color: l.config(text=t, foreground=c))

    def _upd_prog(self, url, val):
        pb = self.prog_bars.get(url)
        if pb:
            self.root.after(0, lambda p=pb, v=val: p.config(value=v))

    # retryable error helpers

    class _RetryableError(Exception):
        """Raised inside _dl_one_attempt when the error is worth retrying."""

    class _CancelledError(Exception):
        """Raised when a download is cancelled by the user."""

    def _dl_one(self, ff_url, folder, sem):
        sem.acquire()
        try:
            # check cancel before even starting
            if self._is_cancelled(ff_url):
                self._upd_stat(ff_url, "⏹ Cancelled", 'gray')
                self._finish_one()
                return

            # resolve the direct download URL (has its own retries)
            self._upd_stat(ff_url, "Resolving…")
            direct = resolve_download_url(
                ff_url,
                status_cb=lambda msg: self._upd_stat(ff_url, msg),
            )

            if not direct:
                self._upd_stat(ff_url, "❌ No link", 'red')
                self._finish_one()
                return

            # download the file, with retry + backoff
            last_err = None
            for attempt in range(MAX_RETRIES):
                if self._is_cancelled(ff_url):
                    raise self._CancelledError()
                try:
                    self._dl_one_attempt(ff_url, direct, folder, attempt)
                    return      # success
                except self._CancelledError:
                    raise
                except self._RetryableError as e:
                    last_err = e
                    if attempt < MAX_RETRIES - 1:
                        delay = _backoff_delay(attempt)
                        print(f"[DL] Attempt {attempt + 1}/{MAX_RETRIES} failed "
                              f"for {ff_url}: {e} — retrying in {delay:.0f}s…")
                        self._upd_stat(
                            ff_url,
                            f"⟳ Retry {attempt + 2}/{MAX_RETRIES} in {delay:.0f}s",
                            'orange',
                        )
                        time.sleep(delay)

            # all retries exhausted
            self._upd_stat(ff_url, "❌ Error", 'red')
            print(f"[DL] All {MAX_RETRIES} attempts failed for {ff_url}: {last_err}")
            self._finish_one()

        except self._CancelledError:
            self._upd_stat(ff_url, "⏹ Cancelled", 'gray')
            print(f"[DL] Download cancelled for {ff_url}")
            self._finish_one()
        except Exception as e:
            # non-retryable / unexpected error
            self._upd_stat(ff_url, "❌ Error", 'red')
            print(f"[DL] Fatal error on {ff_url}: {e}")
        finally:
            sem.release()
            # disable this file's cancel button
            btn = self.cancel_btns.get(ff_url)
            if btn:
                self.root.after(0, lambda b=btn: b.config(state='disabled'))

    def _dl_one_attempt(self, ff_url, direct, folder, attempt):
        """
        Single download attempt.  Raises _RetryableError for transient
        problems (timeouts, connection resets, rate-limits, HTML responses)
        so the caller can retry with backoff.  Raises _CancelledError if
        cancelled.  Non-transient successes / failures return / raise normally.
        """
        fname = _sanitize_fname(
            ff_url.split('#')[-1] if '#' in ff_url else direct.split('/')[-1].split('?')[0]
        )
        fpath = os.path.join(folder, fname)
        part  = fpath + '.part'

        # already fully downloaded in a previous run
        if os.path.exists(fpath):
            self._upd_stat(ff_url, "✔ Exists", 'green')
            self._upd_prog(ff_url, 100)
            self._finish_one()
            return

        resume_from = os.path.getsize(part) if os.path.exists(part) else 0

        hdrs = dict(SESSION.headers)
        if resume_from:
            hdrs['Range'] = f'bytes={resume_from}-'

        attempt_tag = f" (attempt {attempt + 1}/{MAX_RETRIES})" if attempt else ""
        self._upd_stat(ff_url, f"Connecting…{attempt_tag}")

        try:
            with SESSION.get(direct, stream=True, headers=hdrs, timeout=30) as r:
                # Rate-limit / server error -> retryable
                if r.status_code == 429 or r.status_code >= 500:
                    raise self._RetryableError(
                        f"HTTP {r.status_code} {r.reason}")
                r.raise_for_status()

                # HTML instead of binary -> retryable
                ct = r.headers.get('content-type', '')
                if 'text/html' in ct.lower():
                    peek = next(r.iter_content(chunk_size=1024), b'')
                    print(f"[DL] Got HTML instead of file for {ff_url}")
                    print(f"[DL] Response snippet: {peek[:300]}")
                    raise self._RetryableError("Response was HTML, not a file")

                total = int(r.headers.get('content-length', 0)) + resume_from
                if 0 < total < 50_000:
                    print(f"[DL] WARNING: content-length is only {total} "
                          f"bytes for {ff_url} — likely not a real file")

                done = resume_from
                # rolling speed window: deque of (timestamp, bytes_so_far)
                speed_samples = deque(maxlen=SPEED_WINDOW)
                speed_samples.append((time.monotonic(), done))

                with open(part, 'ab' if resume_from else 'wb') as f:
                    for chunk in r.iter_content(chunk_size=512 * 1024):
                        # pause gate
                        self._pause_event.wait()      # blocks while paused

                        # cancel check
                        if self._is_cancelled(ff_url):
                            raise self._CancelledError()

                        if chunk:
                            f.write(chunk)
                            done += len(chunk)
                            now   = time.monotonic()
                            speed_samples.append((now, done))

                            if total:
                                self._upd_prog(ff_url, done / total * 100)

                                # compute speed & ETA
                                t0, b0 = speed_samples[0]
                                dt = now - t0
                                if dt > 0.1:          # need >0.1s for meaningful speed
                                    speed = (done - b0) / dt          # bytes/s
                                    speed_mb = speed / 1_048_576
                                    remaining = total - done
                                    eta = remaining / speed if speed > 0 else 0
                                    mb     = done  / 1_048_576
                                    tot_mb = total / 1_048_576
                                    self._upd_stat(
                                        ff_url,
                                        f"{mb:.0f}/{tot_mb:.0f}MB "
                                        f"{speed_mb:.1f}MB/s "
                                        f"~{_fmt_eta(eta)}",
                                    )
                                else:
                                    mb     = done  / 1_048_576
                                    tot_mb = total / 1_048_576
                                    self._upd_stat(ff_url, f"{mb:.0f}/{tot_mb:.0f} MB")

        except (self._RetryableError, self._CancelledError):
            raise                     # bubble up for the retry / cancel loop

        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 416:
                pass                  # Range not satisfiable -> already complete
            elif e.response is not None and e.response.status_code in (429, 500, 502, 503, 504):
                raise self._RetryableError(str(e))
            else:
                raise                 

        except (requests.ConnectionError, requests.Timeout) as e:
            raise self._RetryableError(str(e))

        # reject suspiciously small / fake files
        if os.path.exists(part):
            file_size = os.path.getsize(part)
            if file_size < 50_000:
                try:
                    with open(part, 'rb') as check_f:
                        head = check_f.read(512)
                    if b'<html' in head.lower() or b'<!doctype' in head.lower():
                        print(f"[DL] Downloaded file is HTML, not a real file: "
                              f"{fname} ({file_size} bytes)")
                        os.remove(part)
                        raise self._RetryableError("Downloaded file was HTML")
                except (self._RetryableError, self._CancelledError):
                    raise
                except Exception:
                    pass
                print(f"[DL] WARNING: {fname} is only {file_size} bytes — may be corrupt")

        if os.path.exists(part):
            os.replace(part, fpath)
        self._upd_stat(ff_url, "✔ Done", 'green')
        self._upd_prog(ff_url, 100)
        self._finish_one()

    def _finish_one(self):
        with self._lock:
            self.completed += 1
            c = self.completed
        self.root.after(0, lambda: self.prog_overall.config(value=c))
        self._set_status(f"Completed {c}/{self.total_sel}")


# Entry point

def main():
    root = tk.Tk()
    try:
        root.tk.call('source', 'azure.tcl')
        root.tk.call('set_theme', 'light')
    except Exception:
        pass

    app = DownloaderApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()