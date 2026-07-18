import json
import tkinter as tk
import urllib.error
import urllib.request


BASE_URL = "http://127.0.0.1:8000"
POLL_MS = 2000


class StarPowerButton:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("STAR Power")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#ffffff")
        self.root.resizable(False, False)

        self.frame = tk.Frame(self.root, bg="#ffffff", bd=1, relief="solid")
        self.frame.pack(fill="both", expand=True)

        self.label = tk.Label(
            self.frame,
            text="STAR",
            bg="#ffffff",
            fg="#63706b",
            font=("Segoe UI", 8, "bold"),
        )
        self.label.grid(row=0, column=0, sticky="w", padx=10, pady=(8, 0))

        self.state_label = tk.Label(
            self.frame,
            text="WAITING",
            bg="#ffffff",
            fg="#9b5d2e",
            font=("Segoe UI", 15, "bold"),
        )
        self.state_label.grid(row=1, column=0, sticky="w", padx=10, pady=(0, 8))

        self.button = tk.Button(
            self.frame,
            text="Checking",
            command=self.toggle,
            bg="#16745f",
            fg="#ffffff",
            activebackground="#125f4f",
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=14,
            pady=7,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
        )
        self.button.grid(row=0, column=1, rowspan=2, padx=(2, 10), pady=10)

        self.quiet = None
        self.drag_start = None
        self.frame.bind("<ButtonPress-1>", self.start_drag)
        self.frame.bind("<B1-Motion>", self.drag)
        self.label.bind("<ButtonPress-1>", self.start_drag)
        self.label.bind("<B1-Motion>", self.drag)
        self.state_label.bind("<ButtonPress-1>", self.start_drag)
        self.state_label.bind("<B1-Motion>", self.drag)

        self.root.after(80, self.place_bottom_right)
        self.refresh()

    def request_json(self, path, method="GET"):
        data = b"" if method == "POST" else None
        request = urllib.request.Request(f"{BASE_URL}{path}", data=data, method=method)
        with urllib.request.urlopen(request, timeout=3) as response:
            return json.loads(response.read().decode("utf-8"))

    def place_bottom_right(self):
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = max(12, screen_width - width - 18)
        y = max(12, screen_height - height - 72)
        self.root.geometry(f"+{x}+{y}")

    def start_drag(self, event):
        self.drag_start = (event.x_root - self.root.winfo_x(), event.y_root - self.root.winfo_y())

    def drag(self, event):
        if not self.drag_start:
            return
        x = event.x_root - self.drag_start[0]
        y = event.y_root - self.drag_start[1]
        self.root.geometry(f"+{x}+{y}")

    def set_waiting(self):
        self.quiet = None
        self.state_label.config(text="WAITING", fg="#9b5d2e")
        self.button.config(text="Server...", state="disabled", bg="#9b5d2e")

    def set_state(self, quiet):
        self.quiet = bool(quiet)
        if self.quiet:
            self.state_label.config(text="OFF", fg="#b42318")
            self.button.config(text="Turn On", state="normal", bg="#b42318", activebackground="#8f1c13")
        else:
            self.state_label.config(text="ON", fg="#16745f")
            self.button.config(text="Turn Off", state="normal", bg="#16745f", activebackground="#125f4f")

    def refresh(self):
        try:
            status = self.request_json("/voice/status")
            settings = status.get("settings", {})
            quiet = str(settings.get("voice_quiet", "false")).lower() in {"1", "true", "yes", "on"}
            self.set_state(quiet)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
            self.set_waiting()
        self.root.after(POLL_MS, self.refresh)

    def toggle(self):
        if self.quiet is None:
            return
        endpoint = "/voice/resume" if self.quiet else "/voice/quiet"
        try:
            self.request_json(endpoint, method="POST")
            self.set_state(not self.quiet)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
            self.set_waiting()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    StarPowerButton().run()
