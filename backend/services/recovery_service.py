def _check_session_on_startup(self):
    if not os.path.exists(SESSION_FILE):
        return
    try:
        with open(SESSION_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        # corrupt JSON -> delete and move on
        self._clear_session()
        return

    pending_urls = [
        url for url, st in data.get('file_status', {}).items()
        if st in ('pending', 'cancelled')  # cancelled mid-stream are also resumable
    ]
    if not pending_urls:
        self._clear_session()
        return

    folder = data.get('folder', '')
    self._show_recovery_dialog(data, pending_urls, folder)

def _show_recovery_dialog(self, session_data, pending_urls, folder):
    preview_names = []
    for url in pending_urls[:3]:
        name = _sanitize_fname(
            url.split('#')[-1] if '#' in url else url.split('/')[-1]
        )
        preview_names.append(name)
    if len(pending_urls) > 3:
        preview_names.append(f"… and {len(pending_urls) - 3} more")
    file_list_text = '\n'.join(f"  • {n}" for n in preview_names)

    # Check which .part files still exist
    parts_found   = 0
    parts_missing = 0
    for url in pending_urls:
        fname = _sanitize_fname(
            url.split('#')[-1] if '#' in url else url.split('/')[-1]
        )
        fpath = os.path.join(folder, fname)
        part  = fpath + '.part'
        if os.path.exists(fpath):
            parts_found += 1          # already fully downloaded
        elif os.path.exists(part):
            parts_found += 1          # resumable partial
        else:
            parts_missing += 1

    # Determine health message
    if parts_missing == len(pending_urls):
        health = (
            "⚠ No .part files were found in the previous download folder.\n"
            f"   ({folder})\n"
            "   Downloads will restart from scratch."
        )
    elif parts_missing > 0:
        health = (
            f"ℹ {parts_found} file(s) are resumable, but {parts_missing} "
            f".part file(s) are missing and will restart from scratch."
        )
    else:
        health = f"✔ All {parts_found} file(s) have resumable .part data."

    # Dialog window
    dlg = tk.Toplevel(self.root)
    dlg.title("Incomplete Download Detected")
    dlg.geometry("520x340")
    dlg.resizable(False, False)
    dlg.grab_set()          # modal
    dlg.focus_force()

    ttk.Label(
        dlg,
        text="An incomplete download session was found:",
        font=('Segoe UI', 11, 'bold'),
    ).pack(anchor=tk.W, padx=16, pady=(14, 4))

    info_frame = ttk.Frame(dlg)
    info_frame.pack(fill=tk.X, padx=16)

    ttk.Label(info_frame, text=file_list_text, justify=tk.LEFT).pack(
        anchor=tk.W, pady=(2, 6))
    ttk.Label(info_frame, text=f"Folder: {folder}", foreground='gray').pack(
        anchor=tk.W)
    ttk.Separator(dlg, orient='horizontal').pack(fill=tk.X, padx=16, pady=8)
    ttk.Label(dlg, text=health, justify=tk.LEFT, wraplength=480).pack(
        anchor=tk.W, padx=16, pady=(0, 8))

    btn_frame = ttk.Frame(dlg)
    btn_frame.pack(pady=(8, 14))

    def _continue():
        dlg.destroy()
        self._restore_session(session_data)

    def _discard():
        dlg.destroy()
        self._clear_session()
        self._set_status("Previous session discarded. Ready.")

    ttk.Button(
        btn_frame, text="▶  Continue Download", command=_continue,
    ).pack(side=tk.LEFT, padx=8)
    ttk.Button(
        btn_frame, text="✘  Discard Session", command=_discard,
    ).pack(side=tk.LEFT, padx=8)

    # Center the dialog over the main window
    dlg.update_idletasks()
    x = self.root.winfo_x() + (self.root.winfo_width()  - dlg.winfo_width())  // 2
    y = self.root.winfo_y() + (self.root.winfo_height() - dlg.winfo_height()) // 2
    dlg.geometry(f"+{x}+{y}")
