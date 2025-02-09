import os
import shutil
import datetime
import tkinter as tk
from tkinter import ttk, messagebox
import configparser
import webbrowser  # For opening the GitHub URL
import sys

# -------------------------------------------------
# Helper: Resource Path
# -------------------------------------------------
def resource_path(relative_path):
    """
    Get absolute path to resource, works for development and for PyInstaller.
    """
    try:
        base_path = sys._MEIPASS  # PyInstaller creates a temp folder and stores path in _MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# -------------------------------------------------
# Global Settings and Paths
# -------------------------------------------------
USERPROFILE = os.environ.get("USERPROFILE", "")
GAME_SAVE_DIR = os.path.join(USERPROFILE, "AppData", "LocalLow", "noio", "KingdomTwoCrowns", "Release")

BACKUP_ROOT = os.path.join(os.getcwd(), "backups")
EXCLUDED_FILES = ["steam_autocloud.vdf"]

DEFAULT_BACKUP_INTERVAL = 300       # in seconds
DEFAULT_MAX_BACKUP_SIZE_MB = 100      # in MB
max_backup_size_bytes = DEFAULT_MAX_BACKUP_SIZE_MB * 1024 * 1024

# -------------------------------------------------
# Helper Function: Parse a backup file name.
# Expected format: {backup_number}-{original_filename}-{YYYY-MM-DD-HH-MM-SS}
# Example: "2-global-v35-2025-02-08-14-29-30"
# Returns: (backup_number (int), original_filename (str), dt (datetime))
# -------------------------------------------------
def parse_backup_filename(filename):
    parts = filename.split('-')
    if len(parts) < 8:
        return None
    try:
        backup_number = int(parts[0])
    except ValueError:
        return None
    ts_parts = parts[-6:]
    timestamp_str = '-'.join(ts_parts)
    try:
        dt = datetime.datetime.strptime(timestamp_str, "%Y-%m-%d-%H-%M-%S")
    except Exception:
        return None
    original_filename = '-'.join(parts[1:-6])
    return backup_number, original_filename, dt

# -------------------------------------------------
# Helper Function: Custom Choice Dialog
# -------------------------------------------------
def custom_choice_dialog(parent, title, message, options):
    dialog = tk.Toplevel(parent)
    dialog.title(title)
    dialog.transient(parent)
    dialog.grab_set()
    # Center the dialog relative to the parent window.
    parent.update_idletasks()
    parent_x = parent.winfo_x()
    parent_y = parent.winfo_y()
    parent_w = parent.winfo_width()
    parent_h = parent.winfo_height()
    dialog.geometry(f"+{parent_x + parent_w//2}+{parent_y + parent_h//2}")
    tk.Label(dialog, text=message).pack(padx=20, pady=10)
    result = [None]
    def on_choice(choice):
        result[0] = choice
        dialog.destroy()
    button_frame = tk.Frame(dialog)
    button_frame.pack(pady=10)
    for text, value in options:
        btn = tk.Button(button_frame, text=text, width=15,
                        command=lambda val=value: on_choice(val))
        btn.pack(side="left", padx=5)
    dialog.wait_window()
    return result[0]

