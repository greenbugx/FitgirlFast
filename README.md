# Fetchra

A modern, high-performance, multi-threaded desktop GUI downloader designed for grabbing game repacks and large multi-part archives. 

Built with a decoupled **FastAPI/Python Backend** and a **Qt6/C++ Frontend**, Fetchra bypasses Cloudflare checks using automated browser instances, decrypts PrivateBin paste strings, and manages concurrent downloads with real-time WebSocket progress streaming.

---

## Key Features

- **Decoupled Architecture**: Features a robust FastAPI background server running the download engine, completely separated from the Qt6 C++ interface. The frontend communicates via REST and WebSockets.
- **PrivateBin Decryptor**: Automatically fetches and decrypts paste links (e.g., `https://paste.fitgirl...#key`) using `AES-GCM` / `PBKDF2` to extract individual parts locally.
- **Smart Link Resolution**:
  - **Playwright Automation**: Headless Edge (Chromium) automation to bypass Cloudflare challenge checks and intercept CDN/download link requests automatically.
- **Download Management**:
  - Multi-threaded downloads with customizable concurrency limits.
  - Resumes interrupted downloads using `.part` temporary files.
  - Real-time streaming of download speed, ETA, and progress via WebSockets.
  - Unique ID-based tracking allowing fine-grained control (Pause, Resume, Cancel) on individual files or the entire queue.
- **Qt6 Desktop UI**:
  - Sleek, high-performance graphical interface powered by Qt6 and C++.

---

## Installation & Setup

### 1. Prerequisites
- **Backend**: Python 3.10+
- **Frontend**: CMake 3.16+ and Qt 6.8+ (including the `Qt6WebSockets` module)

### 2. Install Python Dependencies
Install the required libraries listed in `requirements.txt`:
```bash
pip install -r requirements.txt
```

### 3. Install Playwright Web Browser
Because certain sources use Cloudflare verification, the script uses Playwright with MS Edge to resolve pages. Initialize Playwright using:
```bash
playwright install
```

### 4. Build the Frontend (Qt6)
Open the `frontend` directory in Qt Creator or build via CMake:
```bash
cd frontend
cmake -B build
cmake --build build
```

---

## Roadmap & Planned Features (TODOS)

- [x] **Retry Logic & Backoff**: Downloads now automatically retry up to 3 times with exponential backoff on transient errors.
- [x] **Client-Server Architecture**: Complete separation of Python backend logic and Qt C++ frontend logic.
- [x] **Download Queue (Pause, Resume & Cancel)**: Backend supports individual and global pausing/cancelling using ID tracking and `threading.Event` gates.
- [x] **Session Save / Restore**: Auto-saves the list of queued downloads and settings to a JSON file.
- [x] **Auto-Extraction**: Once all downloaded parts are present and successfully verified, automatically invoke a 7-Zip subprocess to extract the game repack.
- [ ] **Async I/O Rewrite**: Re-architect the backend download engine using `asyncio` and `aiohttp` to replace the thread-pool/semaphore structure.
- [ ] **Bandwidth Limiter & Scheduler**: Add a token-bucket bandwidth throttle and a time scheduler to start downloads during off-peak hours automatically.