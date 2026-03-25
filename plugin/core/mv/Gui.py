"""
class for GUI
@Author: Jingdong Zhang
@DATE  : 2024/7/22
"""
import copy

from .RootWindow import RootWindow
from .ConfigWindow import ConfigWindow
from .AdjustWindow import AdjustWindow
from .DelayRootWindow import DelayRootWindow
from .DelayConfigWindow import DelayConfigWindow
from .DelayAdjustWindow import DelayAdjustWindow


class Gui:
    def __init__(self, target, primary, antenna, config, target_relative_position, secondary_calibrators, mv_flag=False):
        self.target = target
        self.primary = primary
        self.antenna = antenna
        self.config = copy.deepcopy(config)
        self.default_config = copy.deepcopy(config)
        self.target_relative_position = target_relative_position
        self.secondary_calibrators = secondary_calibrators

        # delay GUI first (independent windows)
        delay_smo = self.config.get("delay_smo_half_window", self.config.get("smo_half_window", 5))
        delay_kalman = self.config.get("delay_kalman_factor", self.config.get("kalman_factor", 0.08))
        self.config["delay_smo_half_window"] = delay_smo
        self.config["delay_kalman_factor"] = delay_kalman
        self.antenna.delay_multiview(kalman_factor=delay_kalman, smo_half_window=delay_smo)

        self.delay_root_window = DelayRootWindow(self.target, antenna, self.config)
        if mv_flag:
            self.delay_root_window.load()
            self.delay_config_window = DelayConfigWindow(self.delay_root_window, antenna, self.config, self.default_config)
            self.antenna.delay_multiview(kalman_factor=delay_kalman, smo_half_window=delay_smo)
            self.delay_root_window.delay_normal_vector_plot()
        else:
            self.delay_config_window = DelayConfigWindow(self.delay_root_window, antenna, self.config)
        self.delay_adjust_window = DelayAdjustWindow(self.delay_root_window, antenna, self.config,
                                                     self.target, self.primary, target_relative_position, secondary_calibrators)
        self.delay_root_window.config_window = self.delay_config_window
        self.delay_root_window.adjust_window = self.delay_adjust_window
        self.delay_root_window.run()

        # phase GUI next (original behavior)
        if_freq = self.config.get("if_freq")
        if if_freq is None:
            if_freq = self.config.get("obs_freq")
        if isinstance(if_freq, (list, tuple)):
            freq0 = if_freq[0] if len(if_freq) > 0 else None
        else:
            try:
                freq0 = float(if_freq) if if_freq is not None else None
            except (TypeError, ValueError):
                freq0 = None
        if freq0 is not None:
            self.antenna.apply_delay_phase_correction(target_relative_position, freq0, 0)

        self.antenna.multiview(self.config['max_depth'], self.config['max_ang_v'], self.config['min_z'],
                               self.config['weight'], self.config['kalman_factor'], self.config['smo_half_window'])
        self.root_window = RootWindow(self.target, antenna, self.config)
        if mv_flag:
            self.root_window.load()  # original load behavior
            self.config_window = ConfigWindow(self.root_window, antenna, self.config, self.default_config)
        else:
            self.config_window = ConfigWindow(self.root_window, antenna, self.config)
        self.adjust_window = AdjustWindow(self.root_window, antenna, self.config,
                                          self.target, self.primary, target_relative_position, secondary_calibrators)
        self.root_window.config_window = self.config_window
        self.root_window.adjust_window = self.adjust_window
        self.root_window.run()
