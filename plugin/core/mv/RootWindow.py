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

        base_dir = self.config.get("mv_workspace")
        if not base_dir:
            workspace = self.config.get("workspace")
            exp_name = self.config.get("exp_name", "exp")
            userno = self.config.get("userno", self.config.get("aips_userno", ""))
            if workspace:
                if userno != "":
                    base_dir = os.path.join(workspace, "mv", f"{exp_name}-{userno}")
                else:
                    base_dir = os.path.join(workspace, "mv", exp_name)
            else:
                base_dir = os.path.join(".", "exp", f"{exp_name}-{userno}")
        self.user_exp_dir = base_dir
        os.makedirs(self.user_exp_dir, exist_ok=True)

        self.save_dir = os.path.join(self.user_exp_dir, f"{self.target['ID']}-{self.target['NAME']}-SAVE")
        os.makedirs(self.save_dir, exist_ok=True)
        self.mv_dir = os.path.join(self.user_exp_dir, f"{self.target['ID']}-{self.target['NAME']}-MV")
        os.makedirs(self.mv_dir, exist_ok=True)
        self.image_dir = os.path.join(self.user_exp_dir, f"{self.target['ID']}-{self.target['NAME']}-IMAGE")
        os.makedirs(self.image_dir, exist_ok=True)
        self.adj_dir = os.path.join(self.save_dir, f"{self.target['ID']}-{self.target['NAME']}-{self.antenna.id}-{self.antenna.name}-ADJ.csv")
        self.delay_adj_dir = os.path.join(self.save_dir, f"{self.target['ID']}-{self.target['NAME']}-{self.antenna.id}-{self.antenna.name}-DELAY-ADJ.csv")
        self.conf_dir = os.path.join(self.save_dir, f"{self.target['ID']}-{self.target['NAME']}-{self.antenna.id}-{self.antenna.name}-CONF.yaml")

        self.config_window = None
        self.adjust_window = None
        self.delay_adjust_window = None

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
        button_finish = tk.Button(self.frames[2], text="finish", font=self.font, command=self.finish)
        button_finish.grid(row=0, column=1, sticky="nsew", padx=30, pady=10)

        self.present_fig = None
        self.root_normal_vector_plot()

    def run(self):
        self.root.mainloop()

    def finish(self):
        # save config and mv result
        # NOTE: must run adjust_window.save before yaml dump to ensure reverse para to be saved
        self.adjust_window.save(self.adj_dir, os.path.join(self.mv_dir, f"{self.target['ID']}-{self.target['NAME']}-{self.antenna.id}-{self.antenna.name}.csv"))
        if self.delay_adjust_window is not None:
            self.delay_adjust_window.save(self.delay_adj_dir, os.path.join(self.mv_dir, f"{self.target['ID']}-{self.target['NAME']}-{self.antenna.id}-{self.antenna.name}-DELAY.csv"))
        with open(self.conf_dir, 'w') as f:
            yaml.safe_dump(self.config, f)
        # save figures
        self.present_fig.savefig(os.path.join(self.image_dir, f"{self.target['ID']}-{self.target['NAME']}-{self.antenna.id}-{self.antenna.name}-VECTOR.png"), bbox_inches='tight')
        self.present_fig.savefig(os.path.join(self.image_dir, f"{self.target['ID']}-{self.target['NAME']}-{self.antenna.id}-{self.antenna.name}-VECTOR.pdf"), bbox_inches='tight')
        # self.present_fig.savefig(os.path.join(self.image_dir, f"{self.target['ID']}-{self.target['NAME']}-{self.antenna.id}-{self.antenna.name}-VECTOR.eps"))
        self.adjust_window.phase_plot()
        self.adjust_window.present_phase_fig.savefig(os.path.join(self.image_dir, f"{self.target['ID']}-{self.target['NAME']}-{self.antenna.id}-{self.antenna.name}-PHASE.png"), bbox_inches='tight')
        self.adjust_window.present_phase_fig.savefig(os.path.join(self.image_dir, f"{self.target['ID']}-{self.target['NAME']}-{self.antenna.id}-{self.antenna.name}-PHASE.pdf"), bbox_inches='tight')
        # self.adjust_window.present_phase_fig.savefig(os.path.join(self.image_dir, f"{self.target['ID']}-{self.target['NAME']}-{self.antenna.id}-{self.antenna.name}-PHASE.eps"))
        if self.delay_adjust_window is not None:
            self.delay_adjust_window.delay_plot()
            self.delay_adjust_window.present_delay_fig.savefig(os.path.join(self.image_dir, f"{self.target['ID']}-{self.target['NAME']}-{self.antenna.id}-{self.antenna.name}-DELAY.png"), bbox_inches='tight')
            self.delay_adjust_window.present_delay_fig.savefig(os.path.join(self.image_dir, f"{self.target['ID']}-{self.target['NAME']}-{self.antenna.id}-{self.antenna.name}-DELAY.pdf"), bbox_inches='tight')

        self.root.destroy()
        plt.close('all')

    def root_normal_vector_plot(self):
        if self.antenna.mv_result is None:
            return
        # close present fig
        if self.present_fig is not None:
            plt.close(self.present_fig)

        fig = self.antenna.plot_normal_vector()
        canvas = FigureCanvasTkAgg(fig, master=self.frames[1])
        canvas.draw()
        canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        self.present_fig = fig

    def rerun(self, adjust=True):
        self.antenna.multiview(self.config['max_depth'], self.config['max_ang_v'], self.config['min_z'],
                               self.config['weight'], self.config['kalman_factor'], self.config['smo_half_window'])
        self.root_normal_vector_plot()
        if adjust:
            self.adjust_window.phase_plot()
            self.adjust_window.manual_toggle.set(False)
            if self.delay_adjust_window is not None:
                self.delay_adjust_window.delay_plot()

    def load(self, do_rerun=True):
        with open(self.conf_dir, 'r') as f:
            config_load = yaml.safe_load(f)
            for key, value in config_load.items():
                self.config[key] = value
        adjust_load = pd.read_csv(self.adj_dir)
        for i, item in adjust_load.iterrows():
            self.antenna.adjust_info.loc[i] = item
        self.antenna.update_data()
        if os.path.isfile(self.delay_adj_dir):
            delay_adjust_load = pd.read_csv(self.delay_adj_dir)
            for i, item in delay_adjust_load.iterrows():
                if i < self.antenna.delay_adjust_info.index.size:
                    self.antenna.delay_adjust_info.loc[i] = item
            self.antenna.update_delay_data()
        if 'reverse' in config_load.keys():
            self.antenna.reverse = config_load['reverse']
        if 't_flag' in config_load.keys():
            self.antenna.t_flag_info = config_load['t_flag']
        if 'delay_t_flag' in config_load.keys():
            self.antenna.delay_t_flag_info = config_load['delay_t_flag']
        if do_rerun:
            self.rerun(False)
