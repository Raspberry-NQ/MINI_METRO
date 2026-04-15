# run.py — 运行迷你地铁世界
import random
from station import station, CATEGORY_SHAPE_MAP
from line import MetroLine
from trainInventory import TrainInventory
from passengerManager import PassengerManager
from passenger import Passenger
from game_config import GameConfig
from city_generator import generate_city

OVERCROWD_LIMIT = 15  # 默认值，实际由 config 控制


# ============================================================
# 构建世界
# ============================================================
class MetroWorld:
    def __init__(self, config=None):
        self.config = config or GameConfig()
        self.stations = []
        self.metroLine = []
        self.pm = None
        self.ti = None
        self.tick = 0
        self._next_station_id = 0
        self._next_line_id = 0
        self._resource_accumulator = {}  # {资源类型: 累计获得数量}
        self.game_over = False

    # ============================================================
    # 世界初始化
    # ============================================================

    def setup(self):
        """生成城市站点，不预设线路 — AI/玩家需要自行布线"""
        self.pm = PassengerManager(self)
        self.ti = TrainInventory(self.pm, self.config)

        # 用城市生成器创建站点
        self.stations = generate_city(self.config, id_start=0)
        self._next_station_id = max((s.id for s in self.stations), default=0)

        # 初始资源
        for _ in range(5):
            self.ti.addTrain()
        for _ in range(10):
            self.ti.addCarriage()

        self._rebuild_all_connections()
        self._print_init_summary()

    # 保留旧的 setup 方法名兼容，但标记为旧版
    def setup_legacy(self):
        """旧版: 两条预设线路, 共享换乘站"""
        self.pm = PassengerManager(self)
        self.ti = TrainInventory(self.pm, self.config)

        # 线路1 站点: A(0) - B(1) - C(换乘) - D(3)
        sA = self._make_station("circle", 0, 0)
        sB = self._make_station("triangle", 100, 0)
        sC = self._make_station("square", 200, 0)   # 换乘站
        sD = self._make_station("diamond", 300, 0)

        # 线路2 站点: E(0) - C(换乘) - F(2)
        sE = self._make_station("star", 200, -150)
        sF = self._make_station("pentagon", 200, -300)

        self.stations = [sA, sB, sC, sD, sE, sF]

        line1 = MetroLine(self._alloc_line_id(), [sA, sB, sC, sD])
        line2 = MetroLine(self._alloc_line_id(), [sE, sC, sF])
        self.metroLine = [line1, line2]

        # 初始资源
        for _ in range(4):
            self.ti.addTrain()
        for _ in range(8):
            self.ti.addCarriage()

        # 线路1: 列车1从起点正向, 列车2从终点反向
        self.ti.employTrain(line1, sA, True)
        self.ti.trainBusyList[-1].connectCarriage(self.ti.getFreeCarriage())

        self.ti.employTrain(line1, sD, False)
        self.ti.trainBusyList[-1].connectCarriage(self.ti.getFreeCarriage())

        # 线路2: 列车3从起点正向, 列车4从终点反向
        self.ti.employTrain(line2, sE, True)
        self.ti.trainBusyList[-1].connectCarriage(self.ti.getFreeCarriage())

        self.ti.employTrain(line2, sF, False)
        self.ti.trainBusyList[-1].connectCarriage(self.ti.getFreeCarriage())

        self._rebuild_all_connections()
        self._print_init_summary()

    def _make_station(self, stype, x, y, category=None):
        self._next_station_id += 1
        return station(self._next_station_id, stype, x, y, category=category)

    def _alloc_line_id(self):
        self._next_line_id += 1
        return self._next_line_id

    def _rebuild_all_connections(self):
        """重建所有站点的 connections"""
        for s in self.stations:
            s.connections = []
        for line in self.metroLine:
            line._rebuild_connections()

    def _print_init_summary(self):
        print("=" * 60)
        print("世界初始化完成")
        print(f"站点数: {len(self.stations)}")
        print(f"线路数: {len(self.metroLine)}")
        print(f"列车数: {len(self.ti.trainBusyList)}")

        # 按类别汇总站点
        from station import CATEGORY_LABEL_CN
        cat_count = {}
        for s in self.stations:
            cat = s.category or "unknown"
            cat_count[cat] = cat_count.get(cat, 0) + 1
        for cat, cnt in cat_count.items():
            label = CATEGORY_LABEL_CN.get(cat, cat)
            print(f"  {label}: {cnt} 个站点")

        for line in self.metroLine:
            line.printLine()
        print("=" * 60)

    # ============================================================
    # 玩家 / AI 操作接口
    # ============================================================

    def playerTrainShunt(self, train_obj, goalLine, direction, station_obj):
        """调车：将列车从当前线路调到目标线路

        Args:
            train_obj: 要调的列车
            goalLine: 目标线路
            direction: 在目标线路上的方向 (True=正向, False=反向)
            station_obj: 调车到达的目标站点
        Returns:
            True 成功, False 失败
        """
        if self.game_over:
            return False
        try:
            self.ti.shuntTrain(train_obj, goalLine, direction, station_obj)
            self.pm.route_planner.invalidate_cache()
            return True
        except Exception as e:
            print(f"调车失败: {e}")
            return False

    def playerLineExtension(self, line, station_obj, append=True):
        """延伸线路：在线路末端添加站点

        Args:
            line: 要延伸的线路
            station_obj: 要添加的站点
            append: True=末端延伸, False=起点延伸
        Returns:
            True 成功, False 失败
        """
        if self.game_over:
            return False
        if len(line.stationList) == 0:
            line.addStation(station_obj)
        elif append:
            line.addStation(station_obj)
        else:
            line.insertStation(0, station_obj)

        if station_obj not in self.stations:
            self.stations.append(station_obj)

        self._rebuild_all_connections()
        self.pm.route_planner.invalidate_cache()
        return True

    def playerLineInsert(self, line, index, station_obj):
        """在线路中间插入站点

        Args:
            line: 要修改的线路
            index: 插入位置（0-based）
            station_obj: 要插入的站点
        Returns:
            True 成功, False 失败
        """
        if self.game_over:
            return False
        line.insertStation(index, station_obj)
        if station_obj not in self.stations:
            self.stations.append(station_obj)

        self._rebuild_all_connections()
        self.pm.route_planner.invalidate_cache()
        return True

    def playerNewLine(self, station_list):
        """创建新线路

        Args:
            station_list: 线路站点列表
        Returns:
            新线路对象, 或 None（线路数已达上限）
        """
        if self.game_over:
            return None
        if len(self.metroLine) >= self.config.max_lines:
            print("线路数已达上限，无法创建新线路")
            return None

        new_line = MetroLine(self._alloc_line_id(), station_list)
        self.metroLine.append(new_line)

        for s in station_list:
            if s not in self.stations:
                self.stations.append(s)

        self._rebuild_all_connections()
        self.pm.route_planner.invalidate_cache()
        return new_line

    def playerEmployTrain(self, line, station_obj, direction=True):
        """从车库分配列车到线路

        Returns:
            列车对象, 或 None（资源不足）
        """
        if self.game_over:
            return None
        try:
            self.ti.employTrain(line, station_obj, direction)
            return self.ti.trainBusyList[-1]
        except Exception as e:
            print(f"分配列车失败: {e}")
            return None

    def playerConnectCarriage(self, train_obj):
        """给列车联挂一节车厢

        Returns:
            车厢对象, 或 None（资源不足）
        """
        if self.game_over:
            return None
        try:
            c = self.ti.getFreeCarriage()
            train_obj.connectCarriage(c)
            return c
        except Exception as e:
            print(f"联挂车厢失败: {e}")
            return None

    # ============================================================
    # 游戏状态观察接口 (供 AI 使用)
    # ============================================================

    def getGameState(self):
        """返回标准化的游戏状态快照"""
        cfg = self.config
        period = cfg.get_current_period(self.tick)
        od_weights = cfg.get_od_weights(self.tick)

        return {
            "tick": self.tick,
            "game_over": self.game_over,

            # 时间信息
            "time_of_day": {
                "tick_in_day": self.tick % cfg.day_length,
                "day_length": cfg.day_length,
                "period": period,
                "active_od_patterns": [
                    {"origin": o, "destination": d, "weight": w}
                    for o, d, w in od_weights
                ],
            },

            # 站点信息
            "stations": [
                {
                    "id": s.id,
                    "type": s.type,
                    "category": s.category,
                    "x": s.x,
                    "y": s.y,
                    "passenger_count": s.passengerNm,
                    "connecting_lines": self._get_lines_at_station(s),
                    "passengers_by_dest_category": self._passenger_breakdown(s),
                }
                for s in self.stations
            ],

            # 线路信息
            "lines": [
                {
                    "id": l.number,
                    "station_ids": [s.id for s in l.stationList],
                    "station_categories": [s.category for s in l.stationList],
                    "train_count": l.trainNm,
                }
                for l in self.metroLine
            ],

            # 列车信息
            "trains": [
                {
                    "id": t.number,
                    "line_id": t.line.number if t.line else None,
                    "station_id": t.stationNow.id if t.stationNow else None,
                    "status": t.status,
                    "direction": l.trainDirection.get(t) if (l := t.line) else None,
                    "carriage_count": len(t.carriageList),
                    "passenger_count": sum(c.currentNum for c in t.carriageList),
                    "capacity": sum(c.capacity for c in t.carriageList),
                }
                for t in self.ti.trainBusyList
            ],

            # 可用资源
            "available": {
                "trains": len(self.ti.trainAbleList),
                "carriages": len(self.ti.carriageAbleList),
                "lines_remaining": self.config.max_lines - len(self.metroLine),
            },

            # 全局指标
            "metrics": self._compute_metrics(),
        }

    def _get_lines_at_station(self, s):
        """获取经过指定站点的所有线路 id"""
        return [l.number for l in self.metroLine if s in l.stationList]

    def _passenger_breakdown(self, s):
        """获取站点等待乘客的目的地类别分布"""
        breakdown = {}
        for p in s.passenger_list:
            dest_cat = p.destination_station.category or "unknown"
            breakdown[dest_cat] = breakdown.get(dest_cat, 0) + 1
        return breakdown

    # ---- AI 辅助查询方法 ----

    def getUnconnectedStations(self):
        """返回所有未连接到任何线路的站点列表"""
        return [s for s in self.stations if not self._get_lines_at_station(s)]

    def getCategoryCoverage(self):
        """返回各类别的线路覆盖率

        Returns:
            dict: {category: {"connected": n, "total": n, "lines": set()}}
        """
        coverage = {}
        for cat in self.config.all_categories:
            stations_in_cat = [s for s in self.stations if s.category == cat]
            connected = [s for s in stations_in_cat if self._get_lines_at_station(s)]
            # 哪些线路覆盖了这个类别
            lines_covering = set()
            for s in connected:
                for l_id in self._get_lines_at_station(s):
                    lines_covering.add(l_id)
            coverage[cat] = {
                "connected": len(connected),
                "total": len(stations_in_cat),
                "lines": sorted(lines_covering),
            }
        return coverage

    def findNearestStation(self, x, y, category=None, only_unconnected=False):
        """找离指定坐标最近的站点

        Args:
            x, y: 世界坐标
            category: 只找该类别的站点, None 为不限
            only_unconnected: 只找未连接线路的站点

        Returns:
            station 对象, 或 None
        """
        best = None
        best_dist = float('inf')
        for s in self.stations:
            if category and s.category != category:
                continue
            if only_unconnected and self._get_lines_at_station(s):
                continue
            d = ((s.x - x) ** 2 + (s.y - y) ** 2) ** 0.5
            if d < best_dist:
                best_dist = d
                best = s
        return best

    def findStationById(self, station_id):
        """按 ID 查找站点"""
        for s in self.stations:
            if s.id == station_id:
                return s
        return None

    def findLineById(self, line_id):
        """按 ID 查找线路"""
        for l in self.metroLine:
            if l.number == line_id:
                return l
        return None

    def findTrainById(self, train_id):
        """按 ID 查找列车"""
        for t in self.ti.trainBusyList:
            if t.number == train_id:
                return t
        return None

    def _compute_metrics(self):
        """计算全局评估指标"""
        if not self.stations:
            return {}

        passenger_counts = [s.passengerNm for s in self.stations]
        max_passengers = max(passenger_counts) if passenger_counts else 0

        waiting_times = []
        on_train_count = 0
        arrived_count = 0
        for p in self.pm.passenger_list:
            if p.status in ("waiting", "transferring"):
                waiting_times.append(p.waiting_time)
            elif p.status == "on_train":
                on_train_count += 1
            elif p.status == "arrived":
                arrived_count += 1

        avg_wait = sum(waiting_times) / len(waiting_times) if waiting_times else 0

        # 拥堵风险：接近上限的站点数
        overcrowd_threshold = int(self.config.overcrowd_limit * 0.7)
        at_risk_stations = sum(
            1 for s in self.stations
            if s.passengerNm >= overcrowd_threshold
        )

        # 无线路连接的站点数
        unconnected_stations = sum(
            1 for s in self.stations
            if not self._get_lines_at_station(s)
        )

        return {
            "max_station_passengers": max_passengers,
            "avg_waiting_time": round(avg_wait, 1),
            "at_risk_stations": at_risk_stations,
            "unconnected_stations": unconnected_stations,
            "total_arrived": arrived_count,
            "total_on_train": on_train_count,
            "total_waiting": len(waiting_times),
            "overcrowd_limit": self.config.overcrowd_limit,
        }

    # ============================================================
    # 每帧更新
    # ============================================================

    def updateOneTick(self):
        """单 tick 更新"""
        if self.game_over:
            return

        self.tick += 1

        # 更新列车
        self.ti.updateAllTrain()

        # 更新乘客等待时间
        self.pm.update_all_passengers()

        # 按日调度生成乘客
        self._spawn_passengers_scheduled()

        # 动态站点生成（淡化，极少出现）
        self._maybe_spawn_station()

        # 资源增长
        self._resource_growth()

        # 检查拥堵
        crowded = self.check_overcrowd()
        if crowded:
            self.game_over = True
            print(f"\n{'!' * 60}")
            print(f"游戏结束! 站点 {crowded} 过度拥堵! (等候{crowded.passengerNm}人)")
            print(f"共经过 {self.tick} 个 tick")
            print(f"{'!' * 60}")
            self.print_status()

            # 打印最终统计
            arrived = sum(1 for p in self.pm.passenger_list if p.status == "arrived")
            on_train = sum(1 for p in self.pm.passenger_list if p.status == "on_train")
            waiting = sum(1 for p in self.pm.passenger_list if p.status in ("waiting", "transferring"))
            print(f"\n统计: 到达={arrived}, 在车上={on_train}, 等候中={waiting}")

    def _spawn_passengers_scheduled(self):
        """按日调度生成乘客

        根据当前时段和 O-D 流量模式，按概率在各类别站点生成乘客。
        """
        cfg = self.config
        period = cfg.get_current_period(self.tick)
        base_rate = cfg.get_spawn_rate(self.tick)
        od_weights = cfg.get_od_weights(self.tick)

        if not od_weights:
            return

        # 按 O-D 权重加权随机
        total_weight = sum(w for _, _, w in od_weights)

        # 对每个活跃 O-D 对，尝试生成乘客
        for origin_cat, dest_cat, weight in od_weights:
            # 计算该 O-D 对的生成概率
            prob = base_rate * weight / total_weight

            if random.random() >= prob:
                continue

            # 找该类别的始发站
            origin_stations = [s for s in self.stations if s.category == origin_cat]
            dest_stations = [s for s in self.stations if s.category == dest_cat]

            if not origin_stations or not dest_stations:
                continue

            origin = random.choice(origin_stations)
            destinations = [s for s in dest_stations if s != origin]
            if not destinations:
                continue
            dest = random.choice(destinations)

            self.pm.generate_passenger(origin, dest)

    def _spawn_passengers(self):
        """旧版: 按配置生成乘客（已弃用，保留兼容）"""
        cfg = self.config
        spawn_chance = min(
            cfg.passenger_spawn_max_chance,
            cfg.passenger_spawn_base_chance + self.tick * cfg.passenger_spawn_growth,
        )
        if random.random() < spawn_chance:
            self.generate_random_passenger()
        if self.tick > cfg.passenger_extra_spawn_start_tick:
            if random.random() < spawn_chance * cfg.passenger_extra_spawn_ratio:
                self.generate_random_passenger()

    def _maybe_spawn_station(self):
        """按配置动态生成新站点（已淡化）"""
        cfg = self.config
        if len(self.stations) >= cfg.station_max_count:
            return
        if self.tick % cfg.station_spawn_interval != 0:
            return
        if random.random() > cfg.station_spawn_chance:
            return

        # 生成新站点
        new_station = self._generate_random_station()
        if new_station:
            self.stations.append(new_station)
            print(f"  新站点出现: {new_station}")

    def _generate_random_station(self):
        """尝试生成一个随机站点，确保与已有站点保持最小距离"""
        cfg = self.config
        for _ in range(20):  # 最多尝试 20 次
            x = random.randint(*cfg.station_x_range)
            y = random.randint(*cfg.station_y_range)
            stype = random.choice(cfg.station_type_list)

            # 检查最小距离
            too_close = any(
                ((s.x - x) ** 2 + (s.y - y) ** 2) ** 0.5 < cfg.station_min_distance
                for s in self.stations
            )
            if not too_close:
                return self._make_station(stype, x, y)
        return None  # 20 次都找不到合适位置

    def _resource_growth(self):
        """按配置增长资源"""
        cfg = self.config
        for interval, resource_type, amount in cfg.resource_growth_schedule:
            if interval <= 0 or self.tick % interval != 0:
                continue
            for _ in range(amount):
                self._grant_resource(resource_type)

    def _grant_resource(self, resource_type):
        """发放一项资源"""
        if resource_type == "train":
            if len(self.ti.trainAbleList) + len(self.ti.trainBusyList) < self.config.max_trains:
                self.ti.addTrain()
                print(f"  获得新列车! 车库现有 {len(self.ti.trainAbleList)} 列待命")
        elif resource_type == "carriage":
            if len(self.ti.carriageAbleList) + len(self.ti.carriageBusyList) < self.config.max_carriages:
                self.ti.addCarriage()
                print(f"  获得新车厢! 车库现有 {len(self.ti.carriageAbleList)} 节待命")
        elif resource_type == "line":
            # 新线路额度 — 增加最大线路数上限
            if self.config.max_lines < 20:
                self.config.max_lines += 1
                print(f"  获得新线路额度! 最大线路数: {self.config.max_lines}")
        elif resource_type == "tunnel":
            # 隧道暂不实现，预留
            pass

    # ============================================================
    # 辅助方法
    # ============================================================

    def generate_random_passenger(self):
        if len(self.stations) < 2:
            return
        origin = random.choice(self.stations)
        destinations = [s for s in self.stations if s != origin]
        if not destinations:
            return
        dest = random.choice(destinations)
        self.pm.generate_passenger(origin, dest)

    def check_overcrowd(self):
        limit = self.config.overcrowd_limit
        for s in self.stations:
            if s.passengerNm >= limit:
                return s
        return None

    def print_status(self):
        cfg = self.config
        period = cfg.get_current_period(self.tick)
        print(f"\n--- Tick {self.tick} (时段: {period}) ---")
        print("站点候车:")
        limit = cfg.overcrowd_limit
        for s in self.stations:
            marker = " !!!" if s.passengerNm >= limit - 2 else ""
            lines_at = self._get_lines_at_station(s)
            cat = s.category or "?"
            print(f"  {s} [{cat}] 等候{s.passengerNm}人 线路{lines_at}{marker}")
        print("列车状态:")
        for tr in self.ti.trainBusyList:
            carriage_info = ""
            for c in tr.carriageList:
                carriage_info += f" [{c.currentNum}/{c.capacity}]"
            line_id = tr.line.number if tr.line else "?"
            print(f"  {tr} line={line_id}{carriage_info}")
        print("可用资源:")
        print(f"  列车:{len(self.ti.trainAbleList)} 车厢:{len(self.ti.carriageAbleList)} 线路余额:{self.config.max_lines - len(self.metroLine)}")

    def run(self, max_ticks=500, ai_callback=None):
        """主循环

        Args:
            max_ticks: 最大 tick 数
            ai_callback: 可选的 AI 回调函数, 每隔若干 tick 调用
                         签名: ai_callback(world) -> None
        """
        self.setup()
        while self.tick < max_ticks and not self.game_over:
            self.updateOneTick()

            # AI 决策：每 10 tick 调用一次
            if ai_callback and self.tick % 10 == 0:
                ai_callback(self)

            # 每 10 tick 打印一次
            if self.tick % 10 == 0:
                self.print_status()

        if not self.game_over:
            print(f"\n达到最大tick数 {max_ticks}, 游戏未结束")
            self.print_status()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Mini Metro")
    parser.add_argument("--visual", action="store_true", help="启用 pygame 可视化模式")
    parser.add_argument("--max-ticks", type=int, default=500, help="最大 tick 数 (默认 500)")
    args = parser.parse_args()

    world = MetroWorld()
    if args.visual:
        from visualizer import Visualizer
        viz = Visualizer(world)
        viz.run(max_ticks=args.max_ticks)
    else:
        world.run(max_ticks=args.max_ticks)