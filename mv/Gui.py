"""
class for GUI
@Author: Jingdong Zhang
@DATE  : 2024/7/22
"""
import copy

import mv


class Gui:
    def __init__(self, target, antenna, config, target_relative_position, secondary_calibrators, mv_flag=False):
        self.target = target
        self.antenna = antenna
        self.config = copy.deepcopy(config)
        self.target_relative_position = target_relative_position
        self.secondary_calibrators = secondary_calibrators

        # run mv with default settings
        self.antenna.multiview(self.config['max_depth'], self.config['max_ang_v'], self.config['min_z'], 1.,
                               self.config['kalman_factor'], self.config['smo_half_window'])

        # init windows
        self.root_window = mv.RootWindow(self.target, antenna, self.config)
        if mv_flag:
            self.root_window.load()
        self.config_window = mv.ConfigWindow(self.root_window, antenna, self.config)
        self.adjust_window = mv.AdjustWindow(self.root_window, antenna, self.config,
                                             target_relative_position, secondary_calibrators)
        self.root_window.config_window = self.config_window
        self.root_window.adjust_window = self.adjust_window
        self.root_window.run()
