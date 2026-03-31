"""
flag window of GUI
@Author: Jingdong Zhang
@DATE  : 2024/8/6
"""
import tkinter as tk
from tkinter import font
import matplotlib.pyplot as plt
import numpy as np
from astropy.wcs import WCS
from matplotlib import rc
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class AdjustWindow:
    def __init__(self, root, antenna, config, target, primary, target_relative_position, secondary_calibrators):
        self.root = root
        self.antenna = antenna
        self.config = config
        self.target = target
        self.primary = primary
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

        self.frames[0].grid_columnconfigure(0, weight=1)
        self.frames[0].grid_rowconfigure(0, weight=1)

        self.present_phase_fig = None
        self.present_phase_canvas = None
        self.green_line = None
        self.red_line = None
        self.timerange_start = None
        self.timerange_end = None
        self.fill = None

        self.frames[1].grid_rowconfigure(0, weight=1)
        self.frames[1].grid_columnconfigure(0, weight=12)
        self.frames[1].grid_columnconfigure(1, weight=10)
        self.frames[1].grid_columnconfigure(2, weight=10)

        self.lower_frames = []
        for col in range(3):
            frame = tk.Frame(self.frames[1])
            frame.grid(row=0, column=col, sticky="nsew", padx=5, pady=5)
            self.lower_frames.append(frame)

        self.manual_toggle = tk.BooleanVar(value=False)
        manual_toggle = tk.Checkbutton(self.lower_frames[1], text="manual adjustment", font=self.font,
                                       variable=self.manual_toggle, command=self.on_manual_toggle)
        manual_toggle.pack(padx=5, pady=5)

        self.reverse_toggle = tk.BooleanVar(value=bool(self.antenna.reverse))
        reverse_toggle = tk.Checkbutton(self.lower_frames[1], text="reverse", font=self.font,
                                        variable=self.reverse_toggle, command=self.on_reverse_toggle)
        reverse_toggle.pack(padx=5, pady=5)

        label_if = tk.Label(self.lower_frames[1], text="-- IF selection --", width=36, font=self.font, anchor="center")
        label_if.pack(padx=5, pady=5)
        self.if_options = [f"IF{if_id + 1}" for if_id in self.antenna.delay_if_ids] or ["IF1"]
        self.if_map = {label: if_id for label, if_id in zip(self.if_options, self.antenna.delay_if_ids)}
        if not self.if_map:
            self.if_map = {"IF1": 0}
        self.if_var = tk.StringVar(value=self.if_options[0])
        if_menu = tk.OptionMenu(self.lower_frames[1], self.if_var, *self.if_options, command=lambda _: self.on_if_change())
        if_menu.config(font=self.font)
        if_menu.pack(padx=5, pady=5)

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

        self.lower_frames[0].grid_columnconfigure(0, weight=1)
        self.lower_frames[0].grid_rowconfigure(0, weight=1)
        self.present_position_fig = None
        self.position_plot()

        self.lower_frames[2].grid_columnconfigure(0, weight=1)
        self.lower_frames[2].grid_columnconfigure(1, weight=1)
        for row in range(4):
            self.lower_frames[2].grid_rowconfigure(row, weight=1)

        plus_button = tk.Button(self.lower_frames[2], height=2, width=10, text="+2pi", font=self.font,
                                command=lambda: self.on_wrap('+'))
        plus_button.grid(row=0, column=0, padx=5, pady=5)
        minus_button = tk.Button(self.lower_frames[2], height=2, width=10, text="-2pi", font=self.font,
                                 command=lambda: self.on_wrap('-'))
        minus_button.grid(row=0, column=1, padx=5, pady=5)
        flag_button = tk.Button(self.lower_frames[2], height=2, width=10, text="flag", font=self.font,
                                command=lambda: self.on_flag('flag'))
        flag_button.grid(row=1, column=0, padx=5, pady=5)
        unflag_button = tk.Button(self.lower_frames[2], height=2, width=10, text="unflag", font=self.font,
                                  command=lambda: self.on_flag('unflag'))
        unflag_button.grid(row=1, column=1, padx=5, pady=5)
        t_flag_button = tk.Button(self.lower_frames[2], height=2, width=10, text="T flag", font=self.font,
                                  command=lambda: self.on_t_flag('flag'))
        t_flag_button.grid(row=2, column=0, padx=5, pady=5)
        t_unflag_button = tk.Button(self.lower_frames[2], height=2, width=10, text="T unflag", font=self.font,
                                    command=lambda: self.on_t_flag('unflag'))
        t_unflag_button.grid(row=2, column=1, padx=5, pady=5)
        reset_button = tk.Button(self.lower_frames[2], height=2, width=10, text="reset", font=self.font,
                                 command=self.on_reset)
        reset_button.grid(row=3, column=0, columnspan=2, padx=5, pady=5)

        self.phase_plot()

    def get_selected_if_id(self):
        return self.if_map.get(self.if_var.get(), self.antenna.delay_if_ids[0] if self.antenna.delay_if_ids else 0)

    def on_manual_toggle(self):
        if self.manual_toggle.get():
            self.phase_plot_for_adjust()
        else:
            self.phase_plot()

    def on_reverse_toggle(self):
        self.antenna.reverse = self.reverse_toggle.get()

    def on_if_change(self):
        if self.manual_toggle.get():
            self.phase_plot_for_adjust()
        else:
            self.phase_plot()
        self.root.root_normal_vector_plot()

    def on_calibrator_toggle(self, num):
        if self.calibrator_toggle_var[num].get():
            if self.secondary_calibrators[num].id not in self.calibrator_adjust:
                self.calibrator_adjust.append(self.secondary_calibrators[num].id)
        else:
            if self.secondary_calibrators[num].id in self.calibrator_adjust:
                self.calibrator_adjust.remove(self.secondary_calibrators[num].id)

    def on_click(self, event):
        if event.inaxes is not None:
            x = float(event.xdata)
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

            if self.green_line and self.red_line:
                if self.fill:
                    self.fill.remove()
                y_lim = self.present_phase_fig.axes[0].get_ylim()
                self.fill = self.present_phase_fig.axes[0].fill_betweenx(y_lim, self.timerange_start,
                                                                         self.timerange_end, color='gray', alpha=0.15)
                self.present_phase_fig.axes[0].set_ylim(y_lim)
            self.present_phase_canvas.draw()

    def on_wrap(self, mode):
        if self.manual_toggle.get() and (self.timerange_start is not None) and (self.timerange_end is not None):
            self.antenna.delay_wrap([self.timerange_start, self.timerange_end], self.calibrator_adjust, self.get_selected_if_id(), mode)
            self.phase_plot_for_adjust()
            self.root.rerun(False)

    def on_flag(self, mode):
        if self.manual_toggle.get() and (self.timerange_start is not None) and (self.timerange_end is not None):
            self.antenna.delay_flag([self.timerange_start, self.timerange_end], self.calibrator_adjust, mode)
            self.phase_plot_for_adjust()
            self.root.rerun(False)

    def on_t_flag(self, mode):
        if self.manual_toggle.get() and (self.timerange_start is not None) and (self.timerange_end is not None):
            self.antenna.delay_t_flag([self.timerange_start, self.timerange_end], mode)
            self.phase_plot_for_adjust()

    def on_reset(self):
        if self.manual_toggle.get():
            self.antenna.delay_reset()
            self.root.rerun()

    def phase_plot(self):
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

        fig = self.antenna.plot_delay(self.target_relative_position, self.get_selected_if_id(), adjusted=False)
        canvas = FigureCanvasTkAgg(fig, master=self.frames[0])
        canvas.draw()
        canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.present_phase_fig = fig
        self.present_phase_canvas = canvas

    def phase_plot_for_adjust(self):
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

        fig = self.antenna.plot_delay(self.target_relative_position, self.get_selected_if_id(), adjusted=True)
        canvas = FigureCanvasTkAgg(fig, master=self.frames[0])
        canvas.draw()
        canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        canvas.mpl_connect("button_press_event", self.on_click)
        self.present_phase_fig = fig
        self.present_phase_canvas = canvas

    def position_plot(self):
        if self.present_position_fig is not None:
            plt.close(self.present_position_fig)

        primary_ra = float(self.primary["RA"])
        primary_dec = float(self.primary["DEC"])
        target_ra = float(self.target["RA"])
        target_dec = float(self.target["DEC"])
        cal_ra = [float(c.ra) for c in self.secondary_calibrators]
        cal_dec = [float(c.dec) for c in self.secondary_calibrators]
        all_x = [primary_ra, target_ra] + cal_ra
        all_y = [primary_dec, target_dec] + cal_dec
        x_span = float(np.ptp(all_x)) + 1e-6
        y_span = float(np.ptp(all_y)) + 1e-6
        ratio = np.clip(x_span / y_span, 0.25, 4.0)
        base_size = 3.0
        fig_width = base_size * float(np.sqrt(ratio))
        fig_height = base_size / float(np.sqrt(ratio))

        rc('xtick', direction='in')
        rc('ytick', direction='in')

        w = WCS(naxis=2)
        w.wcs.crval = [primary_ra, primary_dec]
        w.wcs.crpix = [500, 500]
        w.wcs.cdelt = np.array([-0.002, 0.002])
        w.wcs.ctype = ["RA---TAN", "DEC--TAN"]

        fig, ax = plt.subplots(1, 1, figsize=(fig_width, fig_height), subplot_kw={'projection': w})
        fig.subplots_adjust(left=0.12, right=0.98, top=0.96, bottom=0.12)
        ax.coords.grid(True, color="gray", ls="--", alpha=0.5)
        ax.set_xlabel("RA")
        ax.set_ylabel("DEC")

        prim_x, prim_y = w.world_to_pixel_values(primary_ra, primary_dec)
        targ_x, targ_y = w.world_to_pixel_values(target_ra, target_dec)

        ax.plot(prim_x, prim_y, marker='*', markersize=8, color='k')
        ax.text(prim_x, prim_y, self.primary.get("NAME", "PRIMARY"), ha="center", va="bottom", fontsize=8)
        ax.plot(targ_x, targ_y, marker='^', markersize=8, color='#A52C2C')
        ax.text(targ_x, targ_y, self.target["NAME"], ha="center", va="bottom", fontsize=8)

        for i, item in enumerate(self.secondary_calibrators):
            x, y = w.world_to_pixel_values(float(item.ra), float(item.dec))
            color = self.antenna.colors[i % len(self.antenna.colors)]
            ax.plot(x, y, marker='o', markersize=7, color=color)
            ax.text(x, y, item.name, ha="center", va="bottom", fontsize=7, color=color)
        canvas = FigureCanvasTkAgg(fig, master=self.lower_frames[0])
        canvas.draw()
        canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.present_position_fig = fig

    def save(self, adj_dir, mv_dir):
        self.config['reverse'] = self.antenna.reverse
        self.config['t_flag'] = self.antenna.delay_t_flag_info
        self.antenna.save_delay(adj_dir, mv_dir)
