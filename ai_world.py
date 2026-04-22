# ai_world.py — AI 训练专用世界
#
# 与 MetroWorld 的区别:
#   1. 站点一次性全部生成，后续不再新增
#   2. AI 在世界开始时一次性规划所有线路，规划完成后锁定线路不可修改
#   3. 时间尺度贴近现实: 1 tick ≈ 1 分钟, 一天 1200 tick ≈ 20 小时
#   4. 每天结束后自动结算（开支、客流、收益等指标）
#   5. AI 只能做调度操作（调车/分配列车/加车厢），不能改线路

import random
from run import MetroWorld
from game_config import GameConfig
from station import CATEGORY_LABEL_CN


class AIWorld(MetroWorld):
    """AI 训练专用世界

    生命周期:
        1. setup()        — 生成城市，给出初始资源
        2. 规划阶段       — AI 调用 build_lines() 建线路，place_initial_trains() 放列车
        3. lock_lines()   — 锁定线路，此后只能调度不能改线
        4. run_one_day()   — 模拟一天（1200 tick），返回当天结算报告
        5. 可重复步骤 4     — 多天运行，每天独立结算
    """

    def __init__(self, config=None):
        if config is None:
            config = GameConfig.for_ai_training()
        super().__init__(config)
        self._lines_locked = False
        self._day_count = 0
        self._day_start_tick = 0
        self._history = []  # 历史每日结算报告

    # ============================================================
    # 初始化
    # ============================================================

    def setup(self):
        """生成城市和初始资源（不给列车，由 AI 自行分配）"""
        self.pm = None  # 先创建 PassengerManager
        from passengerManager import PassengerManager
        from trainInventory import TrainInventory
        self.pm = PassengerManager(self, self.config)
        self.ti = TrainInventory(self.pm, self.config)

        # 一次性生成所有站点
        from city_generator import generate_city
        self.stations = generate_city(self.config, id_start=0)
        self._next_station_id = max((s.id for s in self.stations), default=0)

        # 按配置的最大资源数直接全部给齐
        cfg = self.config
        for _ in range(cfg.max_trains):
            self.ti.addTrain()
        for _ in range(cfg.max_carriages):
            self.ti.addCarriage()

        self._rebuild_all_connections()
        self._print_init_summary()

    # ============================================================
    # 线路锁定机制
    # ============================================================

    def lock_lines(self):
        """锁定线路，此后不可新建/延伸/插入线路"""
        self._lines_locked = True

    def unlock_lines(self):
        """解锁线路（仅用于重置或调试）"""
        self._lines_locked = False

    # ---- 覆写线路操作方法，锁定后抛异常 ----

    def playerNewLine(self, station_list):
        if self._lines_locked:
            raise RuntimeError("线路已锁定，不可新建线路。仅可做调度操作。")
        return super().playerNewLine(station_list)

    def playerLineExtension(self, line, station_obj, append=True):
        if self._lines_locked:
            raise RuntimeError("线路已锁定，不可延伸线路。仅可做调度操作。")
        return super().playerLineExtension(line, station_obj, append)

    def playerLineInsert(self, line, index, station_obj):
        if self._lines_locked:
            raise RuntimeError("线路已锁定，不可插入站点。仅可做调度操作。")
        return super().playerLineInsert(line, index, station_obj)

    # ============================================================
    # AI 便捷操作
    # ============================================================

    def build_lines(self, line_definitions):
        """一次性创建多条线路

        Args:
            line_definitions: list of list[station_id]
                每个内层列表是一组站点 ID，按顺序组成一条线路
                例: [[1,3,5,7], [2,3,4,6]]

        Returns:
            list[MetroLine]: 成功创建的线路对象列表
        """
        created = []
        for station_ids in line_definitions:
            station_objs = []
            for sid in station_ids:
                s = self.findStationById(sid)
                if s is None:
                    print(f"[WARN] 站点 ID {sid} 不存在，跳过该线路")
                    station_objs = None
                    break
                station_objs.append(s)
            if station_objs is None or len(station_objs) < 2:
                print(f"[WARN] 线路站点不足，跳过: {station_ids}")
                continue
            line = self.playerNewLine(station_objs)
            if line:
                created.append(line)
        return created

    def place_initial_trains(self, train_placements):
        """在线路上放置初始列车

        Args:
            train_placements: list of dict
                每个字典包含:
                  - line_id: int       线路 ID
                  - station_id: int    上车站点 ID
                  - direction: bool    True=正向, False=反向
                例: [{"line_id":1, "station_id":3, "direction":True}, ...]

        Returns:
            list[train]: 成功放置的列车对象列表
        """
        placed = []
        for tp in train_placements:
            line = self.findLineById(tp["line_id"])
            station = self.findStationById(tp["station_id"])
            direction = tp.get("direction", True)
            if line is None or station is None:
                print(f"[WARN] 找不到线路或站点，跳过: {tp}")
                continue
            # 检查该线路列车数是否超过上限
            if line.trainNm >= self.config.max_trains_per_line:
                print(f"[WARN] 线路 {line.number} 已达列车上限 ({self.config.max_trains_per_line})，跳过")
                continue
            train_obj = self.playerEmployTrain(line, station, direction)
            if train_obj:
                placed.append(train_obj)
        return placed

    # ============================================================
    # 运行
    # ============================================================

    def run_one_day(self, ai_callback=None):
        """模拟一天（day_length tick），返回当日结算报告

        Args:
            ai_callback: 可选调度回调，签名 ai_callback(world) -> None
                         每 60 tick (约 1 小时) 调用一次

        Returns:
            dict: 当日结算报告
        """
        self._day_count += 1
        self._day_start_tick = self.tick
        cfg = self.config

        # 记录当天起始指标用于差分计算
        start_arrived = self._count_arrived()
        start_ticks_survived = self.tick

        ticks_this_day = cfg.day_length
        schedule_interval = 60  # 每小时调度一次

        for _ in range(ticks_this_day):
            if self.game_over:
                break
            self.updateOneTick()

            # AI 调度
            if ai_callback and self.tick % schedule_interval == 0:
                try:
                    ai_callback(self)
                except Exception as e:
                    print(f"[ERROR] tick {self.tick} AI调度出错: {e}")

        # 天结束，生成结算报告
        report = self._day_summary(start_arrived, start_ticks_survived)
        self._history.append(report)
        return report

    def run_days(self, num_days=1, ai_callback=None):
        """模拟多天，返回所有结算报告

        Args:
            num_days: 天数
            ai_callback: 调度回调

        Returns:
            list[dict]: 每天的结算报告
        """
        reports = []
        for _ in range(num_days):
            if self.game_over:
                break
            report = self.run_one_day(ai_callback)
            reports.append(report)
        return reports

    # ============================================================
    # 每日结算
    # ============================================================

    def _day_summary(self, start_arrived, start_ticks_survived):
        """计算当日结算报告"""
        cfg = self.config

        # --- 客流指标 ---
        end_arrived = self._count_arrived()
        passengers_arrived_today = end_arrived - start_arrived

        waiting_times = []
        total_on_train = 0
        total_waiting = 0
        for p in self.pm.passenger_list:
            if p.status in ("waiting", "transferring"):
                waiting_times.append(p.waiting_time)
                total_waiting += 1
            elif p.status == "on_train":
                total_on_train += 1

        avg_wait = sum(waiting_times) / len(waiting_times) if waiting_times else 0
        max_wait = max(waiting_times) if waiting_times else 0

        # --- 运营指标 ---
        # 列车总里程 (tick): 每辆运行中列车每个 running tick 算 1 单位里程
        # 简化: 用线路总长度 × 列车数估算
        total_train_km = 0
        for line in self.metroLine:
            line_distance = line.distance()  # 单位: tick
            total_train_km += line_distance * line.trainNm

        # 活跃列车数
        active_trains = sum(1 for t in self.ti.trainBusyList if t.status != 3)
        total_trains_in_service = len(self.ti.trainBusyList)
        total_carriages_in_service = len(self.ti.carriageBusyList)

        # --- 覆盖率 ---
        coverage = self.getCategoryCoverage()
        overall_coverage = sum(
            c["connected"] / c["total"] if c["total"] > 0 else 0
            for c in coverage.values()
        ) / len(coverage) if coverage else 0

        # --- 拥堵风险 ---
        overcrowd_threshold = int(cfg.overcrowd_limit * 0.7)
        at_risk_stations = sum(
            1 for s in self.stations if s.passengerNm >= overcrowd_threshold
        )
        max_station_passengers = max((s.passengerNm for s in self.stations), default=0)

        # --- 财务 ---
        # 每位到达乘客票价收入
        ticket_price = 5
        revenue = passengers_arrived_today * ticket_price

        # 运营成本
        train_cost_per_day = 200           # 每列列车每天固定成本
        carriage_cost_per_day = 50         # 每节车厢每天固定成本
        line_cost_per_day = 500            # 每条线路每天固定成本
        running_cost_per_km = 1            # 每单位里程变动成本

        cost_fixed = (total_trains_in_service * train_cost_per_day +
                      total_carriages_in_service * carriage_cost_per_day +
                      len(self.metroLine) * line_cost_per_day)
        cost_variable = total_train_km * running_cost_per_km

        total_cost = cost_fixed + cost_variable
        profit = revenue - total_cost

        report = {
            "day": self._day_count,
            "survived": not self.game_over,
            "ticks_today": self.tick - self._day_start_tick,

            # 客流
            "passengers_arrived_today": passengers_arrived_today,
            "passengers_on_train": total_on_train,
            "passengers_waiting": total_waiting,
            "avg_waiting_time": round(avg_wait, 1),
            "max_waiting_time": max_wait,

            # 运营
            "active_trains": active_trains,
            "total_trains_in_service": total_trains_in_service,
            "total_carriages_in_service": total_carriages_in_service,
            "train_km": total_train_km,
            "lines_count": len(self.metroLine),

            # 覆盖
            "category_coverage": {cat: cov for cat, cov in coverage.items()},
            "overall_coverage_ratio": round(overall_coverage, 3),

            # 安全
            "at_risk_stations": at_risk_stations,
            "max_station_passengers": max_station_passengers,

            # 财务
            "revenue": revenue,
            "cost_fixed": cost_fixed,
            "cost_variable": cost_variable,
            "total_cost": total_cost,
            "profit": profit,
        }
        return report

    def _count_arrived(self):
        """统计已到达目的地的乘客总数"""
        if self.pm is None:
            return 0
        return sum(1 for p in self.pm.passenger_list if p.status == "arrived")

    def print_day_report(self, report):
        """打印当日结算报告"""
        print(f"\n{'='*60}")
        print(f"第 {report['day']} 天结算")
        print(f"{'='*60}")
        print(f"存活: {'是' if report['survived'] else '否'}  "
              f"运行 tick: {report['ticks_today']}")
        print()
        print("--- 客流 ---")
        print(f"  到达乘客: {report['passengers_arrived_today']}")
        print(f"  在车乘客: {report['passengers_on_train']}")
        print(f"  等候乘客: {report['passengers_waiting']}")
        print(f"  平均等候: {report['avg_waiting_time']} tick")
        print(f"  最大等候: {report['max_waiting_time']} tick")
        print()
        print("--- 运营 ---")
        print(f"  活跃列车: {report['active_trains']}/{report['total_trains_in_service']}")
        print(f"  车厢数:   {report['total_carriages_in_service']}")
        print(f"  列车里程: {report['train_km']} tick-km")
        print(f"  线路数:   {report['lines_count']}")
        print()
        print("--- 覆盖 ---")
        for cat, cov in report["category_coverage"].items():
            label = CATEGORY_LABEL_CN.get(cat, cat)
            print(f"  {label}: {cov['connected']}/{cov['total']}")
        print(f"  总覆盖率: {report['overall_coverage_ratio']*100:.1f}%")
        print()
        print("--- 安全 ---")
        print(f"  拥堵风险站: {report['at_risk_stations']}")
        print(f"  最大候车数: {report['max_station_passengers']}")
        print()
        print("--- 财务 ---")
        print(f"  票价收入: {report['revenue']}")
        print(f"  固定成本: {report['cost_fixed']}")
        print(f"  变动成本: {report['cost_variable']}")
        print(f"  总成本:   {report['total_cost']}")
        print(f"  利润:     {report['profit']}")
        print(f"{'='*60}")

    # ============================================================
    # AI 输入接口 (getGameState 已在父类实现，此处增加 AI 专用字段)
    # ============================================================

    def getGameState(self):
        """返回游戏状态快照，增加 AI 专用字段"""
        state = super().getGameState()
        state["lines_locked"] = self._lines_locked
        state["day_count"] = self._day_count
        state["tick_in_day"] = self.tick - self._day_start_tick

        # 增加每条线路的列车详情（方便 AI 做调度决策）
        for line_info in state["lines"]:
            line_obj = self.findLineById(line_info["id"])
            if line_obj:
                line_info["train_ids"] = [
                    t.number for t in line_obj.trainDirection.keys()
                ]
                line_info["max_trains"] = self.config.max_trains_per_line

        return state

    # ============================================================
    # 禁用不适用于 AI 世界的功能
    # ============================================================

    def _maybe_spawn_station(self):
        """AI 世界不生成新站点"""
        pass

    def _resource_growth(self):
        """AI 世界不渐进增长资源"""
        pass

    # ============================================================
    # 快速启动（一个完整的 AI 测试流程）
    # ============================================================

    def quick_start(self, line_definitions, train_placements, num_days=1,
                    ai_callback=None):
        """一键启动: 建线路 → 放列车 → 锁线 → 运行 N 天

        Args:
            line_definitions: 传给 build_lines() 的线路定义
            train_placements: 传给 place_initial_trains() 的列车部署
            num_days: 模拟天数
            ai_callback: 每小时调用的调度回调

        Returns:
            list[dict]: 每天结算报告
        """
        # 规划阶段
        self.build_lines(line_definitions)
        self.place_initial_trains(train_placements)
        self.lock_lines()

        # 运行阶段
        return self.run_days(num_days, ai_callback)
