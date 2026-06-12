"""
3D slice window for serial MultiView delay inspection.
"""
import numpy as np
import tkinter as tk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.widgets import RangeSlider
from astropy.coordinates import SkyCoord
from astropy import units as u

from .plane import plane
from .Antenna import Antenna


class Slice3DWindow:
    def __init__(self, parent, antenna: Antenna, target, primary, secondary_calibrators, get_selected_if_id, on_close=None):
        self.parent = parent
        self.antenna = antenna
        self.target = target
        self.primary = primary
        self.secondary_calibrators = secondary_calibrators
        self.get_selected_if_id = get_selected_if_id
        self.on_close = on_close
        self.delay_display_scale = 1e12
        self.target_color = "#A52C2C"
        target_coord = SkyCoord(self.target["RA"], self.target["DEC"], unit=u.deg, frame='icrs')
        pri_coord = SkyCoord(self.primary["RA"], self.primary["DEC"], unit=u.deg, frame='icrs')
        dx, dy = target_coord.spherical_offsets_to(pri_coord)
        self.target_x = dx.deg
        self.target_y = dy.deg

        self.window = tk.Toplevel(parent.root)
        self.window.title("3D slice")
        self.window.geometry("900x760+700+120")
        self.window.minsize(width=600, height=600)
        self.window.protocol("WM_DELETE_WINDOW", self.close)

        self.window.grid_rowconfigure(0, weight=18)
        self.window.grid_rowconfigure(1, weight=1)
        self.window.grid_columnconfigure(0, weight=1)

        self.plot_frame = tk.Frame(self.window)
        self.plot_frame.grid(row=0, column=0, sticky="nsew")
        self.slider_frame = tk.Frame(self.window)
        self.slider_frame.grid(row=1, column=0, sticky="nsew")

        self.figure = plt.figure(figsize=(8, 7))
        self.figure.subplots_adjust(left=0.06, right=0.97, top=0.95, bottom=0.12, hspace=0.1)
        self.ax = self.figure.add_subplot(111, projection="3d")
        self.slider_ax = self.figure.add_axes([0.12, 0.04, 0.7, 0.04])

        self.canvas = FigureCanvasTkAgg(self.figure, master=self.plot_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        self.canvas.mpl_connect("button_press_event", self._on_mouse_press)
        self.canvas.mpl_connect("motion_notify_event", self._on_mouse_move)
        self.canvas.mpl_connect("button_release_event", self._on_mouse_release)
        self.canvas.mpl_connect("scroll_event", self._on_scroll)

        self.time_min, self.time_max = self._get_time_bounds()
        self.slider = RangeSlider(
            self.slider_ax,
            "time",
            self.time_min,
            self.time_max,
            valinit=(self.time_min, self.time_max),
            facecolor="#888888",
        )
        self.slider.on_changed(self._on_slider_change)

        self._updating = False
        self._right_drag = None
        self.box_aspect_scale = 1.0
        self.tip_window = None
        self.tip_label = tk.Label(
            self.window,
            text="?",
            bg="#1f1f1f",
            fg="white",
            font=("Consolas", 12, "bold"),
            padx=6,
            pady=2,
            cursor="question_arrow",
        )
        self.tip_label.place(relx=0.01, rely=0.985, anchor="sw")
        self.tip_label.bind("<Enter>", self._show_tip)
        self.tip_label.bind("<Leave>", self._hide_tip)
        self.refresh()

    def _get_time_bounds(self):
        if self.antenna.original_data.empty:
            return 0.0, 1.0
        t_min = float(self.antenna.original_data["t"].min())
        t_max = float(self.antenna.original_data["t"].max())
        if t_min == t_max:
            t_max = t_min + 1.0
        return t_min, t_max

    def _get_slice_range(self):
        try:
            t0, t1 = self.slider.val
        except Exception:
            t0, t1 = self.time_min, self.time_max
        if t0 > t1:
            t0, t1 = t1, t0
        return float(t0), float(t1)

    def _get_center_normal(self, if_id, slice_range):
        mv = self.antenna.delay_mv_result.get(if_id)
        mv_t = self.antenna.delay_mv_t
        if mv is None or mv_t is None or len(mv_t) == 0:
            return None
        center_t = 0.5 * (slice_range[0] + slice_range[1])
        idx = int(np.argmin(np.abs(np.asarray(mv_t) - center_t)))
        if idx < 0 or idx >= len(mv):
            return None
        normal = np.asarray(mv[idx]).reshape(-1)
        if normal.size < 3:
            return None
        norm = np.array(normal[:3], dtype=float)
        nrm = np.linalg.norm(norm)
        if nrm == 0:
            return None
        return norm / nrm

    def _build_plane(self, normal, x_vals, y_vals):
        if normal is None:
            return None, None, None
        # Convert the solver's delay scale to the displayed delay scale.
        scale_ratio = self.antenna.z_scale / self.delay_display_scale if self.delay_display_scale != 0 else 1.0
        nz = float(normal[2]) * scale_ratio
        if abs(nz) < 1e-12:
            return None, None, None
        x_min, x_max = float(np.min(x_vals)), float(np.max(x_vals))
        y_min, y_max = float(np.min(y_vals)), float(np.max(y_vals))
        x_margin = max(0.05, 0.15 * max(abs(x_min), abs(x_max), 1e-6))
        y_margin = max(0.05, 0.15 * max(abs(y_min), abs(y_max), 1e-6))
        x = np.linspace(x_min - x_margin, x_max + x_margin, 20)
        y = np.linspace(y_min - y_margin, y_max + y_margin, 20)
        X, Y = np.meshgrid(x, y)
        Z = plane(normal[0], normal[1], nz, X, Y)
        return X, Y, Z

    def refresh(self):
        if self.antenna.original_data.empty:
            self.ax.clear()
            self.ax.text2D(0.5, 0.5, "No data available", transform=self.ax.transAxes, ha="center", va="center")
            self.canvas.draw_idle()
            return

        if_id = self.get_selected_if_id()
        self.antenna.update_delay_data(if_id)
        slice_range = self._get_slice_range()
        self.ax.clear()

        markers = ['o', 'd', '^', 's', 'v', 'p', 'h', '*', '8', '<', '>', 'H', 'D', 'X', 'P']
        x_vals = [0.0]
        y_vals = [0.0]
        z_vals = [0.0]

        current_data = self.antenna.data.loc[
            (self.antenna.data["t"] >= slice_range[0]) & (self.antenna.data["t"] <= slice_range[1])
        ].copy(deep=True)
        flagged_index = self.antenna.delay_adjust_info[self.antenna._flag_col(if_id)] == 1
        flagged_data = self.antenna.original_data.loc[flagged_index].copy(deep=True)
        flagged_data = flagged_data.loc[
            (flagged_data["t"] >= slice_range[0]) & (flagged_data["t"] <= slice_range[1])
        ].copy(deep=True)

        self.ax.scatter(0.0, 0.0, 0.0, marker="*", s=90, c="k", label=self.primary.get("NAME", "PRIMARY"))

        for i, item in enumerate(self.secondary_calibrators):
            plot_data = current_data.loc[current_data["calsour"] == item.id].copy(deep=True)
            if not plot_data.empty:
                plot_data = self.antenna._correct_delay_with_phase(plot_data, if_id)
                x_vals.extend(plot_data["x"].tolist())
                y_vals.extend(plot_data["y"].tolist())
                plot_data["delay_disp"] = plot_data["total_delay"] * self.delay_display_scale
                z_vals.extend(plot_data["delay_disp"].tolist())
                self.ax.scatter(
                    plot_data["x"], plot_data["y"], plot_data["delay_disp"],
                    marker=markers[i % len(markers)], c=[self.antenna.colors[i % len(self.antenna.colors)]],
                    s=34, alpha=1.0, label=item.name,
                )

            flagged_plot = flagged_data.loc[flagged_data["calsour"] == item.id].copy(deep=True)
            if not flagged_plot.empty:
                flagged_plot = self.antenna._correct_delay_with_phase(flagged_plot, if_id)
                x_vals.extend(flagged_plot["x"].tolist())
                y_vals.extend(flagged_plot["y"].tolist())
                flagged_plot["delay_disp"] = flagged_plot["total_delay"] * self.delay_display_scale
                z_vals.extend(flagged_plot["delay_disp"].tolist())
                self.ax.scatter(
                    flagged_plot["x"], flagged_plot["y"], flagged_plot["delay_disp"],
                    marker=markers[i % len(markers)], c=[self.antenna.colors[i % len(self.antenna.colors)]],
                    s=34, alpha=0.3,
                )

        normal = self._get_center_normal(if_id, slice_range)
        target_z = 0.0
        if normal is not None:
            target_z = plane(normal[0], normal[1], normal[2], self.target_x, self.target_y)
        self.ax.scatter(self.target_x, self.target_y, target_z, marker="^", s=70, c=self.target_color, label=self.target["NAME"])
        X, Y, Z = self._build_plane(normal, np.asarray(x_vals), np.asarray(y_vals))
        if X is not None and Y is not None and Z is not None:
            self.ax.plot_surface(X, Y, Z, color="#7A9CC6", alpha=0.25, linewidth=0, antialiased=True)

        if z_vals:
            self.ax.plot(
                [self.target_x, self.target_x],
                [self.target_y, self.target_y],
                [min(z_vals), max(z_vals)],
                color=self.target_color,
                linewidth=1.0,
                alpha=0.9,
            )

        x_pad = max(0.05, 0.15 * max(np.ptp(x_vals), 1e-6))
        y_pad = max(0.05, 0.15 * max(np.ptp(y_vals), 1e-6))
        z_pad = max(0.05, 0.15 * max(np.ptp(z_vals), 1e-6))
        self.ax.set_xlim(max(x_vals) + x_pad, min(x_vals) - x_pad)
        self.ax.set_ylim(min(y_vals) - y_pad, max(y_vals) + y_pad)
        self.ax.set_zlim(min(z_vals) - z_pad, max(z_vals) + z_pad)

        try:
            self.ax.set_box_aspect((
                np.ptp(x_vals) + 1e-6,
                np.ptp(y_vals) + 1e-6,
                (np.ptp(z_vals) + 1e-6) * self.box_aspect_scale,
            ))
        except Exception:
            pass

        self.ax.set_xlabel("Relative RA")
        self.ax.set_ylabel("Relative DEC")
        self.ax.set_zlabel("Delay (ps)")
        self.ax.set_title(f"3D slice IF{if_id + 1}: {slice_range[0]:.6f} - {slice_range[1]:.6f}")
        self.ax.legend(loc="upper left", fontsize=8)
        self.canvas.draw_idle()

    def _on_slider_change(self, _value):
        if self._updating:
            return
        self.refresh()

    def _show_tip(self, _event=None):
        if self.tip_window is not None:
            return
        text = (
            "3D slice controls\n"
            "Left drag: rotate\n"
            "Right drag: change axis aspect\n"
            "Mouse wheel: zoom Z\n"
            "Slider: choose time slice"
        )
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
            font=("Consolas", 10),
        )
        label.pack()
        x = self.tip_label.winfo_rootx() + 18
        y = self.tip_label.winfo_rooty() - 70
        self.tip_window.geometry(f"+{x}+{y}")

    def _hide_tip(self, _event=None):
        if self.tip_window is not None:
            self.tip_window.destroy()
            self.tip_window = None

    def _on_mouse_press(self, event):
        if event.inaxes != self.ax or event.button != 3:
            return
        self._right_drag = {
            "y": event.y,
            "scale": self.box_aspect_scale,
        }

    def _on_mouse_move(self, event):
        if self._right_drag is None:
            return
        if event.y is None:
            return
        dy = event.y - self._right_drag["y"]
        scale = float(np.exp(-dy * 0.005))
        self.box_aspect_scale = float(np.clip(self._right_drag["scale"] * scale, 0.01, 100))
        self.refresh()

    def _on_mouse_release(self, event):
        if event.button == 3:
            self._right_drag = None

    def _on_scroll(self, event):
        if event.inaxes != self.ax:
            return
        scale = 0.9 if event.button == "up" else 1.1 if event.button == "down" else None
        if scale is None:
            return
        lo, hi = self.ax.get_zlim()
        center = 0.5 * (lo + hi)
        half = 0.5 * (hi - lo) * scale
        self.ax.set_zlim(center - half, center + half)
        self.canvas.draw_idle()

    def close(self):
        if self.on_close is not None:
            self.on_close()
        try:
            self._hide_tip()
            self.window.destroy()
        finally:
            plt.close(self.figure)
