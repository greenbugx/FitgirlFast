from datetime import datetime, timezone, timedelta
import tkinter as tk
from tkinter import ttk

def _record_paste_history(self, url: str, file_count: int):
    entry = {
        'url':        url,
        'timestamp':  datetime.now(timezone.utc).isoformat(),
        'file_count': file_count,
    }
    # avoid exact duplicates at the top
    if self._paste_history and self._paste_history[-1].get('url') == url:
        self._paste_history[-1] = entry   # update timestamp
    else:
        self._paste_history.append(entry)
    self._save_config()

def _show_paste_history(self):
    dlg = tk.Toplevel(self.root)
    dlg.title("Paste History")
    dlg.geometry("620x380")
    dlg.resizable(True, True)
    dlg.grab_set()
    dlg.focus_force()

    ttk.Label(
        dlg, text="Recent paste URLs (last 7 days)",
        font=('Segoe UI', 11, 'bold'),
    ).pack(anchor=tk.W, padx=12, pady=(10, 4))

    outer = ttk.Frame(dlg)
    outer.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))

    canvas = tk.Canvas(outer, highlightthickness=0)
    vsb = ttk.Scrollbar(outer, orient='vertical', command=canvas.yview)
    canvas.configure(yscrollcommand=vsb.set)
    vsb.pack(side=tk.RIGHT, fill=tk.Y)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    inner = ttk.Frame(canvas)
    cwin = canvas.create_window((0, 0), window=inner, anchor='nw')
    inner.bind('<Configure>',
                lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
    canvas.bind('<Configure>',
                lambda e: canvas.itemconfig(cwin, width=e.width))

    # show newest first
    history = list(reversed(self._paste_history))

    if not history:
        ttk.Label(inner, text="No paste history yet.",
                    foreground='gray').pack(pady=20)
    else:
        for entry in history:
            url   = entry.get('url', '?')
            ts    = entry.get('timestamp', '')
            count = entry.get('file_count', '?')

            # format timestamp for display
            try:
                dt = datetime.fromisoformat(ts)
                dt_local = dt.astimezone()
                display_ts = dt_local.strftime('%b %d, %H:%M')
            except Exception:
                display_ts = ts[:16] if ts else '?'

            row = ttk.Frame(inner)
            row.pack(fill=tk.X, pady=2)

            # truncate URL for display
            disp_url = url if len(url) <= 70 else url[:67] + '…'
            ttk.Label(
                row, text=disp_url, anchor=tk.W, width=52,
            ).pack(side=tk.LEFT, padx=(4, 0))

            ttk.Label(
                row, text=f"{count} files", foreground='gray', width=8,
            ).pack(side=tk.LEFT)

            ttk.Label(
                row, text=display_ts, foreground='gray', width=12,
            ).pack(side=tk.LEFT)

def _use(u=url):
    self.var_paste_url.set(u)
    dlg.destroy()

    ttk.Button(row, text="Use", width=5, command=_use).pack(
        side=tk.RIGHT, padx=4)

    ttk.Separator(inner, orient='horizontal').pack(fill=tk.X)

    # bottom buttons
    btn_frame = ttk.Frame(dlg)
    btn_frame.pack(pady=(0, 10))

def _clear_history():
    self._paste_history.clear()
    self._save_config()
    dlg.destroy()

    ttk.Button(btn_frame, text="Clear History", command=_clear_history).pack(
        side=tk.LEFT, padx=6)
    ttk.Button(btn_frame, text="Close", command=dlg.destroy).pack(
            side=tk.LEFT, padx=6)

    # center over main window
    dlg.update_idletasks()
    x = self.root.winfo_x() + (self.root.winfo_width()  - dlg.winfo_width())  // 2
    y = self.root.winfo_y() + (self.root.winfo_height() - dlg.winfo_height()) // 2
    dlg.geometry(f"+{x}+{y}")
