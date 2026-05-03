# external_functions.py — 列车时间计算模块
#
# 本文件提供列车各类时间计算的独立函数，支持传入 GameConfig 覆盖默认值；
# 不传 config 时保持原有默认行为。


def countTrainRunningTime(sta, stb, config=None):
    """计算两站之间运行时间（基于距离 + 基础时间）

    参数:
        sta: 起始站点对象
        stb: 目标站点对象
        config: 游戏配置对象，默认为None

    返回:
        int: 运行时间（tick数）
    """
    speed = config.train_running_speed if config else 1.0
    base = config.running_base_time if config else 0
    x1, x2 = sta.x, stb.x
    y1, y2 = sta.y, stb.y
    d = round(((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5)
    return base + max(1, round(d * speed))


def countTrainBoardingTime(station, config=None):
    """计算上客时间

    参数:
        station: 站点对象
        config: 游戏配置对象，默认为None

    返回:
        int: 上客时间（tick数）
    """
    base = config.boarding_base_time if config else 5
    per_p = config.boarding_per_passenger if config else 5
    return base + station.passengerNm * per_p


def countTrainAlightingTime(train, config=None):
    """计算落客时间

    参数:
        train: 列车对象
        config: 游戏配置对象，默认为None

    返回:
        int: 落客时间（tick数）
    """
    base = config.alighting_base_time if config else 5
    per_p = config.alighting_per_passenger if config else 5
    ticks = base
    for carriage in train.carriageList:
        ticks += carriage.currentNum * per_p
    return ticks


def countTrainIdleTime(config=None):
    """计算空闲状态持续时间

    参数:
        config: 游戏配置对象，默认为None

    返回:
        int: 空闲时间（tick数）
    """
    return config.idle_time if config else 5


def countTrainShuntingime(lineA, lineB, config=None):
    """计算调车时间

    参数:
        lineA: 原线路对象
        lineB: 目标线路对象
        config: 游戏配置对象，默认为None

    返回:
        int: 调车时间（tick数）
    """
    if lineA is None or lineB is None:
        t = config.shunting_no_line_time if config else 20
    elif lineA == lineB:
        t = config.shunting_same_line_time if config else 10
    else:
        t = config.shunting_diff_line_time if config else 20
    return t
