import json
import tkinter as tk
import urllib.error
import urllib.request


BASE_URL = "http://127.0.0.1:8000"
POLL_MS = 350
ANIMATION_MS = 70


def checked(value):
    return str(value).lower() in {"1", "true", "yes", "on"}


class StarPowerButton:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("STAR Power")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#ffffff")
        self.root.resizable(False, False)

        self.frame = tk.Frame(self.root, bg="#0f1513", bd=1, relief="solid")
        self.frame.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(
            self.frame,
            width=92,
            height=56,
            bg="#0f1513",
            highlightthickness=0,
            bd=0,
        )
        self.canvas.grid(row=0, column=0, rowspan=2, padx=(10, 4), pady=8)

        self.label = tk.Label(
            self.frame,
            text="STAR",
            bg="#0f1513",
            fg="#d7fff4",
            font=("Segoe UI", 8, "bold"),
        )
        self.label.grid(row=0, column=1, sticky="w", padx=(4, 10), pady=(8, 0))

        self.state_label = tk.Label(
            self.frame,
            text="WAITING",
            bg="#0f1513",
            fg="#9b5d2e",
            font=("Segoe UI", 15, "bold"),
        )
        self.state_label.grid(row=1, column=1, sticky="w", padx=(4, 10), pady=(0, 8))

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
        self.button.grid(row=0, column=2, rowspan=2, padx=(0, 10), pady=10)

        self.quiet = None
        self.speaking = False
        self.phase = 0
        self.drag_start = None
        self.frame.bind("<ButtonPress-1>", self.start_drag)
        self.frame.bind("<B1-Motion>", self.drag)
        self.canvas.bind("<ButtonPress-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.drag)
        self.label.bind("<ButtonPress-1>", self.start_drag)
        self.label.bind("<B1-Motion>", self.drag)
        self.state_label.bind("<ButtonPress-1>", self.start_drag)
        self.state_label.bind("<B1-Motion>", self.drag)

        self.root.after(80, self.place_bottom_right)
        self.animate()
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
        self.speaking = False
        self.state_label.config(text="WAITING", fg="#9b5d2e")
        self.button.config(text="Server...", state="disabled", bg="#9b5d2e")

    def set_state(self, quiet, speaking=False):
        self.quiet = bool(quiet)
        self.speaking = bool(speaking) and not self.quiet
        if self.quiet:
            self.state_label.config(text="OFF", fg="#b42318")
            self.button.config(text="Turn On", state="normal", bg="#b42318", activebackground="#8f1c13")
        elif self.speaking:
            self.state_label.config(text="SPEAKING", fg="#56f0c6")
            self.button.config(text="Turn Off", state="normal", bg="#16745f", activebackground="#125f4f")
        else:
            self.state_label.config(text="ON", fg="#16745f")
            self.button.config(text="Turn Off", state="normal", bg="#16745f", activebackground="#125f4f")

    def draw_idle_orb(self, color="#16745f"):
        self.canvas.delete("all")
        self.canvas.create_oval(30, 12, 62, 44, fill=color, outline="")
        self.canvas.create_oval(38, 20, 54, 36, fill="#0f1513", outline="")
        self.canvas.create_oval(42, 24, 50, 32, fill="#d7fff4", outline="")

    def draw_speaking_wave(self):
        self.canvas.delete("all")
        colors = ["#56f0c6", "#7bdcff", "#f5d36b", "#ff7aa8", "#9df7df"]
        heights = [14, 24, 34, 44, 30, 20, 36]
        for index, base_height in enumerate(heights):
            wobble = ((self.phase + index * 3) % 10) / 10
            height = int(base_height * (0.55 + wobble))
            x = 15 + index * 10
            y0 = 28 - height // 2
            y1 = 28 + height // 2
            self.canvas.create_rectangle(x, y0, x + 5, y1, fill=colors[index % len(colors)], outline="")
        self.canvas.create_oval(28, 8, 64, 46, outline="#56f0c6", width=2)

    def animate(self):
        self.phase = (self.phase + 1) % 1000
        if self.speaking:
            self.draw_speaking_wave()
        elif self.quiet:
            self.draw_idle_orb("#b42318")
        elif self.quiet is None:
            self.draw_idle_orb("#9b5d2e")
        else:
            self.draw_idle_orb("#16745f")
        self.root.after(ANIMATION_MS, self.animate)

    def refresh(self):
        try:
            status = self.request_json("/voice/status")
            settings = status.get("settings", {})
            quiet = checked(settings.get("voice_quiet", "false"))
            self.set_state(quiet, speaking=checked(status.get("is_speaking", False)))
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
