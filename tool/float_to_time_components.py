"""
description
@Author: Jingdong Zhang
@DATE  : 2024/7/2
"""
import datetime


def float_to_time_components(float_days):
    time_delta = datetime.timedelta(days=float_days)
    days = time_delta.days
    seconds_in_day = time_delta.seconds
    hours = seconds_in_day // 3600
    minutes = (seconds_in_day % 3600) // 60
    seconds = seconds_in_day % 60
    return days, hours, minutes, seconds
