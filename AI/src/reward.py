# reward.py — 调度器差分奖励函数


class RewardCalculator:
    """计算调度器的差分奖励

    核心原则: 用差分(变化量)而非绝对值, 让 AI 学到"我的决策是否改善了局面"
    """

    def __init__(self, overcrowd_limit=50):
        self.overcrowd_limit = overcrowd_limit
        self.prev_total_waiting = None
        self.prev_at_risk = None

    def reset(self):
        """每个 episode 开始时调用"""
        self.prev_total_waiting = None
        self.prev_at_risk = None

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

        # 第一次调用, 只记录基线
        if self.prev_total_waiting is None:
            self.prev_total_waiting = total_waiting
            self.prev_at_risk = at_risk
            return 0.0

        reward = 0.0

        # 1. 等待人数变化 (+2 分 / 改善 overcrowd_limit 人)
        waiting_change = self.prev_total_waiting - total_waiting
        reward += 2.0 * (waiting_change / max(self.overcrowd_limit, 1))

        # 2. 拥堵风险站变化 (+3 分 / 改善一个站)
        risk_change = self.prev_at_risk - at_risk
        reward += 3.0 * risk_change

        # 3. 游戏结束大惩罚
        if state_dict.get("game_over", False):
            reward -= 50.0

        # 更新记录
        self.prev_total_waiting = total_waiting
        self.prev_at_risk = at_risk

        # 裁剪防止极端值
        reward = max(-10.0, min(10.0, reward))

        return reward
