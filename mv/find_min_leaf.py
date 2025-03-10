"""
description
@Author: Jingdong Zhang
@DATE  : 2024/7/18
"""
import numpy as np

import tool


def find_min_leaf(norm_series, time_series, position, root, norm0, weight=1, thres_para=None):
    """
    find the leaf node with minimum total rotation angle
    :param norm_series: normal vector time series before this step
    :param time_series: series of time
    :param position: position in series
    :param root: root node
    :param norm0: normal vector of the root node
    :param weight: weight of the total rotation angle, defaults to 1.
    :param thres_para: parameters for outlier threshold (max_depth, max_ang_v, min_z), defaults to None.
    :return: the leaf node, path to the leaf node
    """
    if root is None or root.data['prune']:
        return None, None
    if root.current is None and root.plus is None and root.minus is None:
        return root, [root.data]
    current_min, current_path = find_min_leaf(norm_series, time_series, position+1, root.current, norm0, weight, thres_para)
    plus_min, plus_path = find_min_leaf(norm_series, time_series, position+1, root.plus, norm0, weight, thres_para)
    minus_min, minus_path = find_min_leaf(norm_series, time_series, position+1, root.minus, norm0, weight, thres_para)

    if norm_series is not None:
        predicted_norm = tool.predict(norm_series, time_series[position])
        norm = predicted_norm
    else:
        norm = norm0

    if thres_para is None:
        score_max = (1+2*10*weight)*3
    else:
        max_depth, max_ang_v, min_z = thres_para
        score_max = (1/(min_z+0.3)+max_depth*max_ang_v*1e-3*weight)*3

    # calculate the 'move', combining the total rotation angle and the angle between final/predicted normal vector
    if current_min is not None:
        current_ang = np.arccos((current_min.data['norm'].T @ norm) / (np.linalg.norm(current_min.data['norm']) * np.linalg.norm(norm)))[0, 0]
        # print(current_ang)
        # print(current_min.data['total'])
        current_score = current_ang + current_min.data['total'] * weight
        # 即使找到合法路径，但score过大的话也认定为outlier，并将xx_min置为none。需要考虑阈值如何设置？根据几个参数计算？
        # print(f"ang={current_ang:.1e}, tot={current_min.data['total']:.1e}, score={current_score:.1e}")
        if current_score > score_max:
            current_min = None

    if plus_min is not None:
        plus_ang = np.arccos((plus_min.data['norm'].T @ norm) / (np.linalg.norm(plus_min.data['norm']) * np.linalg.norm(norm)))[0, 0]
        plus_score = plus_ang + plus_min.data['total'] * weight
        # print(f"ang={plus_ang:.1e}, tot={plus_min.data['total']:.1e}, score={plus_score:.1e}")
        if plus_score > score_max:
            plus_min = None
    if minus_min is not None:
        minus_ang = np.arccos((minus_min.data['norm'].T @ norm) / (np.linalg.norm(minus_min.data['norm']) * np.linalg.norm(norm)))[0, 0]
        minus_score = minus_ang + minus_min.data['total'] * weight
        # print(f"ang={minus_ang:.1e}, tot={minus_min.data['total']:.1e}, score={minus_score:.1e}")
        if minus_score > score_max:
            minus_min = None

    if current_min is not None and plus_min is None and minus_min is None:
        return current_min, [root.data] + current_path
    elif current_min is None and plus_min is not None and minus_min is None:
        return plus_min, [root.data] + plus_path
    elif current_min is None and plus_min is None and minus_min is not None:
        return minus_min, [root.data] + minus_path
    elif current_min is not None and plus_min is not None and minus_min is None:
        if current_score <= plus_score:
            return current_min, [root.data] + current_path
        else:
            return plus_min, [root.data] + plus_path
    elif current_min is not None and plus_min is None and minus_min is not None:
        if current_score <= minus_score:
            return current_min, [root.data] + current_path
        else:
            return minus_min, [root.data] + minus_path
    elif current_min is None and plus_min is not None and minus_min is not None:
        if plus_score <= minus_score:
            return plus_min, [root.data] + plus_path
        else:
            return minus_min, [root.data] + minus_path
    elif current_min is None and plus_min is None and minus_min is None:
        return None, None
    else:
        cmp = np.array([current_score, plus_score, minus_score])
        min_index = np.argmin(cmp)
        if min_index == 0:
            return current_min, [root.data] + current_path
        elif min_index == 1:
            return plus_min, [root.data] + plus_path
        else:
            return minus_min, [root.data] + minus_path


# def find_min_leaf(root, norm0, weight):
#     """
#     find the leaf node with minimum total rotation angle
#     :param root: root node
#     :param norm0: normal vector of the root node
#     :param weight: weight of the total rotation angle
#     :return: the leaf node, path to the leaf node
#     """
#     if root is None or root.data['prune']:
#         return None, None
#     if root.current is None and root.plus is None and root.minus is None:
#         return root, [root.data]
#     current_min, current_path = find_min_leaf(root.current, norm0, weight)
#     plus_min, plus_path = find_min_leaf(root.plus, norm0, weight)
#     minus_min, minus_path = find_min_leaf(root.minus, norm0, weight)
#
#     # calculate the 'move', combining the total rotation angle and the angle between first/final normal vector
#     if current_min is not None:
#         current_ang = np.arccos((current_min.data['norm'].T @ norm0) / (np.linalg.norm(current_min.data['norm']) * np.linalg.norm(norm0)))[0, 0]
#         current_score = current_ang + current_min.data['total'] * weight
#     if plus_min is not None:
#         plus_ang = np.arccos((plus_min.data['norm'].T @ norm0) / (np.linalg.norm(plus_min.data['norm']) * np.linalg.norm(norm0)))[0, 0]
#         plus_score = plus_ang + plus_min.data['total'] * weight
#     if minus_min is not None:
#         minus_ang = np.arccos((minus_min.data['norm'].T @ norm0) / (np.linalg.norm(minus_min.data['norm']) * np.linalg.norm(norm0)))[0, 0]
#         minus_score = minus_ang + minus_min.data['total'] * weight
#
#     if current_min is not None and plus_min is None and minus_min is None:
#         return current_min, [root.data] + current_path
#     elif current_min is None and plus_min is not None and minus_min is None:
#         return plus_min, [root.data] + plus_path
#     elif current_min is None and plus_min is None and minus_min is not None:
#         return minus_min, [root.data] + minus_path
#     elif current_min is not None and plus_min is not None and minus_min is None:
#         if current_score <= plus_score:
#             return current_min, [root.data] + current_path
#         else:
#             return plus_min, [root.data] + plus_path
#     elif current_min is not None and plus_min is None and minus_min is not None:
#         if current_score <= minus_score:
#             return current_min, [root.data] + current_path
#         else:
#             return minus_min, [root.data] + minus_path
#     elif current_min is None and plus_min is not None and minus_min is not None:
#         if plus_score <= minus_score:
#             return plus_min, [root.data] + plus_path
#         else:
#             return minus_min, [root.data] + minus_path
#     elif current_min is None and plus_min is None and minus_min is None:
#         return None, None
#     else:
#         cmp = np.array([current_score, plus_score, minus_score])
#         min_index = np.argmin(cmp)
#         if min_index == 0:
#             return current_min, [root.data] + current_path
#         elif min_index == 1:
#             return plus_min, [root.data] + plus_path
#         else:
#             return minus_min, [root.data] + minus_path
