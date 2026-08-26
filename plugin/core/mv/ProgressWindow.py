"""Parallel-IF progress state and Tk dialog for MultiView calculations."""

import tkinter as tk
from tkinter import ttk


IF_STATES = {
    "queued",
    "preparing",
    "running",
    "complete",
    "skipped",
    "failed",
    "cancelled",
}
TERMINAL_IF_STATES = {"complete", "skipped", "failed", "cancelled"}
GLOBAL_STATES = {"preparing", "solving", "combining", "complete", "failed"}


class ProgressState:
    """Display-independent state reducer for structured solver events."""

    def __init__(self, if_ids):
        self.if_ids = [int(if_id) for if_id in if_ids]
        self.if_states = {if_id: "queued" for if_id in self.if_ids}
        self.global_state = "preparing"
        self.message = "Preparing IF observations"

    @property
    def total(self):
        return len(self.if_ids)

    @property
    def terminal_count(self):
        return sum(state in TERMINAL_IF_STATES for state in self.if_states.values())

    def apply_event(self, event):
        """Validate and apply one solver progress event."""

        event_type = event.get("type")
        if event_type == "if_state":
            if_id = int(event["if_id"])
            state = event["state"]
            if if_id not in self.if_states:
                raise ValueError(f"Unknown IF id in progress event: {if_id}")
            if state not in IF_STATES:
                raise ValueError(f"Unknown IF progress state: {state}")
            self.if_states[if_id] = state
        elif event_type == "global_state":
            state = event["state"]
            if state not in GLOBAL_STATES:
                raise ValueError(f"Unknown global progress state: {state}")
            self.global_state = state
            self.message = event.get("message") or state.capitalize()
        else:
            raise ValueError(f"Unknown progress event type: {event_type}")

    def summary(self):
        """Return the overall label text for the current state."""

        if self.global_state == "solving":
            return f"Solving IFs in parallel — {self.terminal_count}/{self.total} complete"
        if self.global_state == "complete":
            return f"Calculation complete — {self.terminal_count}/{self.total} complete"
        return self.message


class ProgressWindow:
    """Modal Tk dialog showing aggregate and per-IF parallel progress."""

    def __init__(self, parent, if_ids, title="Calculating"):
        """Create a non-cancellable popup attached to ``parent``."""

        self.parent = parent
        self.state = ProgressState(if_ids)
        self.window = tk.Toplevel(parent)
        self.window.title(title)
        visible_rows = min(max(self.state.total, 1), 8)
        self.window.geometry(f"460x{165 + visible_rows * 25}+180+220")
        self.window.minsize(width=420, height=240)
        self.window.resizable(True, True)
        self.window.transient(parent)
        self.window.protocol("WM_DELETE_WINDOW", lambda: None)

        self.window.grid_columnconfigure(0, weight=1)
        self.window.grid_rowconfigure(2, weight=1)
        self.label = tk.Label(self.window, text=self.state.summary(), anchor="w", padx=12)
        self.label.grid(row=0, column=0, sticky="ew", padx=8, pady=(14, 8))
        self.progress = ttk.Progressbar(
            self.window,
            mode="determinate",
            maximum=float(max(1, self.state.total)),
        )
        self.progress.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))

        table_frame = ttk.Frame(self.window)
        table_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 14))
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)
        self.table = ttk.Treeview(
            table_frame,
            columns=("if", "status"),
            show="headings",
            height=visible_rows,
            selectmode="none",
        )
        self.table.heading("if", text="IF")
        self.table.heading("status", text="Status")
        self.table.column("if", width=90, minwidth=70, stretch=False, anchor="center")
        self.table.column("status", width=280, minwidth=160, stretch=True, anchor="w")
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=scrollbar.set)
        self.table.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.table.tag_configure("complete", foreground="#177245")
        self.table.tag_configure("skipped", foreground="#777777")
        self.table.tag_configure("failed", foreground="#b00020")
        self.table.tag_configure("cancelled", foreground="#777777")
        for if_id in self.state.if_ids:
            self.table.insert(
                "",
                "end",
                iid=str(if_id),
                values=(f"IF{if_id + 1}", "Queued"),
                tags=("queued",),
            )

        self.window.grab_set()

    def handle_event(self, event):
        """Apply one event; this method must only run in the Tk thread."""

        self.state.apply_event(event)
        if event["type"] == "if_state":
            if_id = int(event["if_id"])
            state = event["state"]
            self.table.item(str(if_id), values=(f"IF{if_id + 1}", state.capitalize()), tags=(state,))
        self.label.config(text=self.state.summary())
        self.progress["maximum"] = float(max(1, self.state.total))
        if self.state.total == 0 and self.state.global_state == "complete":
            self.progress["value"] = 1.0
        else:
            self.progress["value"] = float(self.state.terminal_count)

    def close(self):
        """Release the modal grab and destroy the popup."""

        try:
            self.window.grab_release()
        except tk.TclError:
            pass
        if self.window.winfo_exists():
            self.window.destroy()
        self.parent.update_idletasks()
