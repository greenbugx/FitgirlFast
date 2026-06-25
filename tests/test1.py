import sys
import os
import re

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from backend.main import BackendApp
from backend.resolvers.privatebin import fetch_privatebin_paste
from backend.utils.network import _clean_url

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_cli.py <url>")
        return
        
    paste_url = sys.argv[1]
    if "fuckingfast.co" in paste_url:
        urls = [paste_url]
    else:
        print(f"Fetching from {paste_url} ...")
        try:
            text = fetch_privatebin_paste(paste_url)
        except Exception as e:
            print(f"Failed to fetch paste: {e}")
            return
            
        urls = re.findall(r'https://fuckingfast\.co/\S+', text)
        urls = [_clean_url(u) for u in urls if u]
        
    if not urls:
        print("No urls found.")
        return
        
    print(f"Found {len(urls)} urls. Starting download to ./downloads ...")
    os.makedirs("downloads", exist_ok=True)
    
    app = BackendApp()
    app.start_download(urls[:1], "downloads")

if __name__ == '__main__':
    main()
