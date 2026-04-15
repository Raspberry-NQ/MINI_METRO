# game_config.py — 集中管理所有可调游戏参数


class GameConfig:
    """游戏配置，所有数值均可调整"""

    def __init__(self):
        # ---- 拥堵 ----
        self.overcrowd_limit = 15  # 站点人数超过此值则游戏结束

        # ---- 乘客生成 ----
        self.passenger_spawn_base_chance = 0.08    # 初始每 tick 生成乘客概率
        self.passenger_spawn_growth = 0.002        # 每 tick 概率增长量
        self.passenger_spawn_max_chance = 0.4       # 生成概率上限
        self.passenger_extra_spawn_start_tick = 50  # 从此 tick 开始额外生成
        self.passenger_extra_spawn_ratio = 0.5      # 额外生成概率 = 基础概率 * 此比例

        # ---- 动态站点生成 ----
        self.station_spawn_interval = 50        # 每 N tick 尝试生成一个新站点
        self.station_spawn_chance = 0.6          # 每次尝试的成功概率
        self.station_type_list = ["circle", "triangle", "square", "diamond", "star", "pentagon"]
        self.station_x_range = (0, 400)          # 站点 x 坐标范围
        self.station_y_range = (-400, 200)       # 站点 y 坐标范围
        self.station_min_distance = 80           # 新站点与已有站点的最小距离
        self.station_max_count = 20              # 最大站点数量

        # ---- 资源增长 ----
        # 格式: [(间隔tick, 资源类型, 数量), ...]
        # 资源类型: "train", "carriage", "line", "tunnel"
        self.resource_growth_schedule = [
            (30, "carriage", 1),
            (60, "train", 1),
            (100, "line", 1),
        ]
        self.max_lines = 7                # 最大线路数
        self.max_trains = 15              # 最大列车数
        self.max_carriages = 30           # 最大车厢数

        # ---- 列车/车厢 ----
        self.carriage_capacity = 6        # 车厢容量
        self.default_carriages_per_train = 1  # employTrain 时自动分配的车厢数

        # ---- 时间计算 ----
        self.train_running_speed = 1.0    # 行驶时间倍率
        self.boarding_base_time = 5       # 上客基础时间
        self.boarding_per_passenger = 5   # 每个乘客额外上客时间
        self.alighting_base_time = 5      # 落客基础时间
        self.alighting_per_passenger = 5  # 每个乘客额外落客时间
        self.idle_time = 5                # 空闲持续时间
        self.shunting_same_line_time = 10 # 同线路调车时间
        self.shunting_diff_line_time = 20 # 不同线路调车时间
        self.shunting_no_line_time = 20   # 无线路调车时间

        # ---- 乘客 ----
        self.passenger_default_patience = 100  # 乘客默认耐心值
        self.passenger_transfer_penalty = 5    # 换乘惩罚时间

        # ---- 可视化 ----
        self.window_width = 1200                # 窗口宽度
        self.window_height = 800                # 窗口高度
        self.fps = 30                           # 渲染帧率
        self.sim_speed = 5                      # 每帧模拟 tick 数（可调节）
        self.station_radius = 18                # 站点绘制半径
        self.train_size = 10                    # 列车绘制大小
        self.passenger_size = 4                 # 乘客绘制大小
        self.line_width = 6                     # 线路绘制宽度
        self.hud_font_size = 16                 # HUD 字体大小
        self.bg_color = (245, 245, 235)         # 背景色
        self.station_color = (60, 60, 60)       # 站点边框色
        self.station_fill = (255, 255, 255)     # 站点填充色
        self.text_color = (40, 40, 40)          # 文字颜色
        self.overcrowd_color = (220, 50, 50)    # 拥堵警告色
        self.line_colors = [                    # 线路颜色 (最多7条)
            (220, 60, 60),     # 红
            (60, 120, 220),    # 蓝
            (60, 180, 60),     # 绿
            (220, 180, 40),    # 黄
            (160, 60, 200),    # 紫
            (220, 130, 40),    # 橙
            (40, 180, 180),    # 青
        ]
