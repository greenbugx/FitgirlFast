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

- [] **Retry Logic & Backoff**: Currently, downloads fail with `❌ Error` upon encountering transient network issues or rate limits. Planned to implement a retry loop with exponential backoff (e.g., 3 attempts spaced at 2s, 4s, and 8s) to handle CDN flakiness automatically.

- [] **Async I/O Rewrite**: Re-architect the download engine using `asyncio` and `aiohttp` to replace the thread-pool/semaphore structure. This will provide cleaner concurrency, lower memory overhead, and much simpler cancellation mechanics.

### User Experience & GUI Enhancements

- [] **Download Speed & ETA Display**: Currently, progress is shown as `MB/totalMB`. We plan to calculate a rolling average over the last 5 downloaded chunks to display live download speeds (MB/s) and estimated time remaining (ETA) per file.

- [] **Download Queue (Pause, Resume & Cancel)**: Implement interactive per-file cancel buttons along with a global pause/resume button that cleanly drains the concurrency semaphore without leaving corrupted files.

- [] **System Notifications**: Integrate a notification library like `plyer` or `win10toast` to trigger OS-level desktop notifications when all files are downloaded, or if an error halts a download.

- [] **Session Save / Restore**: Auto-save the list of loaded URLs, checkbox selections, and settings to a JSON file, letting users safely resume their download session after closing/restarting the application.

- [] **Stats Dashboard Tab**: Add a second tab/dashboard in the GUI showing session stats (total data downloaded, average speed, elapsed time, and a bar chart of per-file sizes).

### Preferences & Scheduling

- [] **Persistent Preferences**: Save download directories, parallel download limits, and application settings in a localized `config.json` file (via `appdirs`) so choices survive application restarts.

- [] **Bandwidth Limiter & Scheduler**: Add a token-bucket bandwidth throttle (e.g., caps at 5 MB/s) and a time scheduler to start downloads during off-peak hours (e.g., overnight) automatically.

### Automation & Deployment

- [] **CLI / Headless Mode**: Add a `--no-gui` flag and CLI arguments (e.g., `--paste <url>` and `--out <dir>`) so the script can run on headless systems, servers, NAS units, or VPS environments without requiring Tkinter.

- [] **Auto-Extraction**: Once all downloaded parts are present and successfully verified, automatically invoke a 7-Zip subprocess to extract the game repack and optionally clean up the downloaded part archives.