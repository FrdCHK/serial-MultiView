"""Small progress dialog for long MultiView calculations."""
import tkinter as tk
from tkinter import ttk


class ProgressWindow:
    """Modal Tk dialog driven by ``Antenna.delay_multiview`` progress callbacks.

    The solver runs in the GUI thread, so ``update`` explicitly flushes Tk idle
    work after changing the label/progressbar.  That keeps the window responsive
    during the roughly tens-of-seconds initial solve and rerun operations.
    """

    def __init__(self, parent, title="Calculating"):
        """Create a non-closable progress popup attached to ``parent``."""
        self.parent = parent
        self.window = tk.Toplevel(parent)
        self.window.title(title)
        self.window.geometry("360x120+180+220")
        self.window.resizable(False, False)
        self.window.transient(parent)
        self.window.protocol("WM_DELETE_WINDOW", lambda: None)

        self.window.grid_columnconfigure(0, weight=1)
        self.label = tk.Label(self.window, text="Starting...", anchor="w", padx=12)
        self.label.grid(row=0, column=0, sticky="ew", padx=8, pady=(14, 8))
        self.progress = ttk.Progressbar(self.window, mode="determinate", maximum=1.0)
        self.progress.grid(row=1, column=0, sticky="ew", padx=20, pady=8)

        self.window.grab_set()
        self.update("Starting...", 0, 1)

    def update(self, message, current=None, total=None):
        """Set the current step text and, when possible, determinate progress."""
        self.label.config(text=message)
        if total is not None and total > 0 and current is not None:
            self.progress.config(mode="determinate", maximum=float(total))
            self.progress["value"] = min(float(current), float(total))
        self.window.update_idletasks()
        self.window.update()

    def close(self):
        """Release the modal grab and destroy the popup."""
        try:
            self.window.grab_release()
        except tk.TclError:
            pass
        if self.window.winfo_exists():
            self.window.destroy()
        self.parent.update_idletasks()
