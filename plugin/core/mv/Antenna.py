"""
class for antennas
@Author: Jingdong Zhang
@DATE  : 2024/7/17
"""
import numpy as np
import pandas as pd
import copy
import matplotlib.pyplot as plt
# import scipy.interpolate as interp
# import pdb
from typing import List

from .Calibrator import Calibrator
from .plane import plane
from .Node import Node
from .recursion import recursion
from .find_min_leaf import find_min_leaf
# from .rodrigues_rotation import rodrigues_rotation


class Antenna:
    def __init__(self, antenna_id, antenna_name, data=None, calibrators: List[Calibrator]=None, if_freq=None, no_if=1):
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
        if data is None:
            data = pd.DataFrame(columns=['calsour', 'x', 'y', 't'])
        if calibrators is None:
            calibrators = []
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

        self.delay_if_ids = list(range(int(no_if)))
        self.if_freq = self._normalize_if_freq(if_freq, self.delay_if_ids)
        delay_adjust_columns = ['flag'] + [f'w{if_id}' for if_id in self.delay_if_ids]
        self.delay_adjust_info = pd.DataFrame(
            data=np.zeros(shape=(self.original_data.index.size, len(delay_adjust_columns))),
            columns=delay_adjust_columns,
        )
        dtype_map = {'flag': int}
        dtype_map.update({f'w{if_id}': int for if_id in self.delay_if_ids})
        self.delay_adjust_info = self.delay_adjust_info.astype(dtype_map)
        self.delay_t_flag_info = []
        self.delay_mv_result = None
        self.delay_mv_t = None

        # how the z axis is scaled for sMV
        max_xy = 0.
        for calibrator in self.secondary_calibrators:
            cal_max_xy = max(abs(calibrator.dx), abs(calibrator.dy))
            max_xy = max_xy if max_xy > cal_max_xy else cal_max_xy
        max_z = self.data[[f'd{if_id}' for if_id in self.delay_if_ids]].abs().max().max()
        self.z_scale = max_xy / max_z

        self.delay_scale = {
            if_id: float(self.if_freq.get(if_id, 1.0)) * 2e9 * np.pi
            for if_id in self.delay_if_ids
        }
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
    def delay_multiview(self, max_depth=4, max_ang_v=864., min_z=0.67, weight=1., kalman_factor=0.08, smo_half_window=None):
        """
        Solve total delay per IF independently, then average the solved target delay.
        """
        if self.original_data.empty:
            self.delay_mv_result = {}
            self.delay_mv_t = np.array([])
            self.delay_target_if = {}
            self.delay_average = np.array([])
            self.delay_average_t = np.array([])
            return
        self.update_delay_data()
        if self.data.empty or not self.delay_if_ids:
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
            data_extended_corrected = self._correct_delay_with_phase(data_extended, if_id)
            data_view = data_extended_corrected[['calsour', 'x', 'y', 't', 'total_delay']].copy(deep=True)
            data_view['total_delay'] = data_view['total_delay'] * self.z_scale  # for numerical stability

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
                freq = self.if_freq.get(if_id, 1.0) * 1e9 / self.z_scale  # here scale the freq
                root_node.current = recursion(data_view, i, max_depth, norm_vec, accu, 0, ang_v, root_node, freq, z_lim)
                root_node.plus = recursion(data_view, i, max_depth, norm_vec, accu, 1, ang_v, root_node, freq, z_lim)
                root_node.minus = recursion(data_view, i, max_depth, norm_vec, accu, -1, ang_v, root_node, freq, z_lim)
                norm_series = None
                if i > 8:
                    norm_series = np.zeros((i, 4))
                    norm_series[:, 0] = data_view.loc[:i - 1, 't']
                    norm_series[:, 1:] = np.array(result)
                    norm_series = norm_series[-9:, :]
                min_node, min_path = find_min_leaf(norm_series, data_view['t'], i, root_node, norm_vec, weight, (max_depth, max_ang_v, min_z))
                if min_node is None:
                    result.append(norm_vec.flatten())
                    root_node = Node({'prune': False, 'position': i, 'action': 0, 'angle': 0, 'total': 0, 'norm': norm_vec})
                    continue
                selected_next = min_path[1]
                accu[calsour_this] += selected_next['action'] / freq
                
                # update self.data
                if i >= extend_length and abs(selected_next['action']) > 1e-10:
                    self.delay_wrap([data_view.loc[i, 't']-1e-8, data_view.loc[data_view.index.size - 1, 't']+1e-8], [calsour_this], if_id, '+' if selected_next['action'] > 0 else '-')

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
        if self.reverse and self.data.index.size > 0:
            self.delay_mv_t = -(np.array(data_extended['t'])[extend_length:] - 2 * self.data['t'].iloc[-1])
        else:
            self.delay_mv_t = np.array(data_extended['t'])[extend_length:]
        self.delay_target_if = delay_target_if

        if smo_half_window is not None and smo_half_window > 0:
            self._lowpass_filter_delay(smo_half_window)

        self._refresh_delay_target_series()

    def delay_flag(self, timerange, calibrators, mode='flag'):
        flag_index = (self.original_data['t'] >= timerange[0]) & (self.original_data['t'] <= timerange[1])
        calibrator_index = self.original_data['calsour'].isin(calibrators)
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
        wrap_index = (self.original_data['t'] >= timerange[0]) & (self.original_data['t'] <= timerange[1])
        calibrator_index = self.original_data['calsour'].isin(calibrators)
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

    def plot_delay(self, target_pos, if_id=0, original_delay_id=None):
        self.target_pos = target_pos
        self._refresh_delay_target_series()
        markers = ['o', 'd', '^', 's', 'v', 'p', '*', '8', '<', '>']
        fig, ax = plt.subplots(1, 1, figsize=(8, 3))
        fig.subplots_adjust(left=0.05, right=0.95, top=0.98, bottom=0.12)

        if if_id in self.delay_target_if and self.delay_target_if[if_id].size > 0:
            ax.plot(self.delay_mv_t, self.delay_target_if[if_id] * 1e12, 'x', color='k', ls='', label='Target')

        for i, item in enumerate(self.secondary_calibrators):
            plot_data = self.data.copy(deep=True)
            plot_data = plot_data.loc[plot_data['calsour'] == item.id]
            plot_data = self._correct_delay_with_phase(plot_data, if_id)
            if not plot_data.empty:
                ax.plot(plot_data['t'], plot_data["total_delay"] * 1e12, ls='none', marker=markers[i], c=self.colors[i], label=item.name)

        flagged_index = self.delay_adjust_info['flag'] == 1
        flagged_data = self.original_data.loc[flagged_index].copy(deep=True)
        flagged_data.reset_index(drop=True, inplace=True)
        for i, item in enumerate(self.secondary_calibrators):
            plot_data = (flagged_data.copy(deep=True)).loc[flagged_data['calsour'] == item.id]
            plot_data = self._correct_delay_with_phase(plot_data, if_id)
            if not plot_data.empty:
                ax.plot(plot_data['t'], plot_data["total_delay"] * 1e12, ls='none', marker=markers[i], c=self.colors[i], alpha=0.3)

        # original delay
        if original_delay_id is not None:
            delay = self.original_data.loc[self.original_data['calsour'] == original_delay_id]
            if not delay.empty:
                ax.plot(delay['t'], delay[f"d{if_id}"] * 1e12, ls='-', marker=None, c="#888888", alpha=0.7, label=f"Ori. delay")

        ax.set_xlabel("time (day)")
        ax.set_ylabel("total delay (ps)")
        ax.set_title(f"IF{if_id + 1}")
        # ax.secondary_yaxis("right")
        scale = self.delay_scale.get(if_id)
        ax_r = ax.secondary_yaxis("right", functions=(lambda x: -x*scale/1e12, lambda x: -x/scale*1e12))
        ax_r.set_ylabel("corresponding phase (rad)", rotation=90)
        for item in self.delay_t_flag_info:
            y_lim = ax.get_ylim()
            ax.fill_betweenx(y_lim, item[0], item[1], color='#FFB6C1', alpha=0.15)
            ax.set_ylim(y_lim)
        ax.legend()
        return fig

    def save_delay(self, delay_adj_dir, delay_mv_dir):
        self._refresh_delay_target_series()
        self.delay_adjust_info.to_csv(delay_adj_dir, index=False)
        mv_table = pd.DataFrame({
            't': self.delay_average_t if self.delay_average_t is not None else [],
            'mbdelay': self.delay_average if self.delay_average is not None else [],
        })
        mv_table.to_csv(delay_mv_dir, index=False)
        # if self.delay_target_if:
        #     detail_path = delay_mv_dir.replace(".csv", "-IFS.csv")
        #     detail_table = pd.DataFrame({'t': self.delay_mv_t if self.delay_mv_t is not None else []})
        #     for if_id in self.delay_if_ids:
        #         if if_id in self.delay_target_if and self.delay_target_if[if_id].size > 0:
        #             detail_table[f'd{if_id}'] = self.delay_target_if[if_id]
        #     detail_table.to_csv(detail_path, index=False)

    def update_delay_data(self):
        self.data = self.original_data.copy(deep=True)
        if self.data.empty:
            return
        # for if_id in self.delay_if_ids:
        #     phase_col = f'p{if_id}'
        #     delay_col = f'd{if_id}'
        #     if phase_col in self.data.columns and delay_col in self.data.columns:
        #         freq_hz = self.if_freq.get(if_id, 1.0) * 1e9
        #         self.data[delay_col] = self.data[delay_col] - self.data[phase_col] / (2 * np.pi * freq_hz)
        for if_id in self.delay_if_ids:
            wrap_col = f'w{if_id}'
            delay_col = f'd{if_id}'
            if wrap_col in self.delay_adjust_info.columns and delay_col in self.data.columns:
                wrap_step = 1.0 / (self.if_freq.get(if_id, 1.0) * 1e9)
                self.data[delay_col] += self.delay_adjust_info[wrap_col].to_numpy() * wrap_step
        non_flagged_index = self.delay_adjust_info['flag'] == 0
        self.data = self.data.loc[non_flagged_index]
        self.data.reset_index(drop=True, inplace=True)

    def _get_extended_delay_data(self, extend_length=10):
        data_extended = self.data.copy(deep=True)
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
        mv_t = np.array(self.data.loc[:, 't'])
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
            refreshed[if_id] = np.array(
                [plane(*mv_res[i], *self.target_pos) / self.z_scale for i in range(mv_res.shape[0])]
            ) if mv_res.size > 0 else np.array([])
        self.delay_target_if = refreshed
        valid = [arr for arr in self.delay_target_if.values() if arr.size > 0]
        if valid:
            self.delay_average = np.mean(np.vstack(valid), axis=0)
            self.delay_average_t = np.array(self.delay_mv_t)
        else:
            self.delay_average = np.array([])
            self.delay_average_t = np.array([])
    
    def _correct_delay_with_phase(self, data_in, if_id):
        scale = self.delay_scale.get(if_id, 1.0)
        phase_of_delay = (-data_in[f"d{if_id}"] * scale + np.pi) % (2 * np.pi) - np.pi
        delta_phase = data_in[f"p{if_id}"] - phase_of_delay
        data_in["total_delay"] = data_in[f"d{if_id}"] - delta_phase / scale
        return data_in
