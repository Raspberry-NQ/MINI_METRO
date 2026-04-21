# game_config.py — 集中管理所有可调游戏参数

from station import (
    CATEGORY_RESIDENTIAL, CATEGORY_COMMERCIAL, CATEGORY_OFFICE,
    CATEGORY_HOSPITAL, CATEGORY_SCENIC, CATEGORY_SCHOOL,
    CATEGORY_SHAPE_MAP, ALL_CATEGORIES,
)


class GameConfig:
    """游戏配置，所有数值均可调整"""

    def __init__(self):
        # ---- 拥堵 ----
        self.overcrowd_limit = 15  # 站点人数超过此值则游戏结束

        # ---- 站点类别 ----
        self.all_categories = list(ALL_CATEGORIES)
        self.category_shape_map = dict(CATEGORY_SHAPE_MAP)

        # 城市布局参数
        self.city_station_count = 20       # 初始站点数量
        self.city_x_range = (-400, 400)    # 城市 x 范围
        self.city_y_range = (-300, 300)    # 城市 y 范围
        self.city_min_distance = 50        # 同类别站点间最小距离
        self.city_cluster_radius = 180     # 同类站点的聚集半径
        self.city_cluster_count_ranges = {
            # 每个类别在初始城市中生成的站点数范围 (min, max)
            CATEGORY_RESIDENTIAL: (5, 7),
            CATEGORY_COMMERCIAL: (3, 4),
            CATEGORY_OFFICE: (3, 5),
            CATEGORY_HOSPITAL: (1, 2),
            CATEGORY_SCENIC: (1, 3),
            CATEGORY_SCHOOL: (2, 3),
        }
        # 类别聚集中心（世界坐标），用于生成城市结构
        # None 表示随机生成
        self.city_cluster_centers = None

        # 动态站点生成（淡化）
        self.station_spawn_interval = 200      # 大幅降低生成频率
        self.station_spawn_chance = 0.3        # 降低生成概率
        self.station_type_list = list(CATEGORY_SHAPE_MAP.values())
        self.station_x_range = self.city_x_range
        self.station_y_range = self.city_y_range
        self.station_min_distance = self.city_min_distance
        self.station_max_count = 25            # 最大站点数量（适度增长）

        # ---- 乘客生成（日调度模式） ----
        # 一天 = day_length ticks
        self.day_length = 300                   # 一天对应 300 ticks
        # 时段定义: [(起始tick比例, 结束tick比例, 时段名称), ...]
        # 0.0=午夜, 0.25=6:00, 0.5=正午, 0.75=18:00
        self.daily_periods = [
            (0.00, 0.20, "night"),         # 午夜-5点: 夜间低峰
            (0.20, 0.35, "morning_rush"),  # 5点-8.4点: 早高峰
            (0.35, 0.50, "morning"),       # 8.4点-12点: 上午
            (0.50, 0.60, "midday"),        # 12点-14.4点: 午间
            (0.60, 0.75, "evening_rush"),  # 14.4点-18点: 晚高峰
            (0.75, 0.88, "evening"),       # 18点-21.1点: 晚间
            (0.88, 1.00, "late_night"),    # 21.1点-午夜: 深夜
        ]

        # O-D 流量模式: (origin_category, dest_category, period, 相对权重)
        # 权重越高，该时段该 O-D 对生成乘客的概率越大
        self.od_flow_patterns = [
            # 早高峰: 居民区→办公区/学校
            (CATEGORY_RESIDENTIAL, CATEGORY_OFFICE, "morning_rush", 10),
            (CATEGORY_RESIDENTIAL, CATEGORY_SCHOOL, "morning_rush", 6),
            (CATEGORY_RESIDENTIAL, CATEGORY_COMMERCIAL, "morning_rush", 2),
            (CATEGORY_RESIDENTIAL, CATEGORY_HOSPITAL, "morning_rush", 1),

            # 上午: 少量办公→商业, 医院→居民
            (CATEGORY_OFFICE, CATEGORY_COMMERCIAL, "morning", 3),
            (CATEGORY_HOSPITAL, CATEGORY_RESIDENTIAL, "morning", 2),
            (CATEGORY_SCHOOL, CATEGORY_COMMERCIAL, "morning", 1),

            # 午间: 办公→商业(午餐), 学校→商业
            (CATEGORY_OFFICE, CATEGORY_COMMERCIAL, "midday", 8),
            (CATEGORY_SCHOOL, CATEGORY_COMMERCIAL, "midday", 3),
            (CATEGORY_RESIDENTIAL, CATEGORY_COMMERCIAL, "midday", 2),
            (CATEGORY_RESIDENTIAL, CATEGORY_HOSPITAL, "midday", 1),

            # 晚高峰: 办公→居民区, 学校→居民区, 景区→居民
            (CATEGORY_OFFICE, CATEGORY_RESIDENTIAL, "evening_rush", 10),
            (CATEGORY_SCHOOL, CATEGORY_RESIDENTIAL, "evening_rush", 5),
            (CATEGORY_COMMERCIAL, CATEGORY_RESIDENTIAL, "evening_rush", 3),
            (CATEGORY_SCENIC, CATEGORY_RESIDENTIAL, "evening_rush", 2),
            (CATEGORY_OFFICE, CATEGORY_COMMERCIAL, "evening_rush", 2),

            # 晚间: 商业→居民, 景区→居民
            (CATEGORY_COMMERCIAL, CATEGORY_RESIDENTIAL, "evening", 5),
            (CATEGORY_SCENIC, CATEGORY_RESIDENTIAL, "evening", 3),
            (CATEGORY_RESIDENTIAL, CATEGORY_SCENIC, "evening", 2),
            (CATEGORY_COMMERCIAL, CATEGORY_HOSPITAL, "evening", 1),

            # 深夜: 少量各类→居民
            (CATEGORY_COMMERCIAL, CATEGORY_RESIDENTIAL, "late_night", 3),
            (CATEGORY_SCENIC, CATEGORY_RESIDENTIAL, "late_night", 2),

            # 夜间: 极少量
            (CATEGORY_RESIDENTIAL, CATEGORY_HOSPITAL, "night", 1),
        ]

        # 每时段基础生成率 ( passengers per tick per active O-D pair )
        self.period_base_spawn_rate = {
            "night": 0.02,
            "morning_rush": 0.15,
            "morning": 0.06,
            "midday": 0.08,
            "evening_rush": 0.15,
            "evening": 0.07,
            "late_night": 0.03,
        }

        # 兼容旧接口的参数（不再作为主要生成逻辑）
        self.passenger_spawn_base_chance = 0.08
        self.passenger_spawn_growth = 0.002
        self.passenger_spawn_max_chance = 0.4
        self.passenger_extra_spawn_start_tick = 50
        self.passenger_extra_spawn_ratio = 0.5

        # ---- 资源增长 ----
        # 格式: [(间隔tick, 资源类型, 数量), ...]
        self.resource_growth_schedule = [
            (30, "carriage", 1),
            (60, "train", 1),
            (100, "line", 1),
        ]
        self.max_lines = 7
        self.max_trains = 15
        self.max_carriages = 30

        # ---- 列车/车厢 ----
        self.carriage_capacity = 6
        self.default_carriages_per_train = 1

        # ---- 时间计算 ----
        self.train_running_speed = 1.0
        self.boarding_base_time = 5
        self.boarding_per_passenger = 5
        self.alighting_base_time = 5
        self.alighting_per_passenger = 5
        self.idle_time = 5
        self.shunting_same_line_time = 10
        self.shunting_diff_line_time = 20
        self.shunting_no_line_time = 20
        self.train_wait_time = 3  # 前方站被占用时，等待重试间隔

        # ---- 乘客 ----
        self.passenger_transfer_penalty = 5

        # ---- 可视化 ----
        self.window_width = 1200
        self.window_height = 800
        self.fps = 30
        self.sim_speed = 5
        self.station_radius = 18
        self.train_size = 10
        self.passenger_size = 4
        self.line_width = 6
        self.hud_font_size = 16
        self.bg_color = (245, 245, 235)
        self.station_color = (60, 60, 60)
        self.station_fill = (255, 255, 255)
        self.text_color = (40, 40, 40)
        self.overcrowd_color = (220, 50, 50)
        self.line_colors = [
            (220, 60, 60),     # 红
            (60, 120, 220),    # 蓝
            (60, 180, 60),     # 绿
            (220, 180, 40),    # 黄
            (160, 60, 200),    # 紫
            (220, 130, 40),    # 橙
            (40, 180, 180),    # 青
        ]

        # 类别对应的底色 (用于站点背景色区分)
        self.category_colors = {
            CATEGORY_RESIDENTIAL: (180, 210, 255),   # 淡蓝
            CATEGORY_COMMERCIAL: (255, 220, 180),    # 淡橙
            CATEGORY_OFFICE: (200, 200, 220),         # 淡灰蓝
            CATEGORY_HOSPITAL: (255, 200, 200),       # 淡红
            CATEGORY_SCENIC: (200, 240, 200),         # 淡绿
            CATEGORY_SCHOOL: (240, 230, 255),         # 淡紫
        }

        # 类别中文名 (用于 HUD)
        self.category_labels = {
            CATEGORY_RESIDENTIAL: "居民区",
            CATEGORY_COMMERCIAL: "商业区",
            CATEGORY_OFFICE: "办公区",
            CATEGORY_HOSPITAL: "医院",
            CATEGORY_SCENIC: "景区",
            CATEGORY_SCHOOL: "学校",
        }

    def get_current_period(self, tick):
        """根据 tick 返回当前时段名称"""
        time_in_day = (tick % self.day_length) / self.day_length
        for start, end, period_name in self.daily_periods:
            if start <= time_in_day < end:
                return period_name
        return "night"

    def get_od_weights(self, tick):
        """返回当前 tick 的活跃 O-D 权重列表
        Returns: [(origin_cat, dest_cat, weight), ...]
        """
        period = self.get_current_period(tick)
        result = []
        for origin, dest, p, weight in self.od_flow_patterns:
            if p == period:
                result.append((origin, dest, weight))
        return result

    def get_spawn_rate(self, tick):
        """返回当前 tick 的乘客生成率"""
        period = self.get_current_period(tick)
        return self.period_base_spawn_rate.get(period, 0.05)
