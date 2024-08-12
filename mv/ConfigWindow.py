"""
config window of GUI
@Author: Jingdong Zhang
@DATE  : 2024/8/6
"""
import copy
import tkinter as tk
from tkinter import font


class ConfigWindow:
    def __init__(self, root, antenna, config):
        self.root = root
        self.antenna = antenna
        self.config = config
        self.config_bk = copy.deepcopy(config)

        self.window = tk.Toplevel(root.root)
        self.window.title("CONFIG")
        self.window.geometry("600x250+0+660")
        self.window.minsize(width=600, height=250)

        self.window.grid_columnconfigure(0, weight=1)
        self.window.grid_columnconfigure(1, weight=1)
        self.window.grid_columnconfigure(2, weight=1)

        self.font = font.Font(family="Consolas", size=16)

        self.labels = ["max_depth", "max_ang_v", "min_z", "kalman_factor", "smo_half_window"]
        self.entries = []
        self.error_labels = []

        for i, text in enumerate(self.labels):
            label = tk.Label(self.window, text=text+':', width=20, anchor="e", font=self.font)
            label.grid(row=i, column=0, padx=5, pady=5)

            entry = tk.Entry(self.window, font=self.font)
            entry.insert(0, self.config[self.labels[i]])
            entry.grid(row=i, column=1, padx=5, pady=5)
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
        types = [int, float, float, float, int]
        ranges = [[1, 10], [0., 10000.], [0., 1.], [0., 10.], [1, 20]]
        out_entries = []
        for i, item in enumerate(self.entries):
            try:
                entry = types[i](item.get())
                if ranges[i][0] <= entry <= ranges[i][1]:
                    out_entries.append(entry)
                else:
                    self.error_labels[i].config(text="invalid input")
                    valid = False
            except ValueError:
                self.error_labels[i].config(text="invalid input")
                valid = False

        if valid:
            for i, entry in enumerate(out_entries):
                self.config[self.labels[i]] = entry
            self.save_label.config(text="saved")
            root.after(1500, lambda lb=self.save_label: hide_text(lb))  # wait 1.5s then clear label

    def reset(self):
        for i, text in enumerate(self.labels):
            self.config[self.labels[i]] = self.config_bk[self.labels[i]]
            self.entries[i].delete(0, tk.END)
            self.entries[i].insert(0, self.config[self.labels[i]])


def hide_text(label):
    label.config(text="")
