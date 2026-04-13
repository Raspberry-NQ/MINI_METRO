# external_functions.py — 列车时间计算函数
import math

def countTrainRunningTime(station_a, station_b):
    """根据两站坐标计算运行时间"""
    dx = station_a.x - station_b.x
    dy = station_a.y - station_b.y
    distance = math.sqrt(dx * dx + dy * dy)
    return max(1, int(distance / 100 * 3))

def countTrainBoardingTime(station):
    """上车时间，与站内乘客数成正比"""
    return 1 + len(station.passenger_list)

def countTrainAlightingTime(train):
    """下车时间，与车厢内乘客数成正比"""
    total = sum(len(c.passenger_list) for c in train.carriageList)
    return 1 + total

def countTrainIdleTime():
    """待命时间"""
    return 1

def countTrainShuntingime(origin_line, target_line):
    """调车时间"""
    return 2
