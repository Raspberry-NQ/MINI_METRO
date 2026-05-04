# reward.py — 调度器综合奖励函数


class RewardCalculator:
    """综合奖励计算器：平衡运力、成本、存活时间

    主要目标：
      - 运力：奖励送达乘客到目的地
      - 存活时间：奖励长期运营
      - 线路平衡：奖励在多条线路间平衡分配列车

    次要目标：
      - 等待人数改善：奖励减少候车乘客
      - 拥堵风险改善：奖励减少风险站点
      - 响应拥堵：奖励及时向拥堵线路调配列车

    从零开始引导：
      - 首次放置列车奖励：鼓励AI开始运营
      - 线路利用率：轻微惩罚有线路但无列车的情况
    """

    def __init__(self, overcrowd_limit=50):
        self.overcrowd_limit = overcrowd_limit
        self.prev_total_waiting = None
        self.prev_at_risk = None
        self.prev_total_arrived = None
        self.prev_active_trains = None
        self.prev_placed_trains = False  # 记录是否已放置过列车
        self.prev_line_distribution = None  # 记录上次的线路列车分布

    def reset(self):
        """每个 episode 开始时调用"""
        self.prev_total_waiting = None
        self.prev_at_risk = None
        self.prev_total_arrived = None
        self.prev_active_trains = None
        self.prev_placed_trains = False
        self.prev_line_distribution = None

    def compute(self, state_dict):
        """计算当前状态的奖励

        Args:
            state_dict: getGameState() 返回的字典

        Returns:
            float: 奖励值
        """
        metrics = state_dict.get("metrics", {})
        total_waiting = metrics.get("total_waiting", 0)
        at_risk = metrics.get("at_risk_stations", 0)
        total_arrived = metrics.get("total_arrived", 0)

        trains = state_dict.get("trains", [])
        active_trains = sum(1 for t in trains if t["status"] != 3)

        # 第一次调用，记录基线
        if self.prev_total_waiting is None:
            self.prev_total_waiting = total_waiting
            self.prev_at_risk = at_risk
            self.prev_total_arrived = total_arrived
            self.prev_active_trains = active_trains
            self.prev_line_distribution = self._get_line_distribution(state_dict)
            return 0.0

        reward = 0.0

        # ========================================
        # 主要奖励
        # ========================================

        # 1. 运力奖励（主要）：每送达一位乘客 +10分
        arrived_change = total_arrived - self.prev_total_arrived
        reward += arrived_change * 10.0

        # 2. 存活奖励（主要）：每决策步 +1分
        reward += 1.0

        # ========================================
        # 线路平衡奖励（核心改进）
        # ========================================

        lines = state_dict.get("lines", [])
        line_distribution = self._get_line_distribution(state_dict)

        # 3. 线路覆盖率奖励：覆盖更多线路
        lines_with_trains = sum(1 for count in line_distribution.values() if count > 0)
        total_lines = len(lines)
        if total_lines > 0:
            coverage_ratio = lines_with_trains / total_lines
            reward += coverage_ratio * 2.0  # 增加权重：覆盖所有线路 +2分

        # 4. 线路平衡奖励：惩罚列车分布不均
        if active_trains > 0 and total_lines > 0:
            # 计算标准差（衡量分布不均匀程度）
            train_counts = list(line_distribution.values())
            mean_trains = active_trains / total_lines
            variance = sum((count - mean_trains) ** 2 for count in train_counts) / total_lines
            std_dev = variance ** 0.5

            # 标准差越小越均衡，给予奖励
            # 理想情况：每条线路列车数相同，std_dev=0
            balance_reward = -std_dev * 1.5  # 惩罚不均衡
            reward += balance_reward

        # 5. 动态调度奖励：奖励向空线路分配列车
        if self.prev_line_distribution:
            for line_id, count in line_distribution.items():
                prev_count = self.prev_line_distribution.get(line_id, 0)
                if prev_count == 0 and count > 0:
                    # 向之前空的线路分配了列车
                    reward += 1.5  # 每向一条空线路分配列车 +1.5分

        # ========================================
        # 响应式调度奖励
        # ========================================

        # 6. 等待人数改善奖励
        waiting_change = self.prev_total_waiting - total_waiting
        reward += 3.0 * (waiting_change / max(self.overcrowd_limit, 1))

        # 7. 拥堵风险改善奖励
        risk_change = self.prev_at_risk - at_risk
        reward += 2.0 * risk_change

        # 8. 线路压力平衡：奖励向高压力线路调配资源
        pressure_balance = self._compute_pressure_balance(state_dict)
        reward += pressure_balance

        # ========================================
        # 引导奖励
        # ========================================

        # 9. 首次放置列车奖励
        if not self.prev_placed_trains and active_trains > 0:
            reward += 10.0
            self.prev_placed_trains = True

        # 10. 线路利用率惩罚
        if active_trains == 0 and len(lines) > 0:
            reward -= 1.0

        # ========================================
        # 游戏结束惩罚
        # ========================================

        if state_dict.get("game_over", False):
            reward -= 200.0

        # 更新记录
        self.prev_total_waiting = total_waiting
        self.prev_at_risk = at_risk
        self.prev_total_arrived = total_arrived
        self.prev_active_trains = active_trains
        self.prev_line_distribution = line_distribution

        # 裁剪防止极端值
        reward = max(-50.0, min(50.0, reward))

        return reward

    def _get_line_distribution(self, state_dict):
        """获取各线路的列车数量

        Args:
            state_dict: 游戏状态字典

        Returns:
            dict: {line_id: train_count}
        """
        distribution = {}
        for line_info in state_dict.get("lines", []):
            line_id = line_info["id"]
            train_count = line_info.get("train_count", 0)
            distribution[line_id] = train_count
        return distribution

    def _compute_pressure_balance(self, state_dict):
        """计算线路压力平衡奖励

        检查列车是否被分配到压力大的线路（等待乘客多的线路）

        Args:
            state_dict: 游戏状态字典

        Returns:
            float: 压力平衡奖励
        """
        lines = state_dict.get("lines", [])
        stations = state_dict.get("stations", [])

        if not lines or not stations:
            return 0.0

        # 计算每条线路的压力（该线路站点的平均等待人数）
        line_pressure = {}
        for line_info in lines:
            line_id = line_info["id"]
            station_ids = set(line_info.get("station_ids", []))

            # 找到该线路的站点
            line_stations = [s for s in stations if s["id"] in station_ids]
            if line_stations:
                avg_waiting = sum(s["passenger_count"] for s in line_stations) / len(line_stations)
                line_pressure[line_id] = avg_waiting
            else:
                line_pressure[line_id] = 0

        # 计算压力差异
        if len(line_pressure) < 2:
            return 0.0

        pressures = list(line_pressure.values())
        mean_pressure = sum(pressures) / len(pressures)

        # 如果所有线路压力都很低，不需要奖励
        if mean_pressure < 5:
            return 0.0

        # 计算压力的标准差
        variance = sum((p - mean_pressure) ** 2 for p in pressures) / len(pressures)
        std_dev = variance ** 0.5

        # 惩罚压力不均衡（有些线路很拥堵，有些很空闲）
        return -std_dev * 0.3
