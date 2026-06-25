def _fetch_paste(self):
    url = self.var_paste_url.get().strip()
    if not url:
        messagebox.showerror("Error", "Enter a paste URL first.")
        return
    self._set_status("Fetching & decrypting paste…")
    threading.Thread(target=self._fetch_paste_bg, args=(url,), daemon=True).start()

def _fetch_paste_bg(self, url):
    try:
        text = fetch_privatebin_paste(url)
        urls = re.findall(r'https://fuckingfast\.co/\S+', text)
        urls = [_clean_url(u) for u in urls if u]
        if not urls:
            self.root.after(0, lambda: messagebox.showwarning(
                "Warning", "Paste decrypted but no fuckingfast.co URLs found.\n"
                           "Check the paste URL or paste URLs manually."))
            self._set_status("No URLs found in paste.")
            return
        self.root.after(0, lambda: self._load_urls(urls))
        self.root.after(0, lambda: self.txt_urls.delete('1.0', tk.END))
        self.root.after(0, lambda: self.txt_urls.insert('1.0', '\n'.join(urls)))
        # record in history
        self._record_paste_history(url, len(urls))
    except ImportError:
        self.root.after(0, lambda: messagebox.showerror(
            "Missing library",
            "Install cryptography:\n  pip install cryptography\nThen retry."))
        self._set_status("cryptography library missing.")
    except Exception as e:
        self.root.after(0, lambda: messagebox.showerror("Fetch error", str(e)))
        self._set_status(f"Error: {e}")

def _load_from_text(self):
    raw  = self.txt_urls.get('1.0', tk.END)
    urls = re.findall(r'https://fuckingfast\.co/\S+', raw)
    urls = [_clean_url(u) for u in urls if u]
    if not urls:
        messagebox.showerror("Error", "No fuckingfast.co URLs found in the text box.")
        return
    self._load_urls(urls)

def _load_urls(self, urls: list[str]):
    self.urls        = urls
    self.file_vars   = []
    self.prog_bars   = {}
    self.stat_labels = {}
    self.cancel_btns = {}
    self.pause_btns  = {}

    for w in self.inner.winfo_children():
        w.destroy()

    hdr = ttk.Frame(self.inner); hdr.pack(fill=tk.X, pady=(0, 2))
    ttk.Label(hdr, text=" #",       width=4,  anchor=tk.W).pack(side=tk.LEFT)
    ttk.Label(hdr, text="Filename", width=42, anchor=tk.W).pack(side=tk.LEFT)
    ttk.Label(hdr, text="Progress", width=16, anchor=tk.CENTER).pack(side=tk.LEFT)
    ttk.Label(hdr, text="Status",   width=35, anchor=tk.W).pack(side=tk.LEFT)
    ttk.Separator(self.inner, orient='horizontal').pack(fill=tk.X)

    for i, url in enumerate(urls):
        fname = _sanitize_fname(url.split('#')[-1] if '#' in url else url.split('/')[-1])
        var   = tk.BooleanVar(value=True)
        self.file_vars.append(var)

        row = ttk.Frame(self.inner); row.pack(fill=tk.X, pady=1)
        ttk.Checkbutton(row, variable=var).pack(side=tk.LEFT)
        ttk.Label(row, text=f"{i + 1:03d}. {fname}", width=42, anchor=tk.W).pack(side=tk.LEFT)

        pb = ttk.Progressbar(row, length=150, mode='determinate', maximum=100)
        pb.pack(side=tk.LEFT, padx=4)
        self.prog_bars[url] = pb

        sl = ttk.Label(row, text="Waiting", width=35, anchor=tk.W)
        sl.pack(side=tk.LEFT)
        self.stat_labels[url] = sl

        cb = ttk.Button(row, text="✕", width=3,
                        command=lambda u=url: self._cancel_one(u))
        cb.pack(side=tk.RIGHT, padx=(2, 6))
        cb.config(state='disabled')
        self.cancel_btns[url] = cb

        ppb = ttk.Button(row, text="⏸", width=3,
                         command=lambda u=url: self._toggle_pause_one(u))
        ppb.pack(side=tk.RIGHT, padx=2)
        ppb.config(state='disabled')
        self.pause_btns[url] = ppb

    self.lbl_count.config(text=f"{len(urls)} files loaded")
    self._set_status(f"Loaded {len(urls)} files. Select files and click Start.")
