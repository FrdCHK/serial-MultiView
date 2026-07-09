"""
class for GUI
@Author: Jingdong Zhang
@DATE  : 2024/7/22
"""
import copy

from .RootWindow import RootWindow
from .ConfigWindow import ConfigWindow
from .AdjustWindow import AdjustWindow
from .Antenna import Antenna
from .solver_config import apply_solver_defaults, solver_kwargs


class Gui:
    def __init__(self, target, primary, antenna: Antenna, config, target_relative_position, secondary_calibrators, mv_flag=False):
        self.target = target
        self.primary = primary
        self.antenna = antenna
        self.config = copy.deepcopy(config)
        apply_solver_defaults(self.config)
        self.default_config = copy.deepcopy(config)
        apply_solver_defaults(self.default_config)
        self.target_relative_position = target_relative_position
        self.secondary_calibrators = secondary_calibrators

        self.antenna.delay_multiview(**solver_kwargs(self.config))

        self.root_window = RootWindow(self.target, antenna, self.config)
        if mv_flag:
            self.root_window.load()
            self.config_window = ConfigWindow(self.root_window, antenna, self.config, self.default_config)
        else:
            self.config_window = ConfigWindow(self.root_window, antenna, self.config)
        self.adjust_window = AdjustWindow(
            self.root_window, antenna, self.config,
            self.target, self.primary, target_relative_position, secondary_calibrators
        )
        self.root_window.config_window = self.config_window
        self.root_window.adjust_window = self.adjust_window
        self.root_window.run()
