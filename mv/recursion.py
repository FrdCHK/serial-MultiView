"""
description
@Author: Jingdong Zhang
@DATE  : 2024/7/18
"""
import copy
import numpy as np

import mv


def recursion(data, position, depth_remain, norm_vec, accumulated_wrap, action, max_ang_v, parent, min_z=0.67):
    """
    Recursive function for locally minimal rotation angle in total
    :param data: input data of calibrators
    :param position: current index in data
    :param depth_remain: remaining recursion depth
    :param norm_vec: normal vector of phase plane
    :param accumulated_wrap: accumulated 2pi-wrap for each calibrator in the recursive path
    :param action: action to take: 1 +2pi, 0 +0, -1 -2pi
    :param max_ang_v: max angular velocity of the plane for pruning
    :param parent: parent node of the tree
    :param min_z: minimum z value of normal vector
    :return: this node
    """
    accu = copy.deepcopy(accumulated_wrap)
    calsour = data.loc[position, 'calsour']
    accu[calsour] += action * 2 * np.pi
    current_phase = data.loc[position, 'phase'] + accu[calsour]
    current_point = np.array([data.loc[position, 'x'], data.loc[position, 'y'], current_phase])
    current_norm, _, current_angle = mv.rodrigues_rotation(norm_vec, current_point)
    current_norm = current_norm / np.linalg.norm(current_norm)
    abs_angle = np.abs(current_angle)
    if current_norm[2, 0] < min_z:  # avoid the plane being too tilted
        new_node = mv.Node({'prune': True, 'position': position, 'action': action, 'angle': abs_angle,
                            'total': parent.data['total'] + abs_angle, 'norm': current_norm})
        return new_node
    if position > 0:  # prune the branch with angular velocity > max (excludes the first data point)
        ang_v = abs_angle / (data.loc[position, 't'] - data.loc[position-1, 't'])
        if ang_v > max_ang_v:
            new_node = mv.Node({'prune': True, 'position': position, 'action': action, 'angle': abs_angle,
                                'total': parent.data['total'] + abs_angle, 'norm': current_norm})
            return new_node
    else:
        abs_angle = 0
    new_node = mv.Node({'prune': False, 'position': position, 'action': action, 'angle': abs_angle,
                        'total': parent.data['total'] + abs_angle, 'norm': current_norm})
    if depth_remain > 1 and position < data.index.size - 1:
        new_node.current = recursion(data, position + 1, depth_remain - 1, current_norm, accu, 0, max_ang_v, new_node, min_z)
        new_node.plus = recursion(data, position + 1, depth_remain - 1, current_norm, accu, 1, max_ang_v, new_node, min_z)
        new_node.minus = recursion(data, position + 1, depth_remain - 1, current_norm, accu, -1, max_ang_v, new_node, min_z)
    return new_node
