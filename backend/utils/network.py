import re
import requests

def _clean_url(u: str) -> str:
    u = re.sub(r'\\[nrt].*$', '', u)
    u = u.rstrip('.,;)"\'> \\-')
    return u

SESSION = requests.Session()
SESSION.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/124.0.0.0 Safari/537.36'
})
