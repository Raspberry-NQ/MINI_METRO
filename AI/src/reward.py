# reward.py — 调度器综合奖励函数


class RewardCalculator:
    """综合奖励计算器：平衡运力、成本、存活时间

    主要目标：
      - 运力：奖励送达乘客到目的地
      - 存活时间：奖励长期运营

    次要目标：
      - 等待人数改善：奖励减少候车乘客
      - 拥堵风险改善：奖励减少风险站点
      - 列车开销：惩罚过度使用列车资源

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

    def reset(self):
        """每个 episode 开始时调用"""
        self.prev_total_waiting = None
        self.prev_at_risk = None
        self.prev_total_arrived = None
        self.prev_active_trains = None
        self.prev_placed_trains = False

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
            return 0.0

        reward = 0.0

        # 1. 运力奖励（主要）：每送达一位乘客 +5分
        arrived_change = total_arrived - self.prev_total_arrived
        reward += arrived_change * 5.0

        # 2. 存活奖励（主要）：每决策步 +0.5分
        reward += 0.5

        # 3. 等待人数改善奖励（次要）
        waiting_change = self.prev_total_waiting - total_waiting
        reward += 5.0 * (waiting_change / max(self.overcrowd_limit, 1))

        # 4. 拥堵风险惩罚（次要）
        risk_change = self.prev_at_risk - at_risk
        reward += 2.0 * risk_change

        # 5. 列车开销惩罚（次要）：每辆运行列车 -0.2分
        reward -= active_trains * 0.2

        # 6. 从零开始引导奖励
        # 首次放置列车奖励：鼓励AI开始运营
        if not self.prev_placed_trains and active_trains > 0:
            reward += 3.0  # 首次放置列车奖励
            self.prev_placed_trains = True

        # 线路利用率惩罚：有线路但没列车时轻微惩罚
        lines = state_dict.get("lines", [])
        if active_trains == 0 and len(lines) > 0:
            # 有线路但没列车运营，给予小惩罚促使AI放置列车
            reward -= 0.5

        # 7. 游戏结束大惩罚
        if state_dict.get("game_over", False):
            reward -= 100.0

        # 更新记录
        self.prev_total_waiting = total_waiting
        self.prev_at_risk = at_risk
        self.prev_total_arrived = total_arrived
        self.prev_active_trains = active_trains

        # 裁剪防止极端值
        reward = max(-20.0, min(20.0, reward))

        return reward
