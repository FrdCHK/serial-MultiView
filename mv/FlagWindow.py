"""
flag window of GUI
@Author: Jingdong Zhang
@DATE  : 2024/8/6
"""
import tkinter as tk
from tkinter import font
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class FlagWindow:
    def __init__(self, root, antenna, config, target_relative_position, secondary_calibrators):
        self.antenna = antenna
        self.config = config
        self.target_relative_position = target_relative_position
        self.secondary_calibrators = secondary_calibrators

        self.window = tk.Toplevel(root)
        self.window.title("FLAG")
        self.window.geometry("1020x800+900+200")
        self.window.minsize(width=1020, height=800)

        self.window.grid_columnconfigure(0, weight=1)
        self.window.grid_rowconfigure(0, weight=5)
        self.window.grid_rowconfigure(1, weight=6)

        self.frames = []
        frame = tk.Frame(self.window)
        frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.frames.append(frame)
        frame = tk.Frame(self.window)
        frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.frames.append(frame)

        # top frame
        self.frames[0].grid_columnconfigure(0, weight=1)
        self.frames[0].grid_rowconfigure(0, weight=1)

        self.phase_plot()

    def phase_plot(self):
        fig = self.antenna.plot_phase(self.target_relative_position, self.secondary_calibrators)
        canvas = FigureCanvasTkAgg(fig, master=self.frames[0])
        canvas.draw()
        canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
