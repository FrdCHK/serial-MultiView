"""
flag window of GUI
@Author: Jingdong Zhang
@DATE  : 2024/8/6
"""
# import yaml
import tkinter as tk
from tkinter import font
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class AdjustWindow:
    def __init__(self, root, antenna, config, target_relative_position, secondary_calibrators):
        self.root = root
        self.antenna = antenna
        self.config = config
        self.target_relative_position = target_relative_position
        self.secondary_calibrators = secondary_calibrators

        self.window = tk.Toplevel(root.root)
        self.window.title("ADJUST")
        self.window.geometry("1320x890+600+60")
        self.window.minsize(width=1320, height=890)

        self.window.grid_columnconfigure(0, weight=1)
        self.window.grid_rowconfigure(0, weight=2)
        self.window.grid_rowconfigure(1, weight=1)

        self.font = font.Font(family="Consolas", size=16)

        self.frames = []
        frame = tk.Frame(self.window)
        frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.frames.append(frame)
        frame = tk.Frame(self.window)
        frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.frames.append(frame)

        # upper frame
        self.frames[0].grid_columnconfigure(0, weight=1)
        self.frames[0].grid_rowconfigure(0, weight=1)

        self.present_phase_fig = None
        self.present_phase_canvas = None
        self.green_line = None
        self.red_line = None
        self.timerange_start = None
        self.timerange_end = None
        self.fill = None
        self.phase_plot()

        # lower frame
        self.frames[1].grid_rowconfigure(0, weight=1)
        self.frames[1].grid_columnconfigure(0, weight=12)
        self.frames[1].grid_columnconfigure(1, weight=10)
        self.frames[1].grid_columnconfigure(2, weight=10)

        self.lower_frames = []
        frame = tk.Frame(self.frames[1])
        frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.lower_frames.append(frame)
        frame = tk.Frame(self.frames[1])
        frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.lower_frames.append(frame)
        frame = tk.Frame(self.frames[1])
        frame.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)
        self.lower_frames.append(frame)

        # manual adjustment toggle
        self.manual_toggle = tk.BooleanVar(value=False)
        manual_toggle = tk.Checkbutton(self.lower_frames[1], text="manual adjustment", font=self.font,
                                       variable=self.manual_toggle, command=self.on_manual_toggle)
        manual_toggle.pack(padx=5, pady=5)

        # reverse toggle
        self.reverse_toggle = tk.BooleanVar(value=False)
        reverse_toggle = tk.Checkbutton(self.lower_frames[1], text="reverse", font=self.font,
                                       variable=self.reverse_toggle, command=self.on_reverse_toggle)
        reverse_toggle.pack(padx=5, pady=5)

        # calibrator select
        label_info = tk.Label(self.lower_frames[1], text="-- secondary calibrator selection --",
                              width=36, font=self.font, anchor="center")
        label_info.pack(padx=5, pady=5)
        self.calibrator_toggle_var = [tk.BooleanVar(value=False) for _ in range(len(self.secondary_calibrators))]
        self.calibrator_adjust = []
        for i, item in enumerate(self.secondary_calibrators):
            calibrator_toggle = tk.Checkbutton(self.lower_frames[1], text=item.name, font=self.font,
                                               variable=self.calibrator_toggle_var[i],
                                               command=lambda j=i: self.on_calibrator_toggle(j))
            calibrator_toggle.pack(padx=5, pady=5)

        # position plot
        self.lower_frames[0].grid_columnconfigure(0, weight=1)
        self.lower_frames[0].grid_rowconfigure(0, weight=1)
        self.present_position_fig = None
        self.position_plot()

        # button frame
        self.lower_frames[2].grid_columnconfigure(0, weight=1)
        self.lower_frames[2].grid_columnconfigure(1, weight=1)
        self.lower_frames[2].grid_rowconfigure(0, weight=1)
        self.lower_frames[2].grid_rowconfigure(1, weight=1)
        self.lower_frames[2].grid_rowconfigure(2, weight=1)

        plus_button = tk.Button(self.lower_frames[2], height=2, width=10, text="+2\u03C0", font=self.font,
                                command=lambda: self.on_wrap('+'))
        plus_button.grid(row=0, column=0, padx=5, pady=5)
        minus_button = tk.Button(self.lower_frames[2], height=2, width=10, text="-2\u03C0", font=self.font,
                                command=lambda: self.on_wrap('-'))
        minus_button.grid(row=0, column=1, padx=5, pady=5)
        flag_button = tk.Button(self.lower_frames[2], height=2, width=10, text="flag", font=self.font,
                                command=lambda: self.on_flag('flag'))
        flag_button.grid(row=1, column=0, padx=5, pady=5)
        unflag_button = tk.Button(self.lower_frames[2], height=2, width=10, text="unflag", font=self.font,
                                command=lambda: self.on_flag('unflag'))
        unflag_button.grid(row=1, column=1, padx=5, pady=5)
        reset_button = tk.Button(self.lower_frames[2], height=2, width=10, text="reset", font=self.font,
                                 command=self.on_reset)
        reset_button.grid(row=2, column=0, padx=5, pady=5)

    def on_manual_toggle(self):
        if self.manual_toggle.get():
            self.phase_plot_for_adjust()
        else:
            self.phase_plot()

    def on_reverse_toggle(self):
        self.antenna.reverse = self.reverse_toggle.get()

    def on_calibrator_toggle(self, num):
        """
        :param num: index of the calibrator to be toggled. Note: this is not its AIPS source ID!
        """
        if self.calibrator_toggle_var[num].get():
            if self.secondary_calibrators[num].id not in self.calibrator_adjust:
                self.calibrator_adjust.append(self.secondary_calibrators[num].id)
        else:
            if self.secondary_calibrators[num].id in self.calibrator_adjust:
                self.calibrator_adjust.remove(self.secondary_calibrators[num].id)

    def on_click(self, event):
        """
        left click to mark start time, right click to mark end time.
        :param event: the click event
        """
        if event.inaxes is not None:
            x = event.xdata

            if event.button == 1:
                if self.red_line and x >= self.red_line.get_xdata()[0]:
                    return
                if self.green_line:
                    self.green_line.remove()
                x_lim = self.present_phase_fig.axes[0].get_xlim()
                self.present_phase_fig.axes[0].set_xlim(x_lim)
                self.green_line = self.present_phase_fig.axes[0].axvline(x=x, color='g', linestyle='-')
                self.timerange_start = x
            elif event.button == 3:
                if self.green_line and x <= self.green_line.get_xdata()[0]:
                    return
                if self.red_line:
                    self.red_line.remove()
                x_lim = self.present_phase_fig.axes[0].get_xlim()
                self.present_phase_fig.axes[0].set_xlim(x_lim)
                self.red_line = self.present_phase_fig.axes[0].axvline(x=x, color='r', linestyle='-')
                self.timerange_end = x

            # fill the area between two lines
            if self.green_line and self.red_line:
                if self.fill:
                    self.fill.remove()
                y_lim = self.present_phase_fig.axes[0].get_ylim()
                self.fill = self.present_phase_fig.axes[0].fill_betweenx(y_lim, self.timerange_start,
                                                                         self.timerange_end, color='gray', alpha=0.15)
                self.present_phase_fig.axes[0].set_ylim(y_lim)

            self.present_phase_canvas.draw()

    def on_wrap(self, mode):
        """
        See Antenna.wrap()
        :param mode: + / -
        """
        if self.manual_toggle.get() and (self.timerange_start is not None) and (self.timerange_end is not None):
            self.antenna.wrap([self.timerange_start, self.timerange_end], self.calibrator_adjust, mode)
            self.phase_plot_for_adjust()

    def on_flag(self, mode):
        """
        See Antenna.flag()
        :param mode: flag / unflag
        """
        if self.manual_toggle.get() and (self.timerange_start is not None) and (self.timerange_end is not None):
            self.antenna.flag([self.timerange_start, self.timerange_end], self.calibrator_adjust, mode)
            self.phase_plot_for_adjust()

    def on_reset(self):
        if self.manual_toggle.get():
            self.antenna.reset(self.root)

    def phase_plot(self):
        # close present fig
        if self.green_line is not None:
            self.green_line.remove()
            self.green_line = None
        if self.red_line is not None:
            self.red_line.remove()
            self.red_line = None
        self.timerange_start = None
        self.timerange_end = None
        if self.present_phase_fig is not None:
            plt.close(self.present_phase_fig)

        fig = self.antenna.plot_phase(self.target_relative_position)
        canvas = FigureCanvasTkAgg(fig, master=self.frames[0])
        canvas.draw()
        canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        self.present_phase_fig = fig

    def phase_plot_for_adjust(self):
        # close present fig
        if self.green_line is not None:
            self.green_line.remove()
            self.green_line = None
        if self.red_line is not None:
            self.red_line.remove()
            self.red_line = None
        self.timerange_start = None
        self.timerange_end = None
        if self.present_phase_fig is not None:
            plt.close(self.present_phase_fig)

        fig = self.antenna.plot_phase(self.target_relative_position, False)
        canvas = FigureCanvasTkAgg(fig, master=self.frames[0])
        canvas.draw()
        canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        canvas.mpl_connect("button_press_event", self.on_click)

        self.present_phase_fig = fig
        self.present_phase_canvas = canvas

    def position_plot(self):
        # close present fig
        if self.present_position_fig is not None:
            plt.close(self.present_position_fig)

        fig, ax = plt.subplots(1, 1, figsize=(1.5, 1.5))
        fig.subplots_adjust(left=0.08, right=0.98, top=0.98, bottom=0.08)
        ax.scatter([0], [0], label="Primary", marker='*', c='k')
        ax.scatter([self.target_relative_position[0]], [self.target_relative_position[1]],
                   label="Target", marker='x', c='k')
        for i, item in enumerate(self.secondary_calibrators):
            # if not self.calibrator_toggle_var[i].get():
            #     ax.scatter([item.dx], [item.dy], alpha=0.3)
            # else:
            #     ax.scatter([item.dx], [item.dy])
            ax.scatter([item.dx], [item.dy])
        ax.set_aspect('equal')
        canvas = FigureCanvasTkAgg(fig, master=self.lower_frames[0])
        canvas.draw()
        canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        self.present_position_fig = fig

    def save(self, adj_dir, mv_dir):
        self.antenna.save(adj_dir, mv_dir)
