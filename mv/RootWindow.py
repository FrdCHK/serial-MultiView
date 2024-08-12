"""
root window of GUI
@Author: Jingdong Zhang
@DATE  : 2024/8/6
"""
import os
import pandas as pd
import tkinter as tk
from tkinter import font
import matplotlib.pyplot as plt
import yaml
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class RootWindow:
    def __init__(self, target, antenna, config):
        self.target = target
        self.antenna = antenna
        self.config = config

        self.user_exp_dir = f"./exp/{self.config['exp_name']}-{self.config['aips_userno']}"
        self.save_dir = os.path.join(self.user_exp_dir, f"{self.target['ID']}-{self.target['NAME']}-SAVE")
        if not os.path.exists(self.save_dir):
            os.mkdir(self.save_dir)
        self.mv_dir = os.path.join(self.user_exp_dir, f"{self.target['ID']}-{self.target['NAME']}-MV")
        if not os.path.exists(self.mv_dir):
            os.mkdir(self.mv_dir)
        self.image_dir = os.path.join(self.user_exp_dir, f"{self.target['ID']}-{self.target['NAME']}-IMAGE")
        if not os.path.exists(self.image_dir):
            os.mkdir(self.image_dir)
        self.adj_dir = os.path.join(self.save_dir, f"{self.target['ID']}-{self.target['NAME']}-{self.antenna.id}-{self.antenna.name}-ADJ.csv")
        self.conf_dir = os.path.join(self.save_dir, f"{self.target['ID']}-{self.target['NAME']}-{self.antenna.id}-{self.antenna.name}-CONF.yaml")

        self.config_window = None
        self.adjust_window = None

        self.root = tk.Tk()
        self.root.title("PLOT")
        self.root.geometry("600x560+0+60")
        self.root.minsize(width=600, height=560)

        self.font = font.Font(family="Consolas", size=16)

        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=6)
        self.root.grid_rowconfigure(2, weight=1)
        # self.root.grid_rowconfigure(3, weight=1)

        self.frames = []
        frame = tk.Frame(self.root)
        frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.frames.append(frame)
        frame = tk.Frame(self.root)
        frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.frames.append(frame)
        frame = tk.Frame(self.root)
        frame.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
        self.frames.append(frame)

        # top frame
        self.frames[0].grid_columnconfigure(0, weight=1)
        self.frames[0].grid_rowconfigure(0, weight=1)

        label_text = f"Target: {self.target['ID']} {self.target['NAME']}   Antenna: {self.antenna.id} {self.antenna.name}"
        label_info = tk.Label(self.frames[0], text=label_text, font=self.font, anchor="center")
        label_info.grid(row=0, column=0, sticky="nsew", padx=30, pady=10)

        # normal vector plot
        self.frames[1].grid_columnconfigure(0, weight=1)
        self.frames[1].grid_rowconfigure(0, weight=1)

        # bottom frame
        self.frames[2].grid_columnconfigure(0, weight=1)
        self.frames[2].grid_columnconfigure(1, weight=1)
        self.frames[2].grid_rowconfigure(0, weight=1)

        button_rerun = tk.Button(self.frames[2], text="rerun", font=self.font, command=self.rerun)
        button_rerun.grid(row=0, column=0, sticky="nsew", padx=30, pady=10)
        button_finish = tk.Button(self.frames[2], text="finish", font=self.font, command=self.stop)
        button_finish.grid(row=0, column=1, sticky="nsew", padx=30, pady=10)

        self.present_fig = None
        self.root_normal_vector_plot()

    def run(self):
        self.root.mainloop()

    def stop(self):
        # save config and mv result
        self.adjust_window.save(self.adj_dir, os.path.join(self.mv_dir, f"{self.target['ID']}-{self.target['NAME']}-{self.antenna.id}-{self.antenna.name}.csv"))
        with open(self.conf_dir, 'w') as f:
            yaml.safe_dump(self.config, f)
        # save figures
        self.present_fig.savefig(os.path.join(self.image_dir, f"{self.target['ID']}-{self.target['NAME']}-{self.antenna.id}-{self.antenna.name}-VECTOR.png"), bbox_inches='tight')
        # self.present_fig.savefig(os.path.join(self.image_dir, f"{self.target['ID']}-{self.target['NAME']}-{self.antenna.id}-{self.antenna.name}-VECTOR.eps"))
        self.adjust_window.phase_plot()
        self.adjust_window.present_phase_fig.savefig(os.path.join(self.image_dir, f"{self.target['ID']}-{self.target['NAME']}-{self.antenna.id}-{self.antenna.name}-PHASE.png"), bbox_inches='tight')
        # self.adjust_window.present_phase_fig.savefig(os.path.join(self.image_dir, f"{self.target['ID']}-{self.target['NAME']}-{self.antenna.id}-{self.antenna.name}-PHASE.eps"))

        self.root.destroy()
        plt.close('all')

    def root_normal_vector_plot(self):
        # close present fig
        if self.present_fig is not None:
            plt.close(self.present_fig)

        fig = self.antenna.plot_normal_vector()
        canvas = FigureCanvasTkAgg(fig, master=self.frames[1])
        canvas.draw()
        canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        self.present_fig = fig

    def rerun(self, adjust=True):
        self.antenna.multiview(self.config['max_depth'], self.config['max_ang_v'], self.config['min_z'], 1.,
                               self.config['kalman_factor'], self.config['smo_half_window'])
        self.root_normal_vector_plot()
        if adjust:
            self.adjust_window.phase_plot()
            self.adjust_window.manual_toggle.set(False)

    def load(self):
        with open(self.conf_dir, 'r') as f:
            config_load = yaml.safe_load(f)
            for key, value in config_load.items():
                self.config[key] = value
        adjust_load = pd.read_csv(self.adj_dir)
        for i, item in adjust_load.iterrows():
            self.antenna.adjust_info.loc[i] = item
        self.antenna.update_data()
        self.rerun(False)
