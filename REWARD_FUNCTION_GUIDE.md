# AI奖励函数修改指南

## 文件位置
`ai/src/reward.py` - RewardCalculator类

## 当前奖励函数结构

```python
class RewardCalculator:
    def __init__(self, overcrowd_limit=50):
        self.overcrowd_limit = overcrowd_limit
        self.prev_total_waiting = None
        self.prev_at_risk = None

    def reset(self):
        """每个episode开始时调用"""
        self.prev_total_waiting = None
        self.prev_at_risk = None

    def compute(self, state_dict):
        """计算当前状态的奖励"""
        metrics = state_dict.get("metrics", {})
        total_waiting = metrics.get("total_waiting", 0)
        at_risk = metrics.get("at_risk_stations", 0)

        # 第一次调用，只记录基线
        if self.prev_total_waiting is None:
            self.prev_total_waiting = total_waiting
            self.prev_at_risk = at_risk
            return 0.0

        reward = 0.0

        # 1. 等待人数变化奖励
        waiting_change = self.prev_total_waiting - total_waiting
        reward += 2.0 * (waiting_change / max(self.overcrowd_limit, 1))

        # 2. 拥堵风险站变化奖励
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
```

---

## 如何修改奖励函数

### 1. 修改权重

**示例：增加运力奖励权重**

```python
def compute(self, state_dict):
    reward = 0.0

    # 原权重: 2.0
    # 新权重: 5.0 (更重视减少等待人数)
    waiting_change = self.prev_total_waiting - total_waiting
    reward += 5.0 * (waiting_change / max(self.overcrowd_limit, 1))

    # 原权重: 3.0
    # 新权重: 1.0 (降低拥堵风险的重要性)
    risk_change = self.prev_at_risk - at_risk
    reward += 1.0 * risk_change

    return reward
```

**权重调整建议**：
- 运力相关：5.0 - 10.0（主要目标）
- 拥堵风险：1.0 - 3.0（次要目标）
- 游戏结束：-50.0 - -100.0（避免失败）

---

### 2. 添加新参数

#### 步骤1：在`__init__`中添加新的跟踪变量

```python
def __init__(self, overcrowd_limit=50):
    self.overcrowd_limit = overcrowd_limit
    self.prev_total_waiting = None
    self.prev_at_risk = None

    # 新增：跟踪到达乘客数
    self.prev_total_arrived = None
    # 新增：跟踪运行列车数
    self.prev_active_trains = None
```

#### 步骤2：在`reset`中初始化新变量

```python
def reset(self):
    self.prev_total_waiting = None
    self.prev_at_risk = None
    self.prev_total_arrived = None  # 新增
    self.prev_active_trains = None  # 新增
```

#### 步骤3：在`compute`中使用新参数

```python
def compute(self, state_dict):
    metrics = state_dict.get("metrics", {})
    total_waiting = metrics.get("total_waiting", 0)
    at_risk = metrics.get("at_risk_stations", 0)

    # 新增：获取到达乘客数
    total_arrived = metrics.get("total_arrived", 0)
    # 新增：获取运行列车数
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

    # 1. 运力奖励：每送达一位乘客 +5分
    arrived_change = total_arrived - self.prev_total_arrived
    reward += arrived_change * 5.0

    # 2. 等待人数变化奖励
    waiting_change = self.prev_total_waiting - total_waiting
    reward += 2.0 * (waiting_change / max(self.overcrowd_limit, 1))

    # 3. 拥堵风险站变化奖励
    risk_change = self.prev_at_risk - at_risk
    reward += 3.0 * risk_change

    # 4. 列车开销惩罚：每辆运行列车每决策步 -0.1分
    reward -= active_trains * 0.1

    # 5. 存活奖励：每决策步 +0.1分
    reward += 0.1

    # 6. 游戏结束大惩罚
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
```

---

### 3. 可用的状态参数

从`state_dict`中可以获取的参数：

#### 全局指标 (metrics)
```python
metrics = state_dict.get("metrics", {})
- total_waiting: 总等待乘客数
- total_arrived: 总到达乘客数
- total_on_train: 车上乘客数
- at_risk_stations: 拥堵风险站数
- unconnected_stations: 未连接站数
- max_station_passengers: 最大站点候车数
- avg_waiting_time: 平均等待时间
```

#### 站点信息 (stations)
```python
stations = state_dict.get("stations", [])
- 每个站点的 passenger_count
- 每个站点的 category
- 每个站点的 connecting_lines
```

#### 列车信息 (trains)
```python
trains = state_dict.get("trains", [])
- 每辆列车的 status (1-6)
- 每辆列车的 passenger_count
- 每辆列车的 capacity
- 每辆列车的 carriage_count
- 每辆列车的 line_id
```

#### 可用资源 (available)
```python
available = state_dict.get("available", {})
- trains: 可用列车数
- carriages: 可用车厢数
- lines_remaining: 剩余线路额度
```

