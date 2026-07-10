"""
config window of GUI
@Author: Jingdong Zhang
@DATE  : 2024/8/6
"""
import copy
import tkinter as tk
from tkinter import font

from .solver_config import SOLVER_KEYS, apply_solver_defaults


PARAM_HELP = {
    "kalman_factor": "Continuous process-noise scale for second/degree gradients and their rates.",
    "rts_smoothing": "Run the backward RTS smoother after the forward Kalman pass.",
    "integer_states": "Integer ambiguity search radius n. Default 3 searches [-3, ..., 3].",
    "max_jump": "Maximum ambiguity change between adjacent observations of the same calibrator. Default 1.",
    "jump_penalty": "Cost for an ambiguity jump. Default 25 strongly discourages isolated false slips.",
    "huber_c": "Huber threshold in standardized-residual units. Default 3 is moderately robust.",
    "z_out": "Outlier rejection threshold in standardized-residual units. Default 4 after robust fitting.",
}


class ConfigWindow:
    def __init__(self, root, antenna, config, default_config=None):
        self.root = root
        self.antenna = antenna
        self.config = config
        apply_solver_defaults(self.config)
        if default_config is None:
            self.config_bk = copy.deepcopy(config)
        else:
            self.config_bk = copy.deepcopy(default_config)
            apply_solver_defaults(self.config_bk)

        self.window = tk.Toplevel(root.root)
        self.window.title("CONFIG")
        self.window.geometry("532x320+67+660")
        self.window.minsize(width=532, height=320)

        self.window.grid_columnconfigure(0, weight=1)
        self.window.grid_columnconfigure(1, weight=1)
        self.window.grid_columnconfigure(2, weight=1)

        self.font = font.Font(family="Consolas", size=16)

        self.labels = SOLVER_KEYS
        self.entries = []
        self.error_labels = []
        self.tip_window = None

        for i, text in enumerate(self.labels):
            label = tk.Label(self.window, text=text+':', width=18, anchor="e", font=self.font,
                             cursor="question_arrow")
            label.grid(row=i, column=0, padx=5, pady=5)
            label.bind("<Enter>", lambda event, key=text: self._show_tip(key, event))
            label.bind("<Leave>", self._hide_tip)

            if text == "rts_smoothing":
                entry = tk.BooleanVar(value=bool(self.config[self.labels[i]]))
                checkbox = tk.Checkbutton(self.window, variable=entry, font=self.font)
                checkbox.grid(row=i, column=1, padx=5, pady=5, sticky="w")
                checkbox.bind("<Enter>", lambda event, key=text: self._show_tip(key, event))
                checkbox.bind("<Leave>", self._hide_tip)
            else:
                entry = tk.Entry(self.window, font=self.font)
                entry.insert(0, self._entry_text(text, self.config[self.labels[i]]))
                entry.grid(row=i, column=1, padx=5, pady=5)
                entry.bind("<Enter>", lambda event, key=text: self._show_tip(key, event))
                entry.bind("<Leave>", self._hide_tip)
            self.entries.append(entry)

            error_label = tk.Label(self.window, text="", width=20, anchor="w", fg="red", font=self.font)
            error_label.grid(row=i, column=2, padx=5, pady=5)
            self.error_labels.append(error_label)

        save_button = tk.Button(self.window, text="save", height=1, width=15, font=self.font,
                                command=lambda r=root.root: self.validate_save(r))
        save_button.grid(row=len(self.labels), column=1, padx=5, pady=5)

        self.save_label = tk.Label(self.window, text="", width=20, anchor="w", font=self.font)
        self.save_label.grid(row=len(self.labels), column=2, padx=5, pady=5)

        reset_button = tk.Button(self.window, text="reset", height=1, width=15, font=self.font,
                                 command=self.reset)
        reset_button.grid(row=len(self.labels), column=0, padx=5, pady=5)

    def validate_save(self, root):
        # clear labels
        for label in self.error_labels:
            label.config(text="")
        self.save_label.config(text="")

        valid = True
        out_entries = []
        for i, item in enumerate(self.entries):
            label = self.labels[i]
            try:
                if label == "rts_smoothing":
                    entry = bool(item.get())
                else:
                    entry = self._parse_entry(label, item.get())
                out_entries.append(entry)
            except (ValueError, SyntaxError):
                self.error_labels[i].config(text="invalid input")
                valid = False

        if valid:
            for i, entry in enumerate(out_entries):
                self.config[self.labels[i]] = entry
            self.save_label.config(text="saved")
            root.after(1500, lambda lb=self.save_label: hide_text(lb))  # wait 1.5s then clear label

    @staticmethod
    def _parse_bool(text):
        if isinstance(text, bool):
            return text
        lowered = str(text).strip().lower()
        if lowered in ("1", "true", "yes", "y", "on"):
            return True
        if lowered in ("0", "false", "no", "n", "off"):
            return False
        raise ValueError("invalid bool")

    @staticmethod
    def _parse_optional(text, dtype=float):
        lowered = str(text).strip().lower()
        if lowered in ("", "none", "null"):
            return None
        value = dtype(text)
        if dtype is float and value <= 0.0:
            raise ValueError("invalid positive float")
        return value

    def _parse_entry(self, label, text):
        if label == "rts_smoothing":
            return self._parse_bool(text)
        if label == "integer_states":
            radius = int(text)
            if radius < 0:
                raise ValueError("invalid radius")
            return radius
        if label == "max_jump":
            value = int(text)
            if value < 0:
                raise ValueError("invalid int")
            return value
        value = float(text)
        if value <= 0.0 and label not in ("jump_penalty",):
            raise ValueError("invalid positive float")
        if label == "jump_penalty" and value < 0.0:
            raise ValueError("invalid penalty")
        return value

    @staticmethod
    def _entry_text(label, value):
        if value is None:
            return ""
        if label == "integer_states" and not isinstance(value, (str, int, float)):
            values = [abs(int(item)) for item in value]
            return str(max(values) if values else 0)
        return str(value)

    def reset(self):
        for i, text in enumerate(self.labels):
            self.config[self.labels[i]] = copy.deepcopy(self.config_bk[self.labels[i]])
            if text == "rts_smoothing":
                self.entries[i].set(bool(self.config[self.labels[i]]))
            else:
                self.entries[i].delete(0, tk.END)
                self.entries[i].insert(0, self._entry_text(text, self.config[self.labels[i]]))

    def _show_tip(self, key, event=None):
        self._hide_tip()
        text = PARAM_HELP.get(key)
        if not text:
            return
        self.tip_window = tk.Toplevel(self.window)
        self.tip_window.overrideredirect(True)
        self.tip_window.attributes("-topmost", True)
        label = tk.Label(
            self.tip_window,
            text=text,
            bg="#222222",
            fg="white",
            justify="left",
            relief="solid",
            borderwidth=1,
            padx=8,
            pady=6,
            wraplength=360,
            font=("Consolas", 10),
        )
        label.pack()
        x = event.x_root + 16 if event is not None else self.window.winfo_rootx() + 16
        y = event.y_root + 12 if event is not None else self.window.winfo_rooty() + 16
        self.tip_window.geometry(f"+{x}+{y}")

    def _hide_tip(self, _event=None):
        if self.tip_window is not None:
            self.tip_window.destroy()
            self.tip_window = None


def hide_text(label):
    label.config(text="")
