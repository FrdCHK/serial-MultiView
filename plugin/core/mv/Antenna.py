"""
class for antennas
@Author: Jingdong Zhang
@DATE  : 2024/7/17
"""
import numpy as np
import pandas as pd
import copy
import matplotlib.pyplot as plt
import scipy.interpolate as interp

from .plane import plane
from .Node import Node
from .recursion import recursion
from .find_min_leaf import find_min_leaf
from .rodrigues_rotation import rodrigues_rotation


class Antenna:
    def __init__(self, antenna_id, antenna_name, data, calibrators, delay_data=None, if_freq=None):
        """
        antenna class for MultiView
        :param antenna_id: antenna id
        :param antenna_name: antenna name
        :param data: input time series
        :param calibrators: secondary calibrator list
        """
        self.colors = plt.rcParams['axes.prop_cycle'].by_key()['color']  # default color sequence used by plt

        self.id = antenna_id
        self.name = antenna_name
        self.original_data = data.copy(deep=True)  # without flag and manual wrap
        self.original_data.reset_index(drop=True, inplace=True)
        self.data = self.original_data.copy(deep=True)  # flagged/wrapped data
        self.secondary_calibrators = calibrators
        self.adjust_info = pd.DataFrame(data=np.zeros(shape=(self.original_data.index.size, 2)),
                                        columns=['flag', 'wrap']).astype({'flag': int, 'wrap': int})
        self.t_flag_info = []
        self.mv_result = None
        self.mv_t = None
        # record accumulated wrap during auto mv procedure
        self.accu_info = pd.DataFrame(data=np.zeros(shape=(self.original_data.index.size, 1)),
                                      columns=['accu']).astype({'accu': float})
        self.accu_data = None  # data with flag+wrap+accu adjustment

        self.target_pos = None

        self.reverse = False

        # Delay branch for the one-step total-delay solution.
        if delay_data is None:
            delay_data = pd.DataFrame(columns=['calsour', 'x', 'y', 't'])
        self.original_delay_data = delay_data.copy(deep=True)
        self.original_delay_data.reset_index(drop=True, inplace=True)
        self.delay_if_ids = sorted(
            int(col[1:]) for col in self.original_delay_data.columns
            if col.startswith('d') and col[1:].isdigit()
        )
        self.if_freq = self._normalize_if_freq(if_freq, self.delay_if_ids)
        self.delay_data = self.original_delay_data.copy(deep=True)
        delay_adjust_columns = ['flag'] + [f'w{if_id}' for if_id in self.delay_if_ids]
        self.delay_adjust_info = pd.DataFrame(
            data=np.zeros(shape=(self.original_delay_data.index.size, len(delay_adjust_columns))),
            columns=delay_adjust_columns,
        )
        dtype_map = {'flag': int}
        dtype_map.update({f'w{if_id}': int for if_id in self.delay_if_ids})
        self.delay_adjust_info = self.delay_adjust_info.astype(dtype_map)
        self.delay_t_flag_info = []
        self.delay_mv_result = None
        self.delay_mv_t = None
        self.delay_scale = {}
        self.delay_target_if = {}
        self.delay_average = np.array([])
        self.delay_average_t = np.array([])

    @staticmethod
    def _normalize_if_freq(if_freq, delay_if_ids):
        if if_freq is None:
            return {if_id: 1.0 for if_id in delay_if_ids}
        if np.isscalar(if_freq):
            return {if_id: float(if_freq) for if_id in delay_if_ids}
        freq_list = list(if_freq)
        out = {}
        for if_id in delay_if_ids:
            if if_id < len(freq_list):
                out[if_id] = float(freq_list[if_id])
            elif freq_list:
                out[if_id] = float(freq_list[-1])
            else:
                out[if_id] = 1.0
        return out

    def multiview(self, max_depth=4, max_ang_v=864., min_z=0.67, weight=1., kalman_factor=None, smo_half_window=None):
        """
        MultiView function
        :param max_depth: max depth of recursion, defaults to 4
        :param max_ang_v: max angular velocity of plane rotation, controls the threshold for pruning, defaults to 864.
        :param min_z: minimum z value of normal vector, defaults to 0.67
        :param weight: weight of the total rotation angle in recursion, defaults to 1.
        :param kalman_factor: Kalman filter process noise that controls smooth effect and filter phase delay, defaults to 0.08.
        :param smo_half_window: half width of moving smoothing window, defaults to 5
        """
        if kalman_factor is not None and kalman_factor > 0:
            self._mv_kalman(max_depth, max_ang_v, min_z, weight, kalman_factor)
        else:
            self._mv_original(max_depth, max_ang_v, min_z, weight)

        if smo_half_window is not None and smo_half_window > 0:
            self._lowpass_filter(smo_half_window)

        self.accu_data = self.original_data.copy(deep=True)
        self.accu_data['phase'] += self.adjust_info['wrap'] * np.pi * 2
        self.accu_data['phase'] += self.accu_info['accu']
        non_flagged_index = self.adjust_info['flag'] == 0
        self.accu_data = self.accu_data.loc[non_flagged_index]
        self.accu_data.reset_index(drop=True, inplace=True)

    def flag(self, timerange, calibrators, mode='flag'):
        """
        flag or unflag data within given timerange
        :param timerange: the timerange to flag / unflag
        :param calibrators: calibrator list to flag / unflag
        :param mode: flag / unflag
        """
        flag_index = (self.original_data['t'] >= timerange[0]) & (self.original_data['t'] <= timerange[1])
        calibrator_index = self.original_data['calsour'].isin(calibrators)
        criteria_index = flag_index & calibrator_index
        if mode == 'flag':
            self.adjust_info.loc[criteria_index, 'flag'] = 1
        elif mode == 'unflag':
            self.adjust_info.loc[criteria_index, 'flag'] = 0
        else:
            raise ValueError('available modes are: flag, unflag')
        self.update_data()

    def t_flag(self, timerange, mode='flag'):
        """
        flag or unflag data within given timerange
        :param timerange: the timerange to flag / unflag
        :param mode: flag / unflag
        """
        if mode == 'flag':
            range_to_append = timerange
            range_list = copy.deepcopy(self.t_flag_info)
            loop_flag = True
            while loop_flag:
                loop_flag = False
                for item in range_list:
                    if item[0] < range_to_append[0] < range_to_append[1] < item[1]:
                        return
                    elif range_to_append[0] < item[0] < range_to_append[1] < item[1]:
                        range_to_append[1] = item[1]
                        range_list.remove(item)
                        loop_flag = True
                        break
                    elif item[0] < range_to_append[0] < item[1] < range_to_append[1]:
                        range_to_append[0] = item[0]
                        range_list.remove(item)
                        loop_flag = True
                        break
                    elif range_to_append[0] < item[0] < item[1] < range_to_append[1]:
                        range_list.remove(item)
                        loop_flag = True
                        break
            # no overlap anymore
            range_list.append(range_to_append)
            self.t_flag_info = range_list
        elif mode == 'unflag':
            range_to_remove = timerange
            range_list = copy.deepcopy(self.t_flag_info)
            loop_flag = True
            while loop_flag:
                loop_flag = False
                for item in range_list:
                    if item[0] < range_to_remove[0] < range_to_remove[1] < item[1]:
                        range_list.append([item[0], range_to_remove[0]])
                        range_list.append([range_to_remove[1], item[1]])
                        range_list.remove(item)
                        loop_flag = True
                        break
                    elif range_to_remove[0] < item[0] < range_to_remove[1] < item[1]:
                        range_list.append([range_to_remove[1], item[1]])
                        range_list.remove(item)
                        loop_flag = True
                        break
                    elif item[0] < range_to_remove[0] < item[1] < range_to_remove[1]:
                        range_list.append([item[0], range_to_remove[0]])
                        range_list.remove(item)
                        loop_flag = True
                        break
                    elif range_to_remove[0] < item[0] < item[1] < range_to_remove[1]:
                        range_list.remove(item)
                        loop_flag = True
                        break
            # no overlap anymore
            self.t_flag_info = range_list
        else:
            raise ValueError('available modes are: flag, unflag')

    def wrap(self, timerange, calibrators, mode='+'):
        """
        manually wrap data within given timerange
        :param timerange: the timerange to wrap
        :param calibrators: calibrator list to flag / unflag
        :param mode: + / -
        """
        wrap_index = (self.original_data['t'] >= timerange[0]) & (self.original_data['t'] <= timerange[1])
        calibrator_index = self.original_data['calsour'].isin(calibrators)
        criteria_index = wrap_index & calibrator_index
        if mode == '+':
            self.adjust_info.loc[criteria_index, 'wrap'] += 1
        elif mode == '-':
            self.adjust_info.loc[criteria_index, 'wrap'] -= 1
        else:
            raise ValueError('available modes are: +, -')
        self.update_data()

    def reset(self, root):
        """
        :param root: root tkinter window object
        """
        self.adjust_info.iloc[:, :] = 0
        self.data = self.original_data.copy(deep=True)
        self.t_flag_info = []
        root.rerun()

    def plot_normal_vector(self):
        linestyles = ['-', '--', ':']
        fig, ax = plt.subplots(1, 1, figsize=(8, 4))
        fig.subplots_adjust(left=0.07, right=0.98, top=0.98, bottom=0.1)
        for i in range(self.mv_result.shape[1]):
            ax.plot(self.mv_t, self.mv_result[:, i], ls=linestyles[i], label=chr(120 + i))
        ax.legend()
        ax.set_xlabel("time (day)")
        return fig

    def plot_phase(self, target_pos, ylim=True):
        """
        :param target_pos: relative position of the target
        :param ylim: whether to limit phase to +/- pi and fold data
        :return: matplotlib figure object
        """
        self.target_pos = target_pos

        markers = ['o', 'd', '^', 's', 'v', 'p', '*', '8', '<', '>']
        fig, ax = plt.subplots(1, 1, figsize=(8, 3))
        fig.subplots_adjust(left=0.06, right=0.99, top=0.98, bottom=0.1)

        mv_target_phase = []
        for i in range(self.mv_result.shape[0]):
            mv_target_phase.append(plane(*self.mv_result[i], *self.target_pos))
        mv_target_phase = np.array(mv_target_phase)
        mv_target_phase_wrap = (mv_target_phase + np.pi) % (2 * np.pi) - np.pi

        for i, item in enumerate(self.secondary_calibrators):
            if ylim:
                plot_data = self.original_data.copy(deep=True)
                non_flagged_index = self.adjust_info['flag'] == 0
                plot_data = plot_data.loc[non_flagged_index]
                plot_data = plot_data.loc[plot_data['calsour'] == item.id]
                ax.plot(plot_data['t'], plot_data['phase'], ls='none', marker=markers[i], label=item.name)
            else:
                plot_data = self.accu_data.loc[self.accu_data['calsour'] == item.id]
                ax.plot(plot_data['t'], plot_data['phase'], ls='none', marker=markers[i], label=item.name)

        if ylim:
            ax.plot(self.mv_t, mv_target_phase_wrap, 'x', color='k', ls='', label='Target')
        else:
            ax.plot(self.mv_t, mv_target_phase, 'x', color='#222222', alpha=0.6, ls='', label='Target')

        flagged_index = self.adjust_info['flag'] == 1
        flagged_data = self.original_data.loc[flagged_index].copy(deep=True)
        flagged_data.reset_index(drop=True, inplace=True)
        for i, item in enumerate(self.secondary_calibrators):
            plot_data = flagged_data.loc[flagged_data['calsour'] == item.id]
            if not plot_data.empty:
                ax.plot(plot_data['t'], plot_data['phase'], ls='none', marker=markers[i], c=self.colors[i], alpha=0.3)

        ax.set_xlabel("time (day)")
        ax.set_ylabel("phase (rad)")

        if ylim:
            y_max = np.pi
            y_min = -np.pi
            ax.set_ylim([y_min, y_max])

        for item in self.t_flag_info:
            y_lim = ax.get_ylim()
            ax.fill_betweenx(y_lim, item[0], item[1], color='#FFB6C1', alpha=0.15)
            ax.set_ylim(y_lim)

        ax.legend()

        return fig

    def delay_multiview(self, max_depth=4, max_ang_v=864., min_z=0.67, weight=1., kalman_factor=0.08, smo_half_window=None):
        """
        Solve total delay per IF independently, then average the solved target delay.
        """
        if self.original_delay_data.empty:
            self.delay_mv_result = {}
            self.delay_mv_t = np.array([])
            self.delay_target_if = {}
            self.delay_average = np.array([])
            self.delay_average_t = np.array([])
            return
        self.update_delay_data()
        if self.delay_data.empty or not self.delay_if_ids:
            self.delay_mv_result = {}
            self.delay_mv_t = np.array([])
            self.delay_target_if = {}
            self.delay_average = np.array([])
            self.delay_average_t = np.array([])
            return

        extend_length = 10
        data_extended = self._get_extended_delay_data(extend_length)
        delay_results = {}
        delay_target_if = {}
        for if_id in self.delay_if_ids:
            col = f"d{if_id}"
            if col not in data_extended.columns:
                continue
            freq_ghz = self.if_freq.get(if_id, 1.0)
            scale = 2 * np.pi * float(freq_ghz) * 1e9
            self.delay_scale[if_id] = scale
            # Minus sign preserves the original +2pi / -2pi semantics in delay space.
            data_view = data_extended[['calsour', 'x', 'y', 't', col]].copy(deep=True)
            data_view['phase'] = -data_view[col] * scale

            norm_vec = np.array([[0], [0], [1]])
            result = []
            root_node = Node({'prune': False, 'position': -1, 'action': 0, 'angle': 0, 'total': 0, 'norm': np.zeros((3, 1))})
            calsour = data_view['calsour'].unique()
            accu = {sour: 0. for sour in calsour}
            z_lim = min_z
            ang_v = max_ang_v
            n = 3
            A = np.eye(n)
            H = np.eye(n)
            Q = np.eye(n) * kalman_factor
            R = np.eye(n) * 0.1
            x_hat = np.zeros((n, 1))
            P = np.eye(n)
            for i in range(data_view.index.size):
                calsour_this = data_view.loc[i, 'calsour']
                root_node.current = recursion(data_view, i, max_depth, norm_vec, accu, 0, ang_v, root_node, z_lim)
                root_node.plus = recursion(data_view, i, max_depth, norm_vec, accu, 1, ang_v, root_node, z_lim)
                root_node.minus = recursion(data_view, i, max_depth, norm_vec, accu, -1, ang_v, root_node, z_lim)
                norm_series = None
                if i > 5:
                    norm_series = np.zeros((i, 4))
                    norm_series[:, 0] = data_view.loc[:i - 1, 't']
                    norm_series[:, 1:] = np.array(result)
                    norm_series = norm_series[-6:, :]
                min_node, min_path = find_min_leaf(norm_series, data_view['t'], i, root_node, norm_vec, weight, (max_depth, max_ang_v, min_z))
                if min_node is None:
                    result.append(norm_vec.flatten())
                    root_node = Node({'prune': False, 'position': i, 'action': 0, 'angle': 0, 'total': 0, 'norm': norm_vec})
                    continue
                selected_next = min_path[1]
                accu[calsour_this] += selected_next['action'] * 2 * np.pi
                x_hat = A @ x_hat
                P = A @ P @ A.T + Q
                K = P @ H.T @ np.linalg.inv(H @ P @ H.T + R)
                x_hat = x_hat + K @ (selected_next['norm'] - H @ x_hat)
                P = (np.eye(n) - K @ H) @ P
                new_norm = x_hat
                result.append(new_norm.flatten())
                root_node = Node(selected_next)
                root_node.data['norm'] = new_norm
                norm_vec = new_norm

            mv_res = np.array(result[extend_length:])
            delay_results[if_id] = mv_res
            delay_target_if[if_id] = np.array([])

        self.delay_mv_result = delay_results
        if self.reverse and self.delay_data.index.size > 0:
            self.delay_mv_t = -(np.array(data_extended['t'])[extend_length:] - 2 * self.delay_data['t'].iloc[-1])
        else:
            self.delay_mv_t = np.array(data_extended['t'])[extend_length:]
        self.delay_target_if = delay_target_if

        if smo_half_window is not None and smo_half_window > 0:
            self._lowpass_filter_delay(smo_half_window)

        self._refresh_delay_target_series()

    def delay_flag(self, timerange, calibrators, mode='flag'):
        flag_index = (self.original_delay_data['t'] >= timerange[0]) & (self.original_delay_data['t'] <= timerange[1])
        calibrator_index = self.original_delay_data['calsour'].isin(calibrators)
        criteria_index = flag_index & calibrator_index
        if mode == 'flag':
            self.delay_adjust_info.loc[criteria_index, 'flag'] = 1
        elif mode == 'unflag':
            self.delay_adjust_info.loc[criteria_index, 'flag'] = 0
        else:
            raise ValueError('available modes are: flag, unflag')
        self.update_delay_data()

    def delay_wrap(self, timerange, calibrators, if_id, mode='+'):
        wrap_col = f'w{if_id}'
        if wrap_col not in self.delay_adjust_info.columns:
            return
        wrap_index = (self.original_delay_data['t'] >= timerange[0]) & (self.original_delay_data['t'] <= timerange[1])
        calibrator_index = self.original_delay_data['calsour'].isin(calibrators)
        criteria_index = wrap_index & calibrator_index
        if mode == '+':
            self.delay_adjust_info.loc[criteria_index, wrap_col] += 1
        elif mode == '-':
            self.delay_adjust_info.loc[criteria_index, wrap_col] -= 1
        else:
            raise ValueError('available modes are: +, -')
        self.update_delay_data()

    def delay_t_flag(self, timerange, mode='flag'):
        if mode == 'flag':
            range_to_append = timerange
            range_list = copy.deepcopy(self.delay_t_flag_info)
            loop_flag = True
            while loop_flag:
                loop_flag = False
                for item in range_list:
                    if item[0] < range_to_append[0] < range_to_append[1] < item[1]:
                        return
                    elif range_to_append[0] < item[0] < range_to_append[1] < item[1]:
                        range_to_append[1] = item[1]
                        range_list.remove(item)
                        loop_flag = True
                        break
                    elif item[0] < range_to_append[0] < item[1] < range_to_append[1]:
                        range_to_append[0] = item[0]
                        range_list.remove(item)
                        loop_flag = True
                        break
                    elif range_to_append[0] < item[0] < item[1] < range_to_append[1]:
                        range_list.remove(item)
                        loop_flag = True
                        break
            range_list.append(range_to_append)
            self.delay_t_flag_info = range_list
        elif mode == 'unflag':
            range_to_remove = timerange
            range_list = copy.deepcopy(self.delay_t_flag_info)
            loop_flag = True
            while loop_flag:
                loop_flag = False
                for item in range_list:
                    if item[0] < range_to_remove[0] < range_to_remove[1] < item[1]:
                        range_list.append([item[0], range_to_remove[0]])
                        range_list.append([range_to_remove[1], item[1]])
                        range_list.remove(item)
                        loop_flag = True
                        break
                    elif range_to_remove[0] < item[0] < range_to_remove[1] < item[1]:
                        range_list.append([range_to_remove[1], item[1]])
                        range_list.remove(item)
                        loop_flag = True
                        break
                    elif item[0] < range_to_remove[0] < item[1] < range_to_remove[1]:
                        range_list.append([item[0], range_to_remove[0]])
                        range_list.remove(item)
                        loop_flag = True
                        break
                    elif range_to_remove[0] < item[0] < item[1] < range_to_remove[1]:
                        range_list.remove(item)
                        loop_flag = True
                        break
            self.delay_t_flag_info = range_list
        else:
            raise ValueError('available modes are: flag, unflag')

    def delay_reset(self):
        self.delay_adjust_info.iloc[:, :] = 0
        self.delay_t_flag_info = []
        self.update_delay_data()

    def plot_delay(self, target_pos, if_id=0, adjusted=False):
        self.target_pos = target_pos
        self._refresh_delay_target_series()
        markers = ['o', 'd', '^', 's', 'v', 'p', '*', '8', '<', '>']
        fig, ax = plt.subplots(1, 1, figsize=(8, 3))
        fig.subplots_adjust(left=0.06, right=0.99, top=0.98, bottom=0.1)

        if if_id in self.delay_target_if and self.delay_target_if[if_id].size > 0:
            ax.plot(self.delay_mv_t, self.delay_target_if[if_id] * 1e12, 'x', color='k', ls='', label='Target')

        for i, item in enumerate(self.secondary_calibrators):
            plot_data = self.delay_data.copy(deep=True) if adjusted else self.original_delay_data.copy(deep=True)
            if not adjusted:
                non_flagged_index = self.delay_adjust_info['flag'] == 0
                plot_data = plot_data.loc[non_flagged_index]
            plot_data = plot_data.loc[plot_data['calsour'] == item.id]
            if not plot_data.empty:
                col = f"d{if_id}"
                if col in plot_data.columns:
                    ax.plot(plot_data['t'], plot_data[col] * 1e12, ls='none', marker=markers[i], label=item.name)

        flagged_index = self.delay_adjust_info['flag'] == 1
        flagged_data = self.original_delay_data.loc[flagged_index].copy(deep=True)
        flagged_data.reset_index(drop=True, inplace=True)
        for i, item in enumerate(self.secondary_calibrators):
            plot_data = flagged_data.loc[flagged_data['calsour'] == item.id]
            if not plot_data.empty:
                col = f"d{if_id}"
                if col in plot_data.columns:
                    ax.plot(plot_data['t'], plot_data[col] * 1e12, ls='none', marker=markers[i], c=self.colors[i], alpha=0.3)

        ax.set_xlabel("time (day)")
        ax.set_ylabel("total delay (ps)")
        ax.set_title(f"IF{if_id + 1}")
        for item in self.delay_t_flag_info:
            y_lim = ax.get_ylim()
            ax.fill_betweenx(y_lim, item[0], item[1], color='#FFB6C1', alpha=0.15)
            ax.set_ylim(y_lim)
        ax.legend()
        return fig

    def save(self, adj_dir, mv_dir):
        """
        Save adjustment and MultiView results
        :param adj_dir: adjustment directory
        :param mv_dir: MultiView directory
        """
        self.adjust_info.to_csv(adj_dir, index=False)
        mv_target_phase = []
        for i in range(self.mv_result.shape[0]):
            mv_target_phase.append(plane(*self.mv_result[i], *self.target_pos))
        mv_target_phase = np.array(mv_target_phase)
        mv_target_phase_wrap = (mv_target_phase + np.pi) % (2 * np.pi) - np.pi
        mv_table = pd.DataFrame({'t': self.mv_t, 'phase': mv_target_phase_wrap})
        mv_table.to_csv(mv_dir, index=False)

    def save_delay(self, delay_adj_dir, delay_mv_dir):
        self._refresh_delay_target_series()
        self.delay_adjust_info.to_csv(delay_adj_dir, index=False)
        mv_table = pd.DataFrame({
            't': self.delay_average_t if self.delay_average_t is not None else [],
            'mbdelay': self.delay_average if self.delay_average is not None else [],
        })
        mv_table.to_csv(delay_mv_dir, index=False)
        if self.delay_target_if:
            detail_path = delay_mv_dir.replace(".csv", "-IFS.csv")
            detail_table = pd.DataFrame({'t': self.delay_mv_t if self.delay_mv_t is not None else []})
            for if_id in self.delay_if_ids:
                if if_id in self.delay_target_if and self.delay_target_if[if_id].size > 0:
                    detail_table[f'd{if_id}'] = self.delay_target_if[if_id]
            detail_table.to_csv(detail_path, index=False)

    def update_data(self):
        self.data = self.original_data.copy(deep=True)
        self.data['phase'] += self.adjust_info['wrap'] * np.pi * 2
        non_flagged_index = self.adjust_info['flag'] == 0
        self.data = self.data.loc[non_flagged_index]
        self.data.reset_index(drop=True, inplace=True)

        self.accu_data = self.original_data.copy(deep=True)
        self.accu_data['phase'] += self.adjust_info['wrap'] * np.pi * 2
        self.accu_data['phase'] += self.accu_info['accu']
        self.accu_data = self.accu_data.loc[non_flagged_index]
        self.accu_data.reset_index(drop=True, inplace=True)

    def update_delay_data(self):
        self.delay_data = self.original_delay_data.copy(deep=True)
        if self.delay_data.empty:
            return
        for if_id in self.delay_if_ids:
            wrap_col = f'w{if_id}'
            delay_col = f'd{if_id}'
            if wrap_col in self.delay_adjust_info.columns and delay_col in self.delay_data.columns:
                wrap_step = 1.0 / (self.if_freq.get(if_id, 1.0) * 1e9)
                self.delay_data[delay_col] += -self.delay_adjust_info[wrap_col].to_numpy() * wrap_step
        non_flagged_index = self.delay_adjust_info['flag'] == 0
        self.delay_data = self.delay_data.loc[non_flagged_index]
        self.delay_data.reset_index(drop=True, inplace=True)

    def _get_extended_delay_data(self, extend_length=10):
        data_extended = self.delay_data.copy(deep=True)
        if data_extended.index.size == 0 or extend_length <= 0:
            return data_extended
        data_rev = data_extended.iloc[::-1, :].copy(deep=True)
        t = data_extended['t'].copy(deep=True)
        if self.reverse:
            data_rev['t'] = -t + 2 * t.iloc[-1]
            data_extended = pd.concat([data_extended.iloc[-(extend_length + 1):-1], data_rev], axis=0)
        else:
            data_rev['t'] = -t + 2 * t.iloc[0]
            data_extended = pd.concat([data_rev.iloc[-(extend_length + 1):-1], data_extended], axis=0)
        data_extended.reset_index(drop=True, inplace=True)
        return data_extended

    def _lowpass_filter_delay(self, smo_half_window=5):
        if not isinstance(self.delay_mv_result, dict):
            return
        mv_data = {k: copy.deepcopy(v) for k, v in self.delay_mv_result.items()}
        mv_t = np.array(self.delay_data.loc[:, 't'])
        mv_smo = {k: copy.deepcopy(v) for k, v in mv_data.items()}
        for if_id, arr in mv_data.items():
            for i in range(1, arr.shape[0] - 1):
                if i < smo_half_window:
                    smo_window_i = i
                elif i >= arr.shape[0] - smo_half_window:
                    smo_window_i = arr.shape[0] - 1 - i
                else:
                    smo_window_i = smo_half_window
                dt = np.abs(mv_t[i] - mv_t[i - smo_window_i:i + smo_window_i + 1])
                dt[dt == 0] = np.min(dt[dt != 0]) / np.e
                weights = np.log(1.0 / dt)
                weights[np.isinf(weights)] = np.max(weights[~np.isinf(weights)])
                normalized_weights = (weights / np.sum(weights)).reshape(smo_window_i * 2 + 1, 1)
                mv_smo[if_id][i] = np.sum(normalized_weights * arr[i - smo_window_i:i + smo_window_i + 1], axis=0)
        self.delay_mv_result = mv_smo
        self._refresh_delay_target_series()

    def plot_delay_normal_vector(self, if_id=None):
        if if_id is None:
            if_id = self.delay_if_ids[0] if self.delay_if_ids else 0
        if if_id not in self.delay_mv_result:
            return plt.figure(figsize=(8, 4))
        linestyles = ['-', '--', ':']
        fig, ax = plt.subplots(1, 1, figsize=(8, 4))
        fig.subplots_adjust(left=0.07, right=0.98, top=0.98, bottom=0.1)
        for i in range(self.delay_mv_result[if_id].shape[1]):
            ax.plot(self.delay_mv_t, self.delay_mv_result[if_id][:, i], ls=linestyles[i], label=chr(120 + i))
        ax.legend()
        ax.set_xlabel("time (day)")
        ax.set_title(f"Delay Normal Vector (IF{if_id + 1})")
        return fig

    def _refresh_delay_target_series(self):
        if self.target_pos is None:
            self.delay_average = np.array([])
            self.delay_average_t = np.array([])
            return
        refreshed = {}
        for if_id, mv_res in self.delay_mv_result.items():
            scale = self.delay_scale.get(if_id, 1.0)
            refreshed[if_id] = np.array(
                [-plane(*mv_res[i], *self.target_pos) / scale for i in range(mv_res.shape[0])]
            ) if mv_res.size > 0 else np.array([])
        self.delay_target_if = refreshed
        valid = [arr for arr in self.delay_target_if.values() if arr.size > 0]
        if valid:
            self.delay_average = np.mean(np.vstack(valid), axis=0)
            self.delay_average_t = np.array(self.delay_mv_t)
        else:
            self.delay_average = np.array([])
            self.delay_average_t = np.array([])

    def _get_extended_data(self, extend_length=10):
        """
        extend a small segment at the beginning of the time series using a reversed segment
        reverse if self.reverse=True
        :param extend_length: length of the extended part of the time series, defaults to 10
        :return: extended time series
        """
        data_extended = self.data.copy(deep=True)
        data_rev = data_extended.iloc[::-1, :].copy(deep=True)
        t = data_extended['t'].copy(deep=True)
        if self.reverse:
            # reversed version of t
            data_rev['t'] = -t + 2 * t.iloc[-1]
            data_extended = pd.concat([data_extended.iloc[-(extend_length + 1):-1], data_rev], axis=0)
        else:
            data_rev['t'] = -t + 2 * t.iloc[0]
            data_extended = pd.concat([data_rev.iloc[-(extend_length + 1):-1], data_extended], axis=0)
        data_extended.reset_index(drop=True, inplace=True)
        return data_extended

    def _lowpass_filter(self, smo_half_window=5):
        """
        lowpass filter (moving average)
        :param smo_half_window: half width of moving smoothing window, defaults to 5
        """
        mv_data = copy.deepcopy(self.mv_result)
        mv_t = np.array(self.data.loc[:, 't'])
        mv_smo = copy.deepcopy(mv_data)
        for i in range(1, mv_data.shape[0] - 1):
            if i < smo_half_window:
                smo_window_i = i
            elif i >= mv_data.shape[0] - smo_half_window:
                smo_window_i = mv_data.shape[0] - 1 - i
            else:
                smo_window_i = smo_half_window

            # delta-t log weighted moving average
            dt = np.abs(mv_t[i] - mv_t[i - smo_window_i:i + smo_window_i + 1])
            dt[dt == 0] = np.min(dt[dt != 0]) / np.e
            weights = np.log(1.0 / dt)
            weights[np.isinf(weights)] = np.max(weights[~np.isinf(weights)])
            normalized_weights = (weights / np.sum(weights)).reshape(smo_window_i * 2 + 1, 1)
            mv_smo[i] = np.sum(normalized_weights * mv_data[i - smo_window_i:i + smo_window_i + 1], axis=0)

        self.mv_result = mv_smo

    def _mv_kalman(self, max_depth=4, max_ang_v=864., min_z=0.67, weight=1., filter_process_noise=0.08):
        """
        calculate multiview phase plane with auto 2pi ambiguity detection (Kalman filter)
        :param max_depth: max depth of recursion, defaults to 4
        :param max_ang_v: max angular velocity of plane rotation, controls the threshold for pruning, defaults to 864.
        :param min_z: minimum z value of normal vector, defaults to 0.67
        :param weight: weight of the total rotation angle in path assessment, defaults to 1.
        :param filter_process_noise: Kalman filter process noise that controls smooth effect and filter phase delay, defaults to 0.08.
        """
        extend_length = 10
        data_extended = self._get_extended_data(extend_length)

        norm_vec = np.array([[0], [0], [1]])
        result = []
        calsour = self.data['calsour'].unique()
        accu = {sour: 0. for sour in calsour}
        root_node = Node(
            {'prune': False, 'position': -1, 'action': 0, 'angle': 0, 'total': 0, 'norm': np.zeros((3, 1))})
        z_lim = min_z
        ang_v = max_ang_v
        # initialize Kalman filter
        n = 3  # State vector size
        A = np.eye(n)  # State transition matrix
        H = np.eye(n)  # Observation matrix
        Q = np.eye(n) * filter_process_noise  # Process noise covariance
        R = np.eye(n) * 0.1  # Observation noise covariance
        x_hat = np.zeros((n, 1))  # Initial state estimate
        P = np.eye(n)  # Initial covariance
        for i in range(data_extended.index.size):
            calsour_this = data_extended.loc[i, 'calsour']

            root_node.current = recursion(data_extended, i, max_depth, norm_vec, accu, 0, ang_v, root_node, z_lim)
            root_node.plus = recursion(data_extended, i, max_depth, norm_vec, accu, 1, ang_v, root_node, z_lim)
            root_node.minus = recursion(data_extended, i, max_depth, norm_vec, accu, -1, ang_v, root_node, z_lim)
            norm_series = None
            if i > 5:
                norm_series = np.zeros((i, 4))
                norm_series[:, 0] = data_extended.loc[:i-1, 't']
                norm_series[:, 1:] = np.array(result)
                norm_series = norm_series[-6:, :]
            min_node, min_path = find_min_leaf(norm_series, data_extended['t'], i, root_node, norm_vec, weight, (max_depth, max_ang_v, min_z))

            if min_node is None:  # skip outliers (can't find any legal path)
                result.append(norm_vec.flatten())
                root_node = Node(
                    {'prune': False, 'position': i, 'action': 0, 'angle': 0, 'total': 0, 'norm': norm_vec})
                continue
            selected_next = min_path[1]
            accu[calsour_this] += selected_next['action'] * 2 * np.pi

            if i >= extend_length:
                if self.reverse:
                    original_t = -(data_extended.loc[i, 't'] - 2*self.data['t'].iloc[-1])
                else:
                    original_t = data_extended.loc[i, 't']
                accu_index = (self.original_data['t'] == original_t) & (self.original_data['calsour'] == calsour_this)
                self.accu_info.loc[accu_index] = accu[calsour_this]

            # Kalman filter for bias
            # Prediction step
            x_hat = A @ x_hat
            P = A @ P @ A.T + Q

            # Update step
            K = P @ H.T @ np.linalg.inv(H @ P @ H.T + R)
            x_hat = x_hat + K @ (selected_next['norm'] - H @ x_hat)
            P = (np.eye(n) - K @ H) @ P

            new_norm = x_hat
            result.append(new_norm.flatten())

            root_node = Node(selected_next)
            root_node.data['norm'] = new_norm
            norm_vec = new_norm

        self.mv_result = np.array(result[extend_length:])
        if self.reverse:
            self.mv_t = -(np.array(data_extended['t'])[extend_length:] - 2*self.data['t'].iloc[-1])
        else:
            self.mv_t = np.array(data_extended['t'])[extend_length:]

    def _mv_original(self, max_depth=4, max_ang_v=864., min_z=0.67, weight=1.):
        """
        calculate multiview phase plane with auto 2pi ambiguity detection
        :param max_depth: max depth of recursion, defaults to 4
        :param max_ang_v: max angular velocity of plane rotation, controls the threshold for pruning, defaults to 864.
        :param min_z: minimum z value of normal vector, defaults to 0.67
        :param weight: weight of the total rotation angle in path assessment, defaults to 1.
        """
        extend_length = 10
        data_extended = self._get_extended_data(extend_length)

        norm_vec = np.array([[0], [0], [1]])
        result = []
        calsour = self.data['calsour'].unique()
        accu = {sour: 0. for sour in calsour}
        root_node = Node(
            {'prune': False, 'position': -1, 'action': 0, 'angle': 0, 'total': 0, 'norm': np.zeros((3, 1))})
        z_lim = min_z
        ang_v = max_ang_v
        for i in range(data_extended.index.size):
            calsour_this = data_extended.loc[i, 'calsour']

            root_node.current = recursion(data_extended, i, max_depth, norm_vec, accu, 0, ang_v, root_node, z_lim)
            root_node.plus = recursion(data_extended, i, max_depth, norm_vec, accu, 1, ang_v, root_node, z_lim)
            root_node.minus = recursion(data_extended, i, max_depth, norm_vec, accu, -1, ang_v, root_node, z_lim)
            norm_series = None
            if i > 5:
                norm_series = np.zeros((i, 4))
                norm_series[:, 0] = data_extended.loc[:i - 1, 't']
                norm_series[:, 1:] = np.array(result)
                norm_series = norm_series[-6:, :]
            min_node, min_path = find_min_leaf(norm_series, data_extended['t'], i, root_node, norm_vec, weight, (max_depth, max_ang_v, min_z))

            if min_node is None:  # skip outliers (can't find any legal path)
                result.append(norm_vec.flatten())
                root_node = Node(
                    {'prune': False, 'position': i, 'action': 0, 'angle': 0, 'total': 0, 'norm': norm_vec})
                continue
            selected_next = min_path[1]
            accu[calsour_this] += selected_next['action'] * 2 * np.pi

            if i >= extend_length:
                if self.reverse:
                    original_t = -(data_extended.loc[i, 't'] - 2*self.data['t'].iloc[-1])
                else:
                    original_t = data_extended.loc[i, 't']
                accu_index = (self.original_data['t'] == original_t) & (self.original_data['calsour'] == calsour_this)
                self.accu_info.loc[accu_index] = accu[calsour_this]

            new_point = np.array([data_extended.loc[i, 'x'], data_extended.loc[i, 'y'],
                                  data_extended.loc[i, 'phase'] + accu[calsour_this]])

            new_norm, _, _ = rodrigues_rotation(norm_vec, new_point)
            new_norm = new_norm / np.linalg.norm(new_norm)
            result.append(new_norm.flatten())

            root_node = Node(selected_next)
            root_node.data['norm'] = new_norm
            norm_vec = new_norm

        self.mv_result = np.array(result[extend_length:])
        if self.reverse:
            self.mv_t = -(np.array(data_extended['t'])[extend_length:] - 2 * self.data['t'].iloc[-1])
        else:
            self.mv_t = np.array(data_extended['t'])[extend_length:]
