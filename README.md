# FitgirlFast

A multi-threaded, desktop GUI downloader written in Python for downloading multi-part game repacks hosted on **fuckingfast.co**. 

This downloader resolves download links, bypasses Cloudflare checks using automated browser instances, decrypts PrivateBin paste strings where URLs are typically stored, and manages concurrent downloads with progress bars and resume capability.

---

## Key Features

- **Fitgirls PrivateBin Decryptor**: Automatically fetches and decrypts Fitgirl PrivateBin paste links (e.g., `https://paste.fitgirl-repacks.site/...#key`) containing repack links. It decrypts data client-side using `AES-GCM` / `PBKDF2` to extract individual parts.
- **Smart Link Resolution**:
  - **HTTP Scraper**: Fast direct-scrape method that parses the download token from javascript.
  - **Playwright Automation**: Headless Edge (Chromium) automation to load pages, pass Cloudflare challenge checks, and intercept CDN/download link popup requests automatically.
- **Download Management**:
  - Multi-threaded downloads with custom concurrency limits (recommended $\le 3$ to avoid rate limiting).
  - Resumes interrupted downloads using `.part` temporary files.
  - File integrity check (auto-removes empty/small files or accidental HTML downloads).
- **Desktop UI (Tkinter)**:
  - Scrollable file list panel with custom checkboxes for selecting parts.
  - Bulk select tools: Select All, Select None, Invert Selection, and Range-based selection (e.g., download parts 5 through 20).
  - Individual visual progress bars and overall task progress bar.

---

## Installation & Setup

### 1. Prerequisites
Ensure you have Python 3.10+ installed on your system.

### 2. Install Python Dependencies
Install the required libraries listed in `requirements.txt`:
```bash
pip install -r requirements.txt
```

### 3. Install Playwright Web Browser
Because **fuckingfast.co** uses Cloudflare verification, the script uses Playwright with MS Edge to resolve pages. Initialize Playwright using:
```bash
playwright install
```
*(Ensure you have Microsoft Edge installed on your Windows system, as the code uses `channel="msedge"`. Alternatively, you can edit the browser launch arguments in `ff.py` to use standard chromium).*

---

## How to Use

Run the main downloader script:
```bash
python ff.py
```

### Step-by-Step Guide:
1. **Load URLs**: 
   - Paste a **Fitgirl PrivateBin** URL containing your repack links into the **PrivateBin / paste URL** field and click **Fetch & Decrypt**.
   - *Alternatively*, paste the direct **fuckingfast.co** download links (one per line) directly into the text area and click **Load from text box**.
2. **Configure Settings**:
   - Set the output directory in **Save to**.
   - Configure **Parallel downloads** (concurrency). It is recommended to keep this at or below 3.
3. **Select Parts**:
   - Use the checkbox list to select which part files you want to download. You can use the bulk action buttons (All, None, Invert, or Range) to quickly select what you need.
4. **Download**:
   - Click the **Start Download** button. The application will resolve and download the parts concurrently, showing real-time speeds and progress.

---

## Roadmap & Planned Features (TODOS)

The following features and improvements are planned for future releases to enhance robustness, usability, and automation:

### Core Improvements & Robustness

- [x] **Retry Logic & Backoff**: Downloads now automatically retry up to 3 times with exponential backoff (2s → 4s → 8s) on transient errors (timeouts, connection resets, HTTP 429/5xx, HTML-instead-of-file CDN glitches). Both URL resolution and file download phases have independent retry loops. The UI status label shows the current retry attempt in real-time.

- [ ] **Async I/O Rewrite**: Re-architect the download engine using `asyncio` and `aiohttp` to replace the thread-pool/semaphore structure. This will provide cleaner concurrency, lower memory overhead, and much simpler cancellation mechanics.

- [ ] **Complete Architecture Rewrite**: Migrate the project from a monolithic Tkinter-based application into a modern client-server desktop architecture using **Qt 6** as the frontend and still using **python** as the backend.

### User Experience & GUI Enhancements

- [x] **Download Speed & ETA Display**: Status label now shows live speed (MB/s) and estimated time remaining (e.g. `12/100MB 5.2MB/s ~1m 30s`) computed from a rolling window of the last 10 chunks via `collections.deque`. Includes a `_fmt_eta()` helper that formats seconds as `42s`, `3m 12s`, or `1h 05m`.

- [x] **Download Queue (Pause, Resume & Cancel)**: Each file row now has a `✕` cancel button. The bottom bar includes a global `⏸ Pause` / `▶ Resume` toggle and a `⏹ Cancel All` button. Pause blocks all download threads on a `threading.Event.wait()` gate inside the chunk loop; resume sets the event to unblock. Cancel sets a per-URL event that the chunk loop checks on every iteration, raising a `_CancelledError` for clean teardown. `.part` files are preserved so cancelled downloads can be resumed later.

- [ ] **System Notifications**: Integrate a notification library like `plyer` or `win10toast` to trigger OS-level desktop notifications when all files are downloaded, or if an error halts a download.

- [x] **Session Save / Restore**: Auto-saves the list of loaded URLs, checkbox selections, and settings to a JSON file, letting users safely resume their download session after closing/restarting the application.

- [x] **Stats Dashboard Tab**: Add a second tab/dashboard in the GUI showing session stats (total data downloaded, average speed, elapsed time, and a bar chart of per-file sizes).

### Preferences & Scheduling

- [x] **Persistent Preferences**: Saves download directories, parallel download limits, and application settings and more in a localized `config.json` file (via `appdirs`) so choices survive application restarts.

- [ ] **Bandwidth Limiter & Scheduler**: Add a token-bucket bandwidth throttle (e.g., caps at 5 MB/s) and a time scheduler to start downloads during off-peak hours (e.g., overnight) automatically.

### Automation & Deployment

~~- [ ] **CLI / Headless Mode**: Add a `--no-gui` flag and CLI arguments (e.g., `--paste <url>` and `--out <dir>`) so the script can run on headless systems, servers, NAS units, or VPS environments without requiring Tkinter.~~

- [x] **Auto-Extraction**: Once all downloaded parts are present and successfully verified, automatically invoke a 7-Zip subprocess to extract the game repack and optionally clean up the downloaded part archives. *(Note: 7-Zip must be installed on the system and either added to PATH or installed in the default `C:\Program Files\7-Zip` directory for this to work).*