import re
def _sanitize_fname(raw: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '', raw)
    cleaned = cleaned.strip().strip('.-')
    return cleaned if cleaned else 'unnamed_download'
