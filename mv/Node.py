"""
class for trident tree node
@Author: Jingdong Zhang
@DATE  : 2024/7/18
"""


class Node:
    def __init__(self, data, current=None, plus=None, minus=None):
        self.data = data
        self.current = current
        self.plus = plus
        self.minus = minus
