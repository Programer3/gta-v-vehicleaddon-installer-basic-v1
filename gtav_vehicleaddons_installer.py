import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import shutil
import datetime
import subprocess
import winreg
import threading

class GTAModInstallerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("GTA V Add-On Car Installer Utility")
        self.root.geometry("900x750")
        self.root.resizable(True, True)

        # Variables
        self.gta_path_var = tk.StringVar()
        self.openiv_path_var = tk.StringVar()
        self.source_folder_var = tk.StringVar()
        self.output_folder_var = tk.StringVar()
        self.detected_folders = []
        self.extratitle_selection = {} # Dict to hold checkbutton vars

        # Styles
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Green.TLabel", foreground="green")
        style.configure("Red.TLabel", foreground="red")

        # --- GUI LAYOUT ---
        
        # 1. Path Selection Section
        path_frame = ttk.LabelFrame(root, text="System Paths", padding=10)
        path_frame.pack(fill="x", padx=10, pady=5)

        # GTA V Path
        ttk.Label(path_frame, text="GTA V Exe Location:").grid(row=0, column=0, sticky="w")
        ttk.Entry(path_frame, textvariable=self.gta_path_var, width=60).grid(row=0, column=1, padx=5)
        ttk.Button(path_frame, text="Browse", command=self.browse_gta).grid(row=0, column=2)
        self.gta_status = ttk.Label(path_frame, text="●", style="Red.TLabel", font=("Arial", 16))
        self.gta_status.grid(row=0, column=3, padx=5)

        # OpenIV Path
        ttk.Label(path_frame, text="OpenIV Location:").grid(row=1, column=0, sticky="w")
        ttk.Entry(path_frame, textvariable=self.openiv_path_var, width=60).grid(row=1, column=1, padx=5)
        ttk.Button(path_frame, text="Browse", command=self.browse_openiv).grid(row=1, column=2)
        self.openiv_status = ttk.Label(path_frame, text="●", style="Red.TLabel", font=("Arial", 16))
        self.openiv_status.grid(row=1, column=3, padx=5)

        # 2. Mod Source Section
        src_frame = ttk.LabelFrame(root, text="Mod Files Selection", padding=10)
        src_frame.pack(fill="x", padx=10, pady=5)

        # DLC Source Folder
        ttk.Label(src_frame, text="Folder with Car DLCs:").grid(row=0, column=0, sticky="w")
        ttk.Entry(src_frame, textvariable=self.source_folder_var, width=60).grid(row=0, column=1, padx=5)
        ttk.Button(src_frame, text="Select Folder", command=self.select_source_folder).grid(row=0, column=2)
        
        # ExtraTitle Listbox area
        ttk.Label(src_frame, text="Select folders requiring 'extratitleupdatedata.meta' (Optional):").grid(row=1, column=0, columnspan=3, sticky="w", pady=(10,0))
        
        self.check_frame = ttk.Frame(src_frame, borderwidth=1, relief="sunken")
        self.check_frame.grid(row=2, column=0, columnspan=3, sticky="nsew", pady=5)
        self.check_canvas = tk.Canvas(self.check_frame, height=100)
        self.scrollbar = ttk.Scrollbar(self.check_frame, orient="vertical", command=self.check_canvas.yview)
        self.scrollable_frame = ttk.Frame(self.check_canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.check_canvas.configure(scrollregion=self.check_canvas.bbox("all"))
        )
        self.check_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.check_canvas.configure(yscrollcommand=self.scrollbar.set)

        self.check_canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # 3. Output Section
        out_frame = ttk.LabelFrame(root, text="Output & Execution", padding=10)
        out_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(out_frame, text="Generated Files Output:").grid(row=0, column=0, sticky="w")
        ttk.Entry(out_frame, textvariable=self.output_folder_var, width=60).grid(row=0, column=1, padx=5)
        ttk.Button(out_frame, text="Select Output", command=self.select_output_folder).grid(row=0, column=2)

        self.execute_btn = ttk.Button(out_frame, text="EXECUTE INSTALLATION", command=self.start_execution, state="disabled")
        self.execute_btn.grid(row=1, column=0, columnspan=3, pady=10, sticky="ew")

        # 4. Log Area
        log_frame = ttk.LabelFrame(root, text="Live Log", padding=10)
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.log_area = scrolledtext.ScrolledText(log_frame, state='disabled', height=10, font=("Consolas", 9))
        self.log_area.pack(fill="both", expand=True)

        # --- INITIALIZATION ---
        self.log("Program Started.")
        self.auto_detect_paths()

    def log(self, message):
        """Thread-safe logging to GUI and internal buffer"""
        timestamp = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        full_msg = f"{timestamp} {message}"
        
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, full_msg + "\n")
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')
        return full_msg

    def update_indicators(self):
        """Updates the Red/Green dots based on file existence"""
        gta_ok = os.path.exists(self.gta_path_var.get()) and self.gta_path_var.get().endswith("GTA5.exe")
        openiv_ok = os.path.exists(self.openiv_path_var.get()) and "OpenIV" in self.openiv_path_var.get()

        if gta_ok:
            self.gta_status.config(style="Green.TLabel")
        else:
            self.gta_status.config(style="Red.TLabel")

        if openiv_ok:
            self.openiv_status.config(style="Green.TLabel")
        else:
            self.openiv_status.config(style="Red.TLabel")

        # Enable Execute only if paths are valid and source/output selected
        if gta_ok and openiv_ok and self.source_folder_var.get() and self.output_folder_var.get():
            self.execute_btn.config(state="normal")
        else:
            self.execute_btn.config(state="disabled")

    def auto_detect_paths(self):
        """Attempts to find GTA5 and OpenIV via Registry"""
        self.log("Attempting auto-detection of paths...")
        
        # Detect GTA V
        gta_found = None
        try:
            # Try Steam Registry
            hkey = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Rockstar Games\Grand Theft Auto V")
            val, _ = winreg.QueryValueEx(hkey, "InstallFolder")
            exe_path = os.path.join(val, "GTA5.exe")
            if os.path.exists(exe_path):
                gta_found = exe_path
        except Exception:
            pass

        if not gta_found:
            # Try common paths
            common_paths = [
                r"C:\Program Files\Epic Games\GTAV\GTA5.exe",
                r"C:\Program Files (x86)\Steam\steamapps\common\Grand Theft Auto V\GTA5.exe",
                r"D:\SteamLibrary\steamapps\common\Grand Theft Auto V\GTA5.exe"
            ]
            for p in common_paths:
                if os.path.exists(p):
                    gta_found = p
                    break
        
        if gta_found:
            self.gta_path_var.set(gta_found)
            self.log(f"GTA V detected: {gta_found}")
        else:
            self.log("GTA V not auto-detected. Please browse manually.")

        # Detect OpenIV
        openiv_found = None
        user_profile = os.environ.get('USERPROFILE')
        local_app_data = os.environ.get('LOCALAPPDATA')
        
        possible_openiv = [
            os.path.join(local_app_data, r"New Technology Studio\Apps\OpenIV\OpenIV.exe"),
            os.path.join(user_profile, r"AppData\Local\New Technology Studio\Apps\OpenIV\OpenIV.exe")
        ]

        for p in possible_openiv:
            if os.path.exists(p):
                openiv_found = p
                break
        
        if openiv_found:
            self.openiv_path_var.set(openiv_found)
            self.log(f"OpenIV detected: {openiv_found}")
        else:
            self.log("OpenIV not auto-detected. Please browse manually.")

        self.update_indicators()

    def browse_gta(self):
        path = filedialog.askopenfilename(filetypes=[("Executable", "GTA5.exe")])
        if path:
            self.gta_path_var.set(path)
            self.update_indicators()

    def browse_openiv(self):
        path = filedialog.askopenfilename(filetypes=[("Executable", "*.exe")])
        if path:
            self.openiv_path_var.set(path)
            self.update_indicators()

    def select_source_folder(self):
        folder = filedialog.askdirectory(title="Select Folder containing Car DLC folders")
        if folder:
            self.source_folder_var.set(folder)
            self.populate_extratitle_list(folder)
            self.update_indicators()

    def select_output_folder(self):
        folder = filedialog.askdirectory(title="Select Output Folder for Logs/XMLs")
        if folder:
            self.output_folder_var.set(folder)
            self.update_indicators()

    def populate_extratitle_list(self, folder_path):
        """Scans source folder for directories and populates the checkbox list"""
        # Clear existing
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.extratitle_selection = {}
        self.detected_folders = []

        try:
            items = os.listdir(folder_path)
            # Filter only directories
            dirs = [d for d in items if os.path.isdir(os.path.join(folder_path, d))]
            dirs.sort() # Alphabetic order
            
            self.detected_folders = dirs
            
            if not dirs:
                self.log("Warning: No subfolders found in selected source directory.")
                return

            for d in dirs:
                var = tk.IntVar()
                chk = ttk.Checkbutton(self.scrollable_frame, text=d, variable=var)
                chk.pack(anchor="w", padx=5)
                self.extratitle_selection[d] = var
                
            self.log(f"Scanned {len(dirs)} folders in source directory.")
            
        except Exception as e:
            self.log(f"Error scanning source folder: {e}")

    def start_execution(self):
        """Starts the main process in a separate thread to keep UI responsive"""
        if not messagebox.askyesno("Confirm", "Are you sure you want to proceed with the installation?"):
            return
        
        threading.Thread(target=self.run_process, daemon=True).start()

    def run_process(self):
        session_log = []
        
        def log_step(msg):
            log_entry = self.log(msg)
            session_log.append(log_entry)

        log_step("--- Execution Started ---")
        
        gta_root = os.path.dirname(self.gta_path_var.get())
        src_dir = self.source_folder_var.get()
        out_dir = self.output_folder_var.get()
        
        # 1. Check/Create Mods folder structure
        mods_dlc_path = os.path.join(gta_root, "mods", "update", "x64", "dlcpacks")
        
        try:
            if not os.path.exists(mods_dlc_path):
                log_step(f"Path not found: {mods_dlc_path}")
                log_step("Creating missing 'mods' directory structure...")
                os.makedirs(mods_dlc_path)
                log_step("Created directory structure successfully.")
            else:
                log_step("Mods directory structure already exists.")
        except Exception as e:
            log_step(f"CRITICAL ERROR creating directories: {e}")
            return

        # 2. Process Folders (Move and collect names)
        dlclist_entries = []
        extratitle_entries = []
        
        folders_to_move = self.detected_folders # These are names sorted alphabetically
        
        for folder_name in folders_to_move:
            src_path = os.path.join(src_dir, folder_name)
            dest_path = os.path.join(mods_dlc_path, folder_name)
            
            # Move Logic
            try:
                if os.path.exists(dest_path):
                    log_step(f"Skipping move: '{folder_name}' already exists in dlcpacks.")
                else:
                    log_step(f"Moving '{folder_name}' to dlcpacks...")
                    shutil.move(src_path, dest_path)
                    log_step(f"Moved '{folder_name}' successfully.")
            except Exception as e:
                log_step(f"Error moving {folder_name}: {e}")
                continue # Skip adding to XML if move failed
            
            # Prepare XML Entries
            # dlclist.xml entry
            dlclist_entries.append(f"\t<Item>dlcpacks:/{folder_name}/</Item>")
            
            # extratitleupdatedata.meta entry (if selected)
            if self.extratitle_selection[folder_name].get() == 1:
                entry = (
                    f"\t<Item type=\"CDataMount\">\n"
                    f"\t\t<Name>dlcpacks:/{folder_name}/</Name>\n"
                    f"\t\t<Parent>dlcpacks:/{folder_name}/</Parent>\n"
                    f"\t</Item>"
                )
                extratitle_entries.append(entry)

        # 3. Generate Output Files
        timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # dlclist file
        dlc_file_path = os.path.join(out_dir, "to_addto_dlclistxml.txt")
        try:
            with open(dlc_file_path, "w") as f:
                f.write("\n".join(dlclist_entries))
            log_step(f"Generated: {dlc_file_path}")
        except Exception as e:
            log_step(f"Error writing dlclist file: {e}")

        # extratitle file
        extra_file_path = os.path.join(out_dir, "toput_in_extratitleupdatedata_meta.txt")
        try:
            with open(extra_file_path, "w") as f:
                f.write("\n".join(extratitle_entries))
            log_step(f"Generated: {extra_file_path}")
        except Exception as e:
            log_step(f"Error writing extratitle file: {e}")

        # 4. Save Full Log File
        log_file_name = f"log_{timestamp_str}.log"
        log_file_path = os.path.join(out_dir, log_file_name)
        try:
            with open(log_file_path, "w") as f:
                f.write("\n".join(session_log))
            log_step(f"Saved session log to: {log_file_path}")
        except Exception as e:
            log_step(f"Error saving log file: {e}")

        # 5. OpenIV and Final Instructions
        log_step("Process Complete. Launching OpenIV...")
        
        # Launch OpenIV
        # Note: OpenIV does not support CLI flags to open specific internal RPF paths or toggle edit mode.
        # We launch it standardly.
        try:
            subprocess.Popen(self.openiv_path_var.get())
        except Exception as e:
            log_step(f"Could not launch OpenIV automatically: {e}")

        final_msg = (
            "--------------------------------------------------\n"
            "SUCCESS: Add-on cars moved.\n"
            "--------------------------------------------------\n"
            "INSTRUCTIONS:\n"
            "1. OpenIV is launching.\n"
            "2. Navigate to: mods > update > update.rpf > common > data\n"
            "3. Toggle 'Edit Mode'.\n"
            "4. Right-click 'dlclist.xml' -> Edit. Add contents of 'to_addto_dlclistxml.txt' before </Paths>.\n"
            "5. (If applicable) Right-click 'extratitleupdatedata.meta' -> Edit. Add contents of 'toput_in_extratitleupdatedata_meta.txt' before </Mounts>.\n"
            "--------------------------------------------------"
        )
        
        log_step(final_msg)
        
        # Show Done Dialog
        messagebox.showinfo("Done", "Operation Complete!\nCheck the log area for next steps.")

if __name__ == "__main__":
    root = tk.Tk()
    app = GTAModInstallerApp(root)
    root.mainloop()