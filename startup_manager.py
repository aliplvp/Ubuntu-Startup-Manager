#!/usr/bin/env python3
import os, re, shlex, shutil, subprocess, tkinter as tk
from tkinter import ttk, messagebox, filedialog
import webbrowser

APP_NAME = "Startup Manager"
AUTOSTART = os.path.expanduser("~/.config/autostart")
SYSTEM_DIRS = ["/etc/xdg/autostart"]
ICON = "/usr/share/icons/hicolor/scalable/apps/startup-manager.svg"

def parse_desktop(path):
    data = {}
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                data[k] = v
    except OSError:
        pass
    return data

def safe_name(name):
    name = re.sub(r"[^A-Za-z0-9_.-]+", "-", name.strip()).strip(".-")
    return name or "startup-app"

class StartupManager:
    def __init__(self, root):
        self.root = root
        root.title("Startup Manager")
        root.geometry("850x540")
        root.minsize(680, 420)
        self.rows = {}
        self.build_ui()
        self.refresh()

    def build_ui(self):
        style = ttk.Style()
        try: style.theme_use("clam")
        except tk.TclError: pass
        style.configure("Treeview", rowheight=30, font=("Ubuntu", 10))
        style.configure("Treeview.Heading", font=("Ubuntu", 10, "bold"))
        top = ttk.Frame(self.root, padding=(14, 12))
        top.pack(fill="x")
        ttk.Label(top, text="Startup Applications", font=("Ubuntu", 17, "bold")).pack(side="left")
        ttk.Button(
            top,
            text="Uninstall",
            command=self.uninstall_app
        ).pack(side="right", padx=(0, 8))

        ttk.Button(
            top,
            text="Refresh",
            command=self.refresh
        ).pack(side="right")

        info = ttk.Label(self.root, text="Manage apps that launch automatically when you sign in. System entries are shown too.",
                         padding=(14, 0, 14, 10))
        info.pack(anchor="w")

        frame = ttk.Frame(self.root, padding=(14, 0, 14, 8))
        frame.pack(fill="both", expand=True)
        cols = ("status", "name", "source", "command")
        self.tree = ttk.Treeview(frame, columns=cols, show="headings", selectmode="browse")
        self.tree.heading("status", text="Status")
        self.tree.heading("name", text="Application")
        self.tree.heading("source", text="Location")
        self.tree.heading("command", text="Command")
        self.tree.column("status", width=90, anchor="center")
        self.tree.column("name", width=190)
        self.tree.column("source", width=100, anchor="center")
        self.tree.column("command", width=390)
        scroll = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", lambda e: self.toggle_selected())

        buttons = ttk.Frame(self.root, padding=(14, 4, 14, 14))
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Add application", command=self.add_app).pack(side="left", padx=(0, 7))
        ttk.Button(buttons, text="Enable / Disable", command=self.toggle_selected).pack(side="left", padx=7)
        ttk.Button(buttons, text="Remove", command=self.remove_selected).pack(side="left", padx=7)
        ttk.Button(buttons, text="Open autostart folder", command=self.open_folder).pack(side="right")
        self.status = ttk.Label(self.root, text="", padding=(14, 0, 14, 8), foreground="#555")
        self.status.pack(anchor="w")
        
        github_link = tk.Label(
            root,
            text="Developed by AliPlvP | GitHub",
            fg="#0969DA",
            cursor="hand2"
        )
        github_link.pack(pady=5)

        github_link.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/aliplvp"))

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        self.rows.clear()
        os.makedirs(AUTOSTART, exist_ok=True)
        found = {}
        # User entries take precedence over system entries with the same filename.
        for directory in SYSTEM_DIRS:
            if os.path.isdir(directory):
                for fn in os.listdir(directory):
                    if fn.endswith(".desktop"):
                        found.setdefault(fn, (os.path.join(directory, fn), "System"))
        for fn in os.listdir(AUTOSTART):
            if fn.endswith(".desktop"):
                found[fn] = (os.path.join(AUTOSTART, fn), "User")
        for fn, (path, source) in sorted(found.items()):
            d = parse_desktop(path)
            if d.get("Type", "Application") != "Application":
                continue
            if d.get("NoDisplay", "false").lower() == "true" and source == "System":
                continue
            name = d.get("Name", fn[:-8])
            command = d.get("Exec", "")
            hidden = d.get("Hidden", "false").lower() == "true"
            disabled = d.get("X-GNOME-Autostart-enabled", "true").lower() == "false"
            enabled = not (hidden or disabled)
            # A user override with Hidden=true disables the system item.
            state = "Enabled" if enabled else "Disabled"
            iid = self.tree.insert("", "end", values=(state, name, source, command))
            self.rows[iid] = {"filename": fn, "path": path, "source": source, "enabled": enabled, "name": name}
        self.status.config(text=f"{len(self.rows)} startup entries found. Changes apply next time you sign in.")

    def selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo(APP_NAME, "Please select an application first.")
            return None
        return self.rows.get(sel[0])

    def toggle_selected(self):
        item = self.selected()
        if not item: return
        fn = item["filename"]
        os.makedirs(AUTOSTART, exist_ok=True)
        user_path = os.path.join(AUTOSTART, fn)
        if item["source"] == "User":
            d = parse_desktop(user_path)
            if item["enabled"]:
                d["Hidden"] = "true"
                d["X-GNOME-Autostart-enabled"] = "false"
            else:
                d["Hidden"] = "false"
                d["X-GNOME-Autostart-enabled"] = "true"
            self.write_desktop(user_path, d)
        else:
            # Per-user override: Hidden=true disables system autostart without root.
            if item["enabled"]:
                self.write_desktop(user_path, {"Type":"Application", "Name":item["name"],
                                               "Hidden":"true", "X-GNOME-Autostart-enabled":"false"})
            else:
                try: os.remove(user_path)
                except FileNotFoundError: pass
        self.refresh()

    def write_desktop(self, path, data):
        with open(path, "w", encoding="utf-8") as f:
            f.write("[Desktop Entry]\n")
            for k, v in data.items():
                f.write(f"{k}={v}\n")

    def add_app(self):
        win = tk.Toplevel(self.root)
        win.title("Add startup application")
        win.transient(self.root)
        win.grab_set()
        win.resizable(False, False)
        box = ttk.Frame(win, padding=16); box.pack(fill="both", expand=True)
        ttk.Label(box, text="Application name").grid(row=0, column=0, sticky="w", pady=5)
        name = tk.StringVar()
        ttk.Entry(box, textvariable=name, width=48).grid(row=0, column=1, pady=5)
        ttk.Label(box, text="Command").grid(row=1, column=0, sticky="w", pady=5)
        cmd = tk.StringVar()
        ttk.Entry(box, textvariable=cmd, width=48).grid(row=1, column=1, pady=5)
        ttk.Label(box, text="Example: /usr/bin/firefox").grid(row=2, column=1, sticky="w")
        def browse():
            p = filedialog.askopenfilename(title="Choose application", initialdir="/usr/bin")
            if p: cmd.set(shlex.quote(p))
        ttk.Button(box, text="Browse…", command=browse).grid(row=1, column=2, padx=(8,0))
        def save():
            n, c = name.get().strip(), cmd.get().strip()
            if not n or not c:
                messagebox.showwarning(APP_NAME, "Enter both an application name and command.", parent=win); return
            filename = safe_name(n) + ".desktop"
            path = os.path.join(AUTOSTART, filename)
            if os.path.exists(path):
                if not messagebox.askyesno(APP_NAME, "An entry with this name already exists. Replace it?", parent=win): return
            data = {"Type":"Application", "Name":n, "Exec":c, "Terminal":"false",
                    "X-GNOME-Autostart-enabled":"true"}
            self.write_desktop(path, data)
            win.destroy(); self.refresh()
        ttk.Button(box, text="Cancel", command=win.destroy).grid(row=3, column=1, sticky="e", pady=(14,0))
        ttk.Button(box, text="Add", command=save).grid(row=3, column=2, sticky="e", pady=(14,0))

    def remove_selected(self):
        item = self.selected()
        if not item: return
        if item["source"] == "User":
            question = f"Remove '{item['name']}' from your startup list?"
        else:
            question = (f"'{item['name']}' is a system startup entry. It cannot be deleted here.\n"
                        "You can disable it for your account using Enable / Disable.")
            messagebox.showinfo(APP_NAME, question); return
        if messagebox.askyesno(APP_NAME, question):
            try: os.remove(item["path"])
            except OSError as e:
                messagebox.showerror(APP_NAME, str(e)); return
            self.refresh()

    def open_folder(self):
        os.makedirs(AUTOSTART, exist_ok=True)
        subprocess.Popen(["xdg-open", AUTOSTART])
        
    def uninstall_app(self):

        confirm = messagebox.askyesno(
            "Uninstall Startup Manager",
            "Are you sure you want to completely uninstall Startup Manager?\n\n"
            "This will remove the application, icon and desktop shortcuts.\n"
            "Your other startup configurations will remain untouched."
        )

        if not confirm:
            return

        try:
            paths = [
                os.path.expanduser("~/.local/share/startup-manager"),
                os.path.expanduser("~/.local/bin/startup-manager"),
                os.path.expanduser("~/.local/share/icons/startup-manager.svg"),
                os.path.expanduser("~/.local/share/applications/startup-manager.desktop"),
                os.path.expanduser("~/Desktop/Startup Manager.desktop")
            ]

            for path in paths:
                if os.path.isdir(path) and not os.path.islink(path):
                    shutil.rmtree(path)
                elif os.path.exists(path):
                    os.remove(path)

            messagebox.showinfo(
                "Uninstall Successful",
                "Startup Manager has been successfully uninstalled."
            )

            self.root.destroy()

        except Exception as e:
            messagebox.showerror(
                "Uninstall Error",
                f"Failed to uninstall application:\n{e}"
            )


        

if __name__ == "__main__":
    root = tk.Tk()
    StartupManager(root)
    root.mainloop()
