# gui.py — FLOAT AI Desktop Assistant
# tkinter dashboard: status dot, animated waveform, conversation log,
text input fallback, quick-action buttons, system tray (pystray)

import math
import queue
import threading
import logging
import tkinter as tk
from tkinter import ttk, scrolledtext, font as tkfont

from config import FLOAT_VERSION, log

logger = logging.getLogger("FLOAT.gui")

# ─── Color Palette ────────────────────────────────────────────────────────────
C_BG        = "#0d0d14"     # deep dark
C_PANEL     = "#13131f"     # slightly lighter panels
C_BORDER    = "#1e1e32"
C_ACCENT    = "#6c63ff"     # purple
C_ACCENT2   = "#00d4aa"     # teal
C_TEXT      = "#e8e8f0"
C_SUBTEXT   = "#7070a0"
C_USER      = "#a0d4ff"     # light blue — user messages
C_FLOAT     = "#b8ffd4"     # mint green — FLOAT replies
C_STATUS = {
    "Sleeping...":   "#555580",
    "Listening...":  "#00d4aa",
    "Thinking...":   "#6c63ff",
}


class FloatGUI(tk.Tk):
    """Main FLOAT dashboard window."""

    def __init__(self, gui_queue: queue.Queue, on_text_command, on_mic_command=None):
        super().__init__()
        self._queue        = gui_queue
        self._on_text_cmd  = on_text_command   # callback: str → None
        self._on_mic_cmd   = on_mic_command    # callback: () → None
        self._status       = "Sleeping..."
        self._wave_phase   = 0.0
        self._wave_active  = False

        self._build_window()
        self._build_layout()
        self._poll_queue()
        self._animate_wave()

    # ─── Window setup ─────────────────────────────────────────────────────────
    def _build_window(self):
        self.title(f"FLOAT v{FLOAT_VERSION}")
        self.configure(bg=C_BG)
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.96)

        # Position bottom-right
        self.update_idletasks()
        W, H = 400, 640
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x  = sw - W - 20
        y  = sh - H - 60
        self.geometry(f"{W}x{H}+{x}+{y}")

        # Intercept close → minimise to tray instead
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ─── Layout ───────────────────────────────────────────────────────────────
    def _build_layout(self):
        # ── TOP: logo + status ────────────────────────────────────────────────
        top = tk.Frame(self, bg=C_BG, pady=12)
        top.pack(fill=tk.X)

        tk.Label(
            top, text="◈ FLOAT", font=("Courier New", 22, "bold"),
            fg=C_ACCENT, bg=C_BG
        ).pack(side=tk.LEFT, padx=18)

        self._status_dot  = tk.Canvas(top, width=14, height=14, bg=C_BG, highlightthickness=0)
        self._status_dot.pack(side=tk.RIGHT, padx=(0, 8))
        self._status_dot.create_oval(2, 2, 12, 12, fill=C_STATUS["Sleeping..."], tags="dot")

        self._status_lbl = tk.Label(
            top, text="Sleeping...", font=("Courier New", 10),
            fg=C_SUBTEXT, bg=C_BG
        )
        self._status_lbl.pack(side=tk.RIGHT, padx=4)

        # Thin separator
        tk.Frame(self, bg=C_BORDER, height=1).pack(fill=tk.X)

        # ── WAVEFORM ANIMATION ────────────────────────────────────────────────
        self._wave_canvas = tk.Canvas(
            self, bg=C_BG, height=50, highlightthickness=0
        )
        self._wave_canvas.pack(fill=tk.X, padx=16, pady=(8, 0))

        # ── BOTTOM: input + buttons ───────────────────────────────────────────
        # We pack this FIRST with side=BOTTOM so it doesn't get pushed off-screen
        tk.Frame(self, bg=C_BORDER, height=1).pack(side=tk.BOTTOM, fill=tk.X)
        bottom = tk.Frame(self, bg=C_BG, pady=10)
        bottom.pack(side=tk.BOTTOM, fill=tk.X, padx=12)

        # Text input
        input_row = tk.Frame(bottom, bg=C_BG)
        input_row.pack(fill=tk.X, pady=(0, 8))

        self._entry = tk.Entry(
            input_row,
            bg=C_PANEL, fg=C_TEXT,
            insertbackground=C_ACCENT,
            font=("Segoe UI", 11),
            relief=tk.FLAT, bd=0,
        )
        self._entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6, padx=(0, 6))
        self._entry.bind("<Return>", self._on_enter)

        mic_btn = tk.Button(
            input_row, text="🎙️",
            bg=C_ACCENT2, fg="white", activebackground="#00b38f",
            font=("Segoe UI", 12),
            relief=tk.FLAT, bd=0, cursor="hand2",
            command=self._on_mic_click,
        )
        mic_btn.pack(side=tk.LEFT, ipadx=8, ipady=4, padx=(0, 6))

        send_btn = tk.Button(
            input_row, text="↵",
            bg=C_ACCENT, fg="white", activebackground="#5a52e0",
            font=("Segoe UI", 12, "bold"),
            relief=tk.FLAT, bd=0, cursor="hand2",
            command=self._on_enter,
        )
        send_btn.pack(side=tk.LEFT, ipadx=10, ipady=4)

        # Quick action buttons
        quick = tk.Frame(bottom, bg=C_BG)
        quick.pack(fill=tk.X)

        actions = [
            ("📶 WiFi",      lambda: self._quick("wifi toggle")),
            ("🔊 Volume",    lambda: self._quick("volume up")),
            ("📷 Shot",      lambda: self._quick("screenshot")),
            ("🔒 Lock",      lambda: self._quick("lock screen")),
        ]
        for label, cmd in actions:
            btn = tk.Button(
                quick, text=label,
                bg=C_BORDER, fg=C_TEXT,
                activebackground=C_ACCENT,
                font=("Segoe UI", 9),
                relief=tk.FLAT, bd=0, cursor="hand2",
                command=cmd,
            )
            btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2, ipady=5)

        # ── MID: conversation log ─────────────────────────────────────────────
        # Now pack the log frame with expand=True so it fills the remaining space
        log_frame = tk.Frame(self, bg=C_PANEL, bd=0)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)

        self._log_text = scrolledtext.ScrolledText(
            log_frame,
            bg=C_PANEL, fg=C_TEXT,
            font=("Segoe UI", 10),
            wrap=tk.WORD,
            state=tk.DISABLED,
            bd=0, relief=tk.FLAT,
            padx=8, pady=8,
            insertbackground=C_ACCENT,
        )
        self._log_text.pack(fill=tk.BOTH, expand=True)

        # Tag colours
        self._log_text.tag_configure("user",  foreground=C_USER,  font=("Segoe UI", 10, "bold"))
        self._log_text.tag_configure("float", foreground=C_FLOAT, font=("Segoe UI", 10))
        self._log_text.tag_configure("sys",   foreground=C_SUBTEXT, font=("Segoe UI", 9, "italic"))

    # ─── Waveform Animation ───────────────────────────────────────────────────
    def _animate_wave(self):
        c = self._wave_canvas
        c.delete("wave")
        w = c.winfo_width() or 400
        h = 50
        num_bars  = 24
        bar_w     = max(4, (w - 20) // num_bars - 2)
        spacing   = (w - 20) // num_bars
        base_y    = h // 2

        for i in range(num_bars):
            if self._wave_active:
                amplitude = 18 * abs(math.sin(self._wave_phase + i * 0.4))
            else:
                amplitude = 3.0  # idle — tiny bumps

            x1 = 10 + i * spacing
            x2 = x1 + bar_w
            y1 = base_y - amplitude
            y2 = base_y + amplitude

            color = C_ACCENT if self._wave_active else C_BORDER
            c.create_rectangle(x1, y1, x2, y2, fill=color, outline="", tags="wave")

        self._wave_phase += 0.18
        self.after(45, self._animate_wave)

    # ─── Queue Polling ────────────────────────────────────────────────────────
    def _poll_queue(self):
        try:
            while True:
                item = self._queue.get_nowait()
                kind, data = item[0], item[1]

                if kind == "status":
                    self._update_status(data)
                elif kind == "user_msg":
                    self._append_log(f"You: {data}\n", "user")
                elif kind == "float_msg":
                    self._append_log(f"FLOAT: {data}\n\n", "float")
                elif kind == "sys_msg":
                    self._append_log(f"[{data}]\n", "sys")

        except queue.Empty:
            pass
        self.after(80, self._poll_queue)

    # ─── Status Update ────────────────────────────────────────────────────────
    def _update_status(self, status: str):
        self._status = status
        color = C_STATUS.get(status, C_SUBTEXT)
        self._status_dot.itemconfig("dot", fill=color)
        self._status_lbl.configure(text=status, fg=color)
        self._wave_active = (status == "Listening...")

    # ─── Conversation Log ─────────────────────────────────────────────────────
    def _append_log(self, text: str, tag: str):
        self._log_text.configure(state=tk.NORMAL)
        self._log_text.insert(tk.END, text, tag)
        self._log_text.see(tk.END)
        self._log_text.configure(state=tk.DISABLED)

        # Keep only last 40 lines
        lines = int(self._log_text.index("end-1c").split(".")[0])
        if lines > 40:
            self._log_text.configure(state=tk.NORMAL)
            self._log_text.delete("1.0", f"{lines-40}.0")
            self._log_text.configure(state=tk.DISABLED)

    # ─── Input Handlers ───────────────────────────────────────────────────────
    def _on_enter(self, event=None):
        text = self._entry.get().strip()
        if text:
            self._entry.delete(0, tk.END)
            self._on_text_cmd(text)

    def _on_mic_click(self):
        if self._on_mic_cmd:
            self._on_mic_cmd()

    def _quick(self, cmd: str):
        self._on_text_cmd(cmd)

    # ─── Close / Tray ─────────────────────────────────────────────────────────
    def _on_close(self):
        self.withdraw()   # Hide instead of destroying
        self._start_tray()

    def _start_tray(self):
        try:
            import pystray
            from PIL import Image, ImageDraw

            # Create a small icon
            img = Image.new("RGB", (64, 64), color=C_BG)
            draw = ImageDraw.Draw(img)
            draw.ellipse([8, 8, 56, 56], fill="#6c63ff")
            draw.text((20, 20), "F", fill="white")

            def _show(icon, item):
                icon.stop()
                self.after(0, self.deiconify)

            def _quit(icon, item):
                icon.stop()
                self.after(0, self.destroy)

            menu = pystray.Menu(
                pystray.MenuItem("Show FLOAT", _show),
                pystray.MenuItem("Quit", _quit),
            )
            icon = pystray.Icon("FLOAT", img, "FLOAT AI", menu)
            t = threading.Thread(target=icon.run, daemon=True)
            t.start()
        except Exception as e:
            logger.warning(f"System tray unavailable: {e}")
            self.deiconify()   # Just show again if tray fails
