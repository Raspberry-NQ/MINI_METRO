# external_functions.py — 列车各类时间计算的独立函数
# 支持传入 GameConfig 覆盖默认值；不传 config 时保持原有默认行为


def countTrainRunningTime(sta, stb, config=None):
    """计算两站之间运行时间（基于距离）"""
    speed = config.train_running_speed if config else 1.0
    x1, x2 = sta.x, stb.x
    y1, y2 = sta.y, stb.y
    d = round(((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5)
    return max(1, round(d * speed))


def countTrainBoardingTime(station, config=None):
    """计算上客时间"""
    base = config.boarding_base_time if config else 5
    per_p = config.boarding_per_passenger if config else 5
    return base + station.passengerNm * per_p


def countTrainAlightingTime(train, config=None):
    """计算落客时间"""
    base = config.alighting_base_time if config else 5
    per_p = config.alighting_per_passenger if config else 5
    ticks = base
    for carriage in train.carriageList:
        ticks += carriage.currentNum * per_p
    return ticks


def countTrainIdleTime(config=None):
    """空闲状态持续时间"""
    return config.idle_time if config else 5


def countTrainShuntingime(lineA, lineB, config=None):
    """调车时间"""
    if lineA is None or lineB is None:
        t = config.shunting_no_line_time if config else 20
    elif lineA == lineB:
        t = config.shunting_same_line_time if config else 10
    else:
        t = config.shunting_diff_line_time if config else 20
    return t
