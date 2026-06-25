import re
import time
from backend.utils.network import SESSION
from backend.core.browser_manager import _acquire_browser
from backend.utils.retry import MAX_RETRIES, _backoff_delay

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
    if "fuckingfast.co" not in ff_url:
        return ff_url
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