# -------------------------------------------------
# Main Application Class
# -------------------------------------------------
class BackupApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Kingdom: Two Crowns Backuper v0.1")
        self.geometry("950x600")
        
        # Load icon from bundled resource.
        try:
            self.icon_img = tk.PhotoImage(file=resource_path("icon.png"))
            self.iconphoto(True, self.icon_img)
        except Exception as e:
            print("Could not load icon.png:", e)
        
        # Initialize configuration.
        self.config_file = os.path.join(os.getcwd(), "backup_config.ini")
        self.app_config = configparser.ConfigParser()
        self.load_config()
        
        # Setup configuration variables.
        self.backup_interval_var = tk.StringVar(value=self.app_config.get("Settings", "backup_interval", fallback=str(DEFAULT_BACKUP_INTERVAL)))
        self.time_unit_var = tk.StringVar(value=self.app_config.get("Settings", "time_unit", fallback="seconds"))
        self.max_backup_size_var = tk.StringVar(value=self.app_config.get("Settings", "max_backup_size", fallback=str(DEFAULT_MAX_BACKUP_SIZE_MB)))
        self.start_on_launch_var = tk.BooleanVar(value=self.app_config.getboolean("Settings", "start_on_launch", fallback=False))
        self.time_unit_var.trace("w", lambda *args: self.save_config())
        self.backup_interval_var.trace("w", lambda *args: self.save_config())
        self.max_backup_size_var.trace("w", lambda *args: self.save_config())
        
        self.backup_items = {}
        
        # ----------------------------
        # Top Frame: Settings and Logo
        # ----------------------------
        top_frame = tk.Frame(self)
        top_frame.pack(pady=10, padx=10, fill='x')
        
        settings_frame = tk.Frame(top_frame)
        settings_frame.grid(row=0, column=0, sticky='nw')
        
        tk.Label(settings_frame, text="Backup Interval:").grid(row=0, column=0, sticky='w')
        self.interval_entry = tk.Entry(settings_frame, width=10, textvariable=self.backup_interval_var)
        self.interval_entry.grid(row=0, column=1, sticky='w', padx=5)
        
        rb_seconds = tk.Radiobutton(settings_frame, text="Seconds", variable=self.time_unit_var, value="seconds")
        rb_minutes = tk.Radiobutton(settings_frame, text="Minutes", variable=self.time_unit_var, value="minutes")
        rb_seconds.grid(row=0, column=2, padx=5)
        rb_minutes.grid(row=0, column=3, padx=5)
        
        tk.Label(settings_frame, text="Max Backup Size (MB):").grid(row=1, column=0, sticky='w')
        self.max_size_entry = tk.Entry(settings_frame, width=10, textvariable=self.max_backup_size_var)
        self.max_size_entry.grid(row=1, column=1, sticky='w', padx=5)
        
        self.start_on_launch_cb = tk.Checkbutton(settings_frame,
                                                 text="Start backup on program start",
                                                 variable=self.start_on_launch_var,
                                                 command=self.on_start_on_launch_change)
        self.start_on_launch_cb.grid(row=2, column=0, columnspan=2, sticky='w', pady=5)
        
        logo_frame = tk.Frame(top_frame)
        logo_frame.grid(row=0, column=1, sticky='ne', padx=20)
        try:
            self.logo_img = tk.PhotoImage(file=resource_path("logo.png"))
        except Exception as e:
            print("Could not load logo.png:", e)
            self.logo_img = None
        if self.logo_img:
            self.logo_label = tk.Label(logo_frame, image=self.logo_img)
            self.logo_label.pack()
        
        # ----------------------------
        # Control Buttons
        # ----------------------------
        control_frame = tk.Frame(self)
        control_frame.pack(pady=5, padx=10, fill='x')
        self.start_button = tk.Button(control_frame, text="Start Backup", command=self.start_backup)
        self.start_button.pack(side='left', padx=5)
        self.stop_button = tk.Button(control_frame, text="Stop Backup", command=self.stop_backup, state='disabled')
        self.stop_button.pack(side='left', padx=5)
        self.delete_button = tk.Button(control_frame, text="Delete Selected Backup", command=self.delete_selected)
        self.delete_button.pack(side='left', padx=5)
        self.about_button = tk.Button(control_frame, text="About", command=self.about)
        self.about_button.pack(side='left', padx=5)
        
        # ----------------------------
        # Status Label
        # ----------------------------
        self.status_label = tk.Label(self, text="Status: Idle", fg="blue")
        self.status_label.pack(pady=5)
        
        # ----------------------------
        # Treeview for Backup List
        # ----------------------------
        tree_frame = tk.Frame(self)
        tree_frame.pack(pady=10, padx=10, fill='both', expand=True)
        self.tree = ttk.Treeview(tree_frame)
        self.tree.heading("#0", text="Backup Days and Files", anchor='w')
        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side='right', fill='y')
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # ----------------------------
        # Restore Button
        # ----------------------------
        action_frame = tk.Frame(self)
        action_frame.pack(pady=5)
        self.restore_button = tk.Button(action_frame, text="Restore Selected Backup", command=self.restore_selected)
        self.restore_button.pack(side='left', padx=5)
        
        self.backup_job = None
        
        self.refresh_backup_list()
        if self.start_on_launch_var.get():
            self.start_backup()
    
    # -------------------------------------------------
    # Configuration Loading and Saving
    # -------------------------------------------------
    def load_config(self):
        if os.path.exists(self.config_file):
            self.app_config.read(self.config_file)
        else:
            self.app_config["Settings"] = {
                "backup_interval": str(DEFAULT_BACKUP_INTERVAL),
                "time_unit": "seconds",
                "max_backup_size": str(DEFAULT_MAX_BACKUP_SIZE_MB),
                "start_on_launch": "False"
            }
            with open(self.config_file, "w") as f:
                self.app_config.write(f)
    
    def save_config(self):
        if "Settings" not in self.app_config:
            self.app_config["Settings"] = {}
        self.app_config["Settings"]["backup_interval"] = self.backup_interval_var.get()
        self.app_config["Settings"]["time_unit"] = self.time_unit_var.get()
        self.app_config["Settings"]["max_backup_size"] = self.max_backup_size_var.get()
        self.app_config["Settings"]["start_on_launch"] = str(self.start_on_launch_var.get())
        with open(self.config_file, "w") as f:
            self.app_config.write(f)
    
    def on_start_on_launch_change(self):
        self.save_config()
    
    # -------------------------------------------------
    # About Dialog (with Clickable GitHub URL)
    # -------------------------------------------------
    def about(self):
        about_window = tk.Toplevel(self)
        about_window.title("About")
        about_window.geometry("400x200")
        about_window.resizable(False, False)
        x = self.winfo_x() + (self.winfo_width() // 2) - 200
        y = self.winfo_y() + (self.winfo_height() // 2) - 100
        about_window.geometry(f"+{x}+{y}")
        
        about_text = (
            "Kingdom: Two Crowns Backuper v0.1\n"
            "Coded by Tatoline\n\n"
            "This is an open source and unofficial program that is not connected with Raw Fury."
        )
        label_info = tk.Label(about_window, text=about_text, justify="left", wraplength=400)
        label_info.pack(padx=10, pady=10)
        
        url = "https://github.com/tatoline/kingdom-two-crowns-backuper"
        label_url = tk.Label(about_window, text=url, fg="blue", cursor="hand2")
        label_url.pack(pady=5)
        label_url.bind("<Button-1>", lambda e: webbrowser.open_new(url))
        
        ok_button = tk.Button(about_window, text="OK", command=about_window.destroy)
        ok_button.pack(pady=10)
    
    # -------------------------------------------------
    # Backup Scheduling and Execution
    # -------------------------------------------------
    def start_backup(self):
        try:
            interval_val = int(self.backup_interval_var.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid backup interval", parent=self)
            return
        if self.time_unit_var.get() == "minutes":
            interval_val *= 60
        try:
            max_size_mb = int(self.max_backup_size_var.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid max backup size", parent=self)
            return
        global max_backup_size_bytes
        max_backup_size_bytes = max_size_mb * 1024 * 1024
        
        self.save_config()
        
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.status_label.config(text="Status: Backup in progress", fg="green")
        self.schedule_backup(interval_val * 1000)
    
    def stop_backup(self):
        if self.backup_job is not None:
            self.after_cancel(self.backup_job)
            self.backup_job = None
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.status_label.config(text="Status: Idle", fg="blue")
    
    def schedule_backup(self, delay):
        self.perform_backup()
        self.backup_job = self.after(delay, lambda: self.schedule_backup(delay))
    
    def perform_backup(self):
        if not os.path.exists(GAME_SAVE_DIR):
            print("Game save directory does not exist!")
            return
        for file in os.listdir(GAME_SAVE_DIR):
            if file in EXCLUDED_FILES:
                continue
            src = os.path.join(GAME_SAVE_DIR, file)
            if os.path.isfile(src):
                today_str = datetime.date.today().isoformat()
                dest_dir = os.path.join(BACKUP_ROOT, today_str)
                if not os.path.exists(dest_dir):
                    os.makedirs(dest_dir)
                max_num = 0
                for existing in os.listdir(dest_dir):
                    parsed = parse_backup_filename(existing)
                    if parsed:
                        num, _, _ = parsed
                        if num > max_num:
                            max_num = num
                backup_number = max_num + 1
                now_str = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
                new_filename = f"{backup_number}-{file}-{now_str}"
                dest = os.path.join(dest_dir, new_filename)
                try:
                    shutil.copy2(src, dest)
                    print(f"Backed up {src} to {dest}")
                except Exception as e:
                    print(f"Error backing up {src}: {e}")
        self.enforce_backup_size_limit()
        self.refresh_backup_list()
    
    def enforce_backup_size_limit(self):
        total_size = 0
        backup_files = []
        for root, dirs, files in os.walk(BACKUP_ROOT):
            for f in files:
                full_path = os.path.join(root, f)
                try:
                    size = os.path.getsize(full_path)
                except Exception:
                    size = 0
                total_size += size
                parsed = parse_backup_filename(f)
                if parsed:
                    _, _, dt = parsed
                else:
                    dt = datetime.datetime.fromtimestamp(os.path.getmtime(full_path))
                backup_files.append((full_path, dt, size))
        backup_files.sort(key=lambda x: x[1])
        global max_backup_size_bytes
        while total_size > max_backup_size_bytes and backup_files:
            file_to_delete, dt, size = backup_files.pop(0)
            try:
                os.remove(file_to_delete)
                print(f"Deleted old backup: {file_to_delete}")
                total_size -= size
            except Exception as e:
                print(f"Error deleting backup file {file_to_delete}: {e}")
        # Cleanup empty directories (except BACKUP_ROOT itself)
        for dirpath, dirnames, filenames in os.walk(BACKUP_ROOT, topdown=False):
            if dirpath != BACKUP_ROOT and not os.listdir(dirpath):
                os.rmdir(dirpath)
    
    # -------------------------------------------------
    # UI Refresh, Delete, and Restore Methods
    # -------------------------------------------------
    def refresh_backup_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.backup_items.clear()
        if not os.path.exists(BACKUP_ROOT):
            return
        days = os.listdir(BACKUP_ROOT)
        days.sort(reverse=True)
        for day in days:
            day_path = os.path.join(BACKUP_ROOT, day)
            if os.path.isdir(day_path):
                files = []
                for f in os.listdir(day_path):
                    full_path = os.path.join(day_path, f)
                    if os.path.isfile(full_path):
                        parsed = parse_backup_filename(f)
                        if parsed:
                            backup_number, _, dt = parsed
                            files.append((f, backup_number, dt))
                files.sort(key=lambda x: x[1])
                total_size = sum(os.path.getsize(os.path.join(day_path, f[0])) for f in files)
                total_size_mb = total_size / (1024 * 1024)
                parent_text = f"{day} - {len(files)} backup(s) - {total_size_mb:.2f} MB"
                parent_id = self.tree.insert("", "end", text=parent_text, open=False)
                for f, backup_number, dt in files:
                    display_text = f"{backup_number}) {dt.strftime('%Y.%m.%d %A - %H:%M:%S')}"
                    item_id = self.tree.insert(parent_id, "end", text=display_text)
                    self.backup_items[item_id] = os.path.join(day_path, f)
    
    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("Error", "No backup selected", parent=self)
            return
        parent = self.tree.parent(selected[0])
        if parent == "":
            day_text_full = self.tree.item(selected[0], "text")
            day_str = day_text_full.split(" - ")[0]
            try:
                dt = datetime.datetime.strptime(day_str, "%Y-%m-%d")
                display_day = dt.strftime("%Y.%m.%d %A")
            except Exception:
                display_day = day_str
            confirm = custom_choice_dialog(self, "Delete Confirmation",
                                           f"Are you sure to delete {display_day}?",
                                           [("Delete", True), ("Cancel", False)])
            if confirm:
                day_folder = os.path.join(BACKUP_ROOT, day_str)
                try:
                    shutil.rmtree(day_folder)
                    print(f"Deleted backup folder: {day_folder}")
                except Exception as e:
                    messagebox.showerror("Error", f"Error deleting backup folder: {e}", parent=self)
        else:
            child_text = self.tree.item(selected[0], "text")
            confirm = custom_choice_dialog(self, "Delete Confirmation",
                                           f"Are you sure to delete {child_text}?",
                                           [("Delete", True), ("Cancel", False)])
            if confirm:
                file_path = self.backup_items.get(selected[0])
                if file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        print(f"Deleted backup file: {file_path}")
                    except Exception as e:
                        messagebox.showerror("Error", f"Error deleting backup file: {e}", parent=self)
                else:
                    messagebox.showerror("Error", "Selected backup file not found.", parent=self)
        self.refresh_backup_list()
    
    def restore_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("Error", "No backup selected", parent=self)
            return
        parent = self.tree.parent(selected[0])
        if parent == "":
            children = self.tree.get_children(selected[0])
            if not children:
                messagebox.showerror("Error", "No backups available for this day", parent=self)
                return
            backups = []
            for child in children:
                full_path = self.backup_items.get(child)
                if not full_path:
                    continue
                base = os.path.basename(full_path)
                parsed = parse_backup_filename(base)
                if parsed:
                    backup_number, _, dt = parsed
                    backups.append((child, backup_number, dt))
            if not backups:
                messagebox.showerror("Error", "No valid backups found", parent=self)
                return
            backups.sort(key=lambda x: x[2])
            latest_id, latest_num, latest_dt = backups[-1]
            previous_id = None
            if len(backups) >= 2:
                previous_id, prev_num, prev_dt = backups[-2]
            message = f"Select backup to restore:\nLatest: {latest_dt.strftime('%Y.%m.%d %A - %H:%M:%S')}\n"
            if previous_id is not None:
                message += f"Previous: {prev_dt.strftime('%Y.%m.%d %A - %H:%M:%S')}\n"
            options = [("Latest", "latest")]
            if previous_id is not None:
                options.append(("Previous", "previous"))
            options.append(("Cancel", "cancel"))
            choice = custom_choice_dialog(self, "Restore", message, options)
            if choice == "latest":
                full_path = self.backup_items.get(latest_id)
                self.restore_backup(full_path)
            elif choice == "previous" and previous_id is not None:
                full_path = self.backup_items.get(previous_id)
                self.restore_backup(full_path)
            else:
                return
        else:
            item_id = selected[0]
            full_path = self.backup_items.get(item_id)
            if not full_path:
                messagebox.showerror("Error", "Invalid backup selection", parent=self)
                return
            base = os.path.basename(full_path)
            parsed = parse_backup_filename(base)
            if not parsed:
                messagebox.showerror("Error", "Invalid backup file format", parent=self)
                return
            backup_number, _, dt = parsed
            display_text = f"{backup_number}) {dt.strftime('%Y.%m.%d %A - %H:%M:%S')}"
            choice = custom_choice_dialog(self, "Restore Confirmation",
                                          f"Are you sure you want to restore\n{display_text} save file?",
                                          [("Yes", True), ("Cancel", False)])
            if choice:
                self.restore_backup(full_path)
            else:
                return
    
    def restore_backup(self, backup_file_path):
        basename = os.path.basename(backup_file_path)
        parsed = parse_backup_filename(basename)
        if not parsed:
            messagebox.showerror("Error", "Invalid backup file format", parent=self)
            return
        _, original_file_name, _ = parsed
        dest = os.path.join(GAME_SAVE_DIR, original_file_name)
        try:
            shutil.copy2(backup_file_path, dest)
            messagebox.showinfo("Restore", f"Backup restored to:\n{dest}", parent=self)
        except Exception as e:
            messagebox.showerror("Error", f"Error restoring backup: {e}", parent=self)

# -------------------------------------------------
# Main Entry Point
# -------------------------------------------------
def main():
    app = BackupApp()
    app.mainloop()

if __name__ == "__main__":
    main()
