# external_functions.py
# 列车各类时间计算的独立函数


def countTrainRunningTime(sta, stb):
    """计算两站之间运行时间（基于距离）"""
    x1 = sta.x
    x2 = stb.x
    y1 = sta.y
    y2 = stb.y
    d = round(((x1 - x2) ** 2 + (y1 - y2) ** 2) ** (1 / 2))
    return d


def countTrainBoardingTime(station):
    """计算上客时间"""
    ticks = 5
    ticks += station.passengerNm * 5
    return ticks


def countTrainAlightingTime(train):
    """计算落客时间"""
    ticks = 5
    for carriage in train.carriageList:
        ticks += carriage.currentNum * 5
    return ticks


def countTrainIdleTime():
    """空闲状态持续时间"""
    return 5


def countTrainShuntingime(lineA, lineB):
    """调车时间"""
    if lineA is None or lineB is None:
        return 20
    if lineA == lineB:
        return 10
    return 20
