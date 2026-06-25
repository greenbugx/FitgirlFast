import subprocess
import shutil
import os
import re

class ExtractionManager:
    def __init__(self, event_bus):
        self.event_bus = event_bus
        
    def run_extraction(self, folder: str, downloads: dict, delete_after: bool) -> bool:
        exe_7z = None
        paths = [shutil.which('7z'), shutil.which('7za'), shutil.which('7z.exe'),
                 r"C:\Program Files\7-Zip\7z.exe", r"C:\Program Files (x86)\7-Zip\7z.exe"]
        for p in paths:
            if p and os.path.exists(p):
                exe_7z = p
                break
                
        if not exe_7z:
            self.event_bus.status_changed.emit("Extraction skipped: 7-Zip not found.")
            return False
            
        downloaded_files = []
        for dl in downloads.values():
            if dl.filename:
                fpath = os.path.join(folder, dl.filename)
                if os.path.exists(fpath):
                    downloaded_files.append(fpath)
                    
        if not downloaded_files: return False
        
        downloaded_files.sort()
        part_re = re.compile(r'\.part(\d+)\.rar$', re.IGNORECASE)
        standalone, first_parts = [], []
        has_other_parts = False
        
        for f in downloaded_files:
            lower_f = f.lower()
            if lower_f.endswith('.rar'):
                m = part_re.search(lower_f)
                if m:
                    if int(m.group(1)) == 1: first_parts.append(f)
                    else: has_other_parts = True
                else: standalone.append(f)
            elif lower_f.endswith('.001'): first_parts.append(f)
            elif re.search(r'\.\d{3}$', lower_f): has_other_parts = True
            elif lower_f.endswith('.zip') or lower_f.endswith('.7z'): standalone.append(f)
            
        if has_other_parts and not first_parts:
            self.event_bus.status_changed.emit("Extraction skipped: missing first part.")
            return False
            
        targets = first_parts + standalone
        if not targets: return False
        
        success = True
        for target in targets:
            basename = os.path.basename(target)
            self.event_bus.status_changed.emit(f"Extracting {basename}...")
            try:
                cmd = [exe_7z, 'x', '-y', f'-o{folder}', target]
                creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=creationflags)
                process.communicate()
                if process.returncode != 0:
                    success = False
            except Exception:
                success = False
                
        if success and delete_after:
            for f in downloaded_files:
                if re.search(r'\.(rar|r\d+|zip|z\d+|7z|0\d+)$', f.lower()):
                    try: os.remove(f)
                    except: pass
        return success