---

### 4. 常见奖励设计示例

#### 示例1：重视运力和存活时间
```python
reward = 0.0

# 运力奖励（主要）
arrived_change = total_arrived - self.prev_total_arrived
reward += arrived_change * 10.0

# 存活奖励（主要）
reward += 1.0

# 列车开销惩罚（次要）
reward -= active_trains * 0.05

# 拥堵惩罚（次要）
reward -= at_risk * 2.0

# 游戏结束惩罚
if game_over:
    reward -= 100.0
```

#### 示例2：重视效率和成本控制
```python
reward = 0.0

# 运力奖励
arrived_change = total_arrived - self.prev_total_arrived
reward += arrived_change * 5.0

# 满载率奖励（效率）
avg_load = calculate_average_load(trains)
reward += avg_load * 2.0

# 列车开销惩罚（成本）
reward -= active_trains * 0.2

# 等待时间惩罚（服务质量）
avg_wait = metrics.get("avg_waiting_time", 0)
reward -= avg_wait * 0.1

# 游戏结束惩罚
if game_over:
    reward -= 50.0
```

#### 示例3：重视服务质量
```python
reward = 0.0

# 运力奖励
arrived_change = total_arrived - self.prev_total_arrived
reward += arrived_change * 8.0

# 等待时间惩罚（服务质量）
avg_wait = metrics.get("avg_waiting_time", 0)
reward -= avg_wait * 0.5

# 最大等待时间惩罚
max_wait = calculate_max_waiting_time(state_dict)
reward -= max_wait * 0.1

# 拥堵惩罚
reward -= at_risk * 5.0

# 存活奖励
reward += 0.5

# 游戏结束惩罚
if game_over:
    reward -= 200.0
```

---

### 5. 调试技巧

#### 5.1 打印奖励分解
```python
def compute(self, state_dict):
    # ... 计算各项奖励 ...

    # 打印分解（调试用）
    if DEBUG_MODE:
        print(f"Reward breakdown:")
        print(f"  Arrived: +{arrived_reward:.2f}")
        print(f"  Waiting: +{waiting_reward:.2f}")
        print(f"  Risk: +{risk_reward:.2f}")
        print(f"  Cost: -{cost_penalty:.2f}")
        print(f"  Total: {reward:.2f}")

    return reward
```

#### 5.2 记录奖励历史
```python
def __init__(self):
    self.reward_history = []  # 记录每次奖励

def compute(self, state_dict):
    reward = ... # 计算奖励
    self.reward_history.append({
        'step': len(self.reward_history),
        'reward': reward,
        'arrived': total_arrived,
        'waiting': total_waiting,
    })
    return reward
```

---

### 6. 常见问题

#### Q1: 奖励值太大或太小怎么办？
**A**: 使用裁剪函数：
```python
reward = max(-20.0, min(20.0, reward))
```
根据你的主要奖励项调整范围。

#### Q2: 如何判断权重是否合理？
**A**: 观察训练结果：
- 如果AI总是快速失败 → 增加存活奖励，减少惩罚
- 如果AI不重视运力 → 增加运力奖励权重
- 如果AI过度使用列车 → 增加列车开销惩罚

#### Q3: 奖励函数需要多久调整一次？
**A**: 建议：
- 初期：每训练100-200 episode观察一次，调整权重
- 中期：基本定型后，微调即可
- 后期：可以尝试不同的奖励策略对比效果

---

### 7. 推荐的奖励函数（综合版）

```python
class RewardCalculator:
    """综合奖励计算器：平衡运力、成本、存活时间"""

    def __init__(self, overcrowd_limit=50):
        self.overcrowd_limit = overcrowd_limit
        self.prev_total_waiting = None
        self.prev_at_risk = None
        self.prev_total_arrived = None
        self.prev_active_trains = None

    def reset(self):
        self.prev_total_waiting = None
        self.prev_at_risk = None
        self.prev_total_arrived = None
        self.prev_active_trains = None

    def compute(self, state_dict):
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
        reward += 1.0 * (waiting_change / max(self.overcrowd_limit, 1))

        # 4. 拥堵风险惩罚（次要）
        risk_change = self.prev_at_risk - at_risk
        reward += 2.0 * risk_change

        # 5. 列车开销惩罚（次要）：每辆运行列车 -0.05分
        reward -= active_trains * 0.05

        # 6. 游戏结束大惩罚
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
```

---

## 总结

修改奖励函数的关键：
1. **明确目标**：运力、成本、存活时间哪个最重要？
2. **调整权重**：主要目标权重高，次要目标权重低
3. **添加参数**：根据需要添加新的跟踪变量
4. **调试观察**：训练过程中观察AI行为，持续调整
5. **保持平衡**：奖励和惩罚要平衡，避免极端行为

记住：奖励函数是AI学习的"老师"，好的奖励函数能引导AI学到正确的行为！