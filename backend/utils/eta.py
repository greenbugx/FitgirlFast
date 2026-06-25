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
