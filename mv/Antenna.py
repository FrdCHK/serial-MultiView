"""
class for antennas
@Author: Jingdong Zhang
@DATE  : 2024/7/17
"""
import numpy as np
import pandas as pd
import copy
import matplotlib.pyplot as plt

import mv


class Antenna:
    def __init__(self, antenna_id, antenna_name, data, calibrators):
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
        self.mv_result = None
        self.mv_t = None
        # record accumulated wrap during auto mv procedure
        self.accu_info = pd.DataFrame(data=np.zeros(shape=(self.original_data.index.size, 1)),
                                      columns=['accu']).astype({'accu': float})
        self.accu_data = None  # data with flag+wrap+accu adjustment

        self.target_pos = None

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
        if kalman_factor > 0:
            self._mv_kalman(max_depth, max_ang_v, min_z, weight, kalman_factor)
        else:
            self._mv_original(max_depth, max_ang_v, min_z, weight)

        if smo_half_window > 0:
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
        root.rerun()

    def plot_normal_vector(self):
        fig, ax = plt.subplots(1, 1, figsize=(8, 4))
        fig.subplots_adjust(left=0.07, right=0.98, top=0.98, bottom=0.1)
        for i in range(self.mv_result.shape[1]):
            ax.plot(self.mv_t, self.mv_result[:, i], label=chr(120 + i))
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

        fig, ax = plt.subplots(1, 1, figsize=(8, 3))
        fig.subplots_adjust(left=0.06, right=0.99, top=0.98, bottom=0.1)

        mv_target_phase = []
        for i in range(self.mv_result.shape[0]):
            mv_target_phase.append(mv.plane(*self.mv_result[i], *self.target_pos))
        mv_target_phase = np.array(mv_target_phase)
        mv_target_phase_wrap = (mv_target_phase + np.pi) % (2 * np.pi) - np.pi
        if ylim:
            ax.plot(self.mv_t, mv_target_phase_wrap, 'x', color='k', ls='', label='Target')
        else:
            ax.plot(self.mv_t, mv_target_phase, 'x', color='#222222', alpha=0.6, ls='', label='Target')

        for item in self.secondary_calibrators:
            if ylim:
                plot_data = self.original_data.copy(deep=True)
                non_flagged_index = self.adjust_info['flag'] == 0
                plot_data = plot_data.loc[non_flagged_index]
                plot_data = plot_data.loc[plot_data['calsour'] == item.id]
                ax.plot(plot_data['t'], plot_data['phase'], '.', label=item.name)
            else:
                plot_data = self.accu_data.loc[self.accu_data['calsour'] == item.id]
                ax.plot(plot_data['t'], plot_data['phase'], '.', label=item.name)

        flagged_index = self.adjust_info['flag'] == 1
        flagged_data = self.original_data.loc[flagged_index].copy(deep=True)
        flagged_data.reset_index(drop=True, inplace=True)
        for i, item in enumerate(self.secondary_calibrators):
            plot_data = flagged_data.loc[flagged_data['calsour'] == item.id]
            if not plot_data.empty:
                ax.plot(plot_data['t'], plot_data['phase'], '.', c=self.colors[i], alpha=0.3)

        ax.set_xlabel("time (day)")
        ax.set_ylabel("phase")

        if ylim:
            y_max = np.pi
            y_min = -np.pi
            ax.set_ylim([y_min, y_max])
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
            mv_target_phase.append(mv.plane(*self.mv_result[i], *self.target_pos))
        mv_target_phase = np.array(mv_target_phase)
        mv_target_phase_wrap = (mv_target_phase + np.pi) % (2 * np.pi) - np.pi
        mv_table = pd.DataFrame({'t': self.mv_t, 'phase': mv_target_phase_wrap})
        mv_table.to_csv(mv_dir, index=False)

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

    def _get_extended_data(self, extend_length=10):
        """
        extend a small segment at the beginning of the time series using a reversed segment
        :param extend_length: length of the extended part of the time series, defaults to 10
        :return: extended time series
        """
        data_extended = self.data.copy(deep=True)
        data_rev = data_extended.iloc[::-1, :]
        t = data_extended['t'].copy(deep=True)
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
        :param weight: weight of the total rotation angle in recursion, defaults to 1.
        :param filter_process_noise: Kalman filter process noise that controls smooth effect and filter phase delay, defaults to 0.08.
        """
        extend_length = 10
        data_extended = self._get_extended_data(extend_length)

        norm_vec = np.array([[0], [0], [1]])
        result = []
        calsour = self.data['calsour'].unique()
        accu = {sour: 0. for sour in calsour}
        root_node = mv.Node(
            {'prune': False, 'position': -1, 'action': 0, 'angle': 0, 'total': 0, 'norm': np.zeros((3, 1))})
        z_lim = min_z
        ang_v = max_ang_v
        # initialize Kalman filter
        n = 3  # 状态向量维度
        A = np.eye(n)  # 状态转移矩阵
        H = np.eye(n)  # 观测矩阵
        Q = np.eye(n) * filter_process_noise  # 过程噪声协方差
        R = np.eye(n) * 0.1  # 观测噪声协方差
        x_hat = np.zeros((n, 1))  # 初始状态估计
        P = np.eye(n)  # 初始协方差矩阵
        for i in range(data_extended.index.size):
            calsour_this = data_extended.loc[i, 'calsour']

            root_node.current = mv.recursion(data_extended, i, max_depth, norm_vec, accu, 0, ang_v, root_node, z_lim)
            root_node.plus = mv.recursion(data_extended, i, max_depth, norm_vec, accu, 1, ang_v, root_node, z_lim)
            root_node.minus = mv.recursion(data_extended, i, max_depth, norm_vec, accu, -1, ang_v, root_node, z_lim)
            min_node, min_path = mv.find_min_leaf(root_node, norm_vec, weight)

            if min_node is None:  # skip outliers (can't find any legal path)
                result.append(norm_vec.flatten())
                root_node = mv.Node(
                    {'prune': False, 'position': i, 'action': 0, 'angle': 0, 'total': 0, 'norm': norm_vec})
                continue
            selected_next = min_path[1]
            accu[calsour_this] += selected_next['action'] * 2 * np.pi

            if i >= extend_length:
                accu_index = (self.original_data['t'] == data_extended.loc[i, 't']) & (self.original_data['calsour'] == calsour_this)
                self.accu_info.loc[accu_index] = accu[calsour_this]

            # Kalman filter for bias
            # 预测步骤
            x_hat = A @ x_hat
            P = A @ P @ A.T + Q

            # 更新步骤
            K = P @ H.T @ np.linalg.inv(H @ P @ H.T + R)
            x_hat = x_hat + K @ (selected_next['norm'] - H @ x_hat)
            P = (np.eye(n) - K @ H) @ P

            new_norm = x_hat
            result.append(new_norm.flatten())

            root_node = mv.Node(selected_next)
            root_node.data['norm'] = new_norm
            norm_vec = new_norm

        self.mv_result = np.array(result[extend_length:])
        self.mv_t = np.array(data_extended['t'])[extend_length:]

    def _mv_original(self, max_depth=4, max_ang_v=864., min_z=0.67, weight=1.):
        """
        calculate multiview phase plane with auto 2pi ambiguity detection
        :param max_depth: max depth of recursion, defaults to 4
        :param max_ang_v: max angular velocity of plane rotation, controls the threshold for pruning, defaults to 864.
        :param min_z: minimum z value of normal vector, defaults to 0.67
        :param weight: weight of the total rotation angle in recursion, defaults to 1.
        """
        extend_length = 10
        data_extended = self._get_extended_data(extend_length)

        norm_vec = np.array([[0], [0], [1]])
        result = []
        calsour = self.data['calsour'].unique()
        accu = {sour: 0. for sour in calsour}
        root_node = mv.Node(
            {'prune': False, 'position': -1, 'action': 0, 'angle': 0, 'total': 0, 'norm': np.zeros((3, 1))})
        z_lim = min_z
        ang_v = max_ang_v
        for i in range(data_extended.index.size):
            calsour_this = data_extended.loc[i, 'calsour']

            root_node.current = mv.recursion(data_extended, i, max_depth, norm_vec, accu, 0, ang_v, root_node, z_lim)
            root_node.plus = mv.recursion(data_extended, i, max_depth, norm_vec, accu, 1, ang_v, root_node, z_lim)
            root_node.minus = mv.recursion(data_extended, i, max_depth, norm_vec, accu, -1, ang_v, root_node, z_lim)
            min_node, min_path = mv.find_min_leaf(root_node, norm_vec, weight)

            if min_node is None:  # skip outliers (can't find any legal path)
                result.append(norm_vec.flatten())
                root_node = mv.Node(
                    {'prune': False, 'position': i, 'action': 0, 'angle': 0, 'total': 0, 'norm': norm_vec})
                continue
            selected_next = min_path[1]
            accu[calsour_this] += selected_next['action'] * 2 * np.pi

            if i >= extend_length:
                accu_index = (self.original_data['t'] == data_extended.loc[i, 't']) & (self.original_data['calsour'] == calsour_this)
                self.accu_info.loc[accu_index] = accu[calsour_this]

            new_point = np.array([data_extended.loc[i, 'x'], data_extended.loc[i, 'y'],
                                  data_extended.loc[i, 'phase'] + accu[calsour_this]])

            new_norm, _, _ = mv.rodrigues_rotation(norm_vec, new_point)
            new_norm = new_norm / np.linalg.norm(new_norm)
            result.append(new_norm.flatten())

            root_node = mv.Node(selected_next)
            root_node.data['norm'] = new_norm
            norm_vec = new_norm

        self.mv_result = np.array(result[extend_length:])
        self.mv_t = np.array(data_extended['t'])[extend_length:]
