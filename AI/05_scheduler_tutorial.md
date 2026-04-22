# 05 - 列车调度器：从小白到实现

这是一份面向零机器学习基础的开发者教程。我会从最基本的概念讲起，最终带你写出一个能训练的列车调度 AI。

---

## 第一部分：你需要理解的核心概念

### 1.1 什么是强化学习？

想象你在训练一只狗：狗做对了给零食，做错了不理它。狗会慢慢学会做什么动作能拿到零食。

强化学习就是这个过程：
- **智能体 (Agent)**：做决策的 AI（我们的列车调度器）
- **环境 (Environment)**：游戏世界（AIWorld）
- **状态 (State)**：AI 看到的世界信息（候车人数、列车位置等）
- **动作 (Action)**：AI 可以做的事（调车、分配列车、加车厢）
- **奖励 (Reward)**：告诉 AI 做得好不好（等待人数减少 = 好，拥堵 = 不好）

训练循环就是反复：**看状态 → 做动作 → 得奖励 → 学习**

### 1.2 什么是 DQN？

DQN = Deep Q-Network。核心思想：

> 对于每个可能的动作，预测一个分数 Q，表示"如果我在当前状态下做这个动作，以后总共能拿多少奖励"。

选动作时，挑 Q 值最高的就行。

问题是：状态太复杂（20 个站点、20 辆列车的各种数值），没法用表格存所有 Q 值。所以用**神经网络**来**近似** Q 值函数——输入状态，输出每个动作的 Q 值。这就是 DQN。

### 1.3 什么是 Dueling DQN？

普通 DQN 把 Q(s,a) 当作一个整体来学。Dueling DQN 把它拆成两部分：

```
Q(s, a) = V(s) + A(s, a)
```

- **V(s)**：这个状态本身有多好（比如"全局拥堵很严重"→ V 很低）
- **A(s, a)**：在这个状态下，每个动作比平均水平好多少

为什么这样更好？因为很多时候**大部分动作都不好，问题在状态本身**。比如一个已经快拥堵的站，无论调哪辆车过去都来不及——先学会判断状态好坏，再学动作差异，收敛更快。

### 1.4 什么是经验回放 (Experience Replay)？

AI 每做一步，得到一个四元组 `(状态s, 动作a, 奖励r, 下一个状态s')`，叫一条**经验**。

把这些经验存进一个大池子（replay buffer），训练时随机从池子里抽一批来学。好处：
- 数据可以重复利用，训练效率高
- 随机抽样打乱了时间顺序，避免相邻经验的相关性干扰学习

### 1.5 什么是 ε-greedy 探索？

训练初期，AI 还不知道什么动作好。如果总挑当前 Q 值最高的动作，可能永远发现不了更好的策略。

解决：以 ε 的概率随机选动作（探索），1-ε 的概率选最优动作（利用）。训练开始时 ε=1.0（完全随机），慢慢衰减到 0.05（几乎不随机）。

---

## 第二部分：把游戏状态变成数字

神经网络只认数字（张量）。`getGameState()` 返回的是字典，需要**编码**成张量。

### 2.1 调度器需要看什么？

调度器只需要关注：
1. **每条线路的压力**：候车人数多不多？列车够不够？载客率高不高？
2. **空闲资源**：还有多少列车/车厢可用？
3. **当前时段**：早高峰和夜间的调度策略完全不同
4. **每辆列车的状态**：在哪条线上？在干嘛？还能调吗？

### 2.2 编码方案

我们不用 GNN（那是线路规划器需要的复杂特征），调度器用更简单的编码就够了：

```python
import torch
import numpy as np

class SchedulerEncoder:
    """把 getGameState() 的输出编码成 PyTorch 张量"""

    def __init__(self, config):
        self.cfg = config
        self.max_lines = config.max_lines       # 7
        self.max_trains = config.max_trains      # 20

    def encode(self, state):
        """
        输入: getGameState() 返回的字典
        输出: 一个一维张量，作为神经网络输入
        """
        features = []

        # --- 1. 全局特征 (11 维) ---
        tick_ratio = state["tick_in_day"] / state["time_of_day"]["day_length"]
        features.append(tick_ratio)

        # 时段 one-hot (7维)
        periods = ["night", "morning_rush", "morning", "midday",
                   "evening_rush", "evening", "late_night"]
        current_period = state["time_of_day"]["period"]
        period_onehot = [1 if p == current_period else 0 for p in periods]
        features.extend(period_onehot)

        # 可用资源占比 (3维)
        features.append(state["available"]["trains"] / self.max_trains)
        features.append(state["available"]["carriages"] / self.cfg.max_carriages)

        # --- 2. 每条线路的特征 (7 条线 × 7 维 = 49 维) ---
        line_features = {}
        for line_info in state["lines"]:
            lf = [
                len(line_info["station_ids"]) / 20,       # 线路长度归一化
                line_info["train_count"] / self.cfg.max_trains_per_line,  # 列车数占比
                0.0,  # 该线路上总候客人数 (需要从站点汇总)
                0.0,  # 该线路上列车平均载客率
                1.0,  # 该线存在 (用 1 标记)
                0.0,  # 该线路上列车是否都在运行
                0.0,  # 该线路是否有空位可加车
            ]
            line_features[line_info["id"]] = lf

        # 填充线路相关数据
        # 先统计每条线路的候客人数 (从站点汇总)
        station_line_waiting = {}  # line_id -> total waiting
        for station in state["stations"]:
            for lid in station["connecting_lines"]:
                station_line_waiting.setdefault(lid, 0)
                station_line_waiting[lid] += station["passenger_count"]

        for line_info in state["lines"]:
            lid = line_info["id"]
            lf = line_features[lid]
            lf[2] = station_line_waiting.get(lid, 0) / self.cfg.overcrowd_limit

            # 统计该线列车载客率
            line_trains = [t for t in state["trains"] if t["line_id"] == lid]
            if line_trains:
                avg_load = np.mean([t["passenger_count"] / max(t["capacity"], 1)
                                    for t in line_trains])
                lf[3] = avg_load
                all_running = all(t["status"] == 4 for t in line_trains)
                lf[5] = 1.0 if all_running else 0.0

            has_slot = line_info["train_count"] < line_info.get("max_trains", 2)
            lf[6] = 1.0 if has_slot else 0.0

        # 按线路 ID 排序，没有的线路填零
        for lid in range(self.max_lines):
            if lid in line_features:
                features.extend(line_features[lid])
            else:
                features.extend([0.0] * 7)  # 不存在的线路用零填充

        # --- 3. 每辆列车的特征 (20 辆车 × 6 维 = 120 维) ---
        train_feature_list = []
        for train in state["trains"]:
            tf = [
                train["line_id"] / self.max_lines if train["line_id"] is not None else -1,
                train["status"] / 6,   # 状态码归一化
                train["direction"] if train["direction"] is not None else 0,
                train["passenger_count"] / max(train["capacity"], 1),  # 载客率
                train["carriage_count"] / 3,  # 车厢数归一化
                1 if train["status"] == 3 else 0,  # 是否空闲(可调)
            ]
            train_feature_list.append(tf)

        # 补零到 max_trains
        while len(train_feature_list) < self.max_trains:
            train_feature_list.append([0.0] * 6)
        # 只取前 max_trains
        for tf in train_feature_list[:self.max_trains]:
            features.extend(tf)

        # --- 4. 站点拥堵概要 (6 维：每类别的最大候车数) ---
        categories = ["residential", "commercial", "office", "hospital", "scenic", "school"]
        for cat in categories:
            cat_stations = [s for s in state["stations"] if s["category"] == cat]
            max_wait = max((s["passenger_count"] for s in cat_stations), default=0)
            features.append(max_wait / self.cfg.overcrowd_limit)

        # 总维度: 11 + 49 + 120 + 6 = 186
        return torch.tensor(features, dtype=torch.float32)
```

**为什么这样编码？** 每个特征都是归一化到 0~1 之间的小数。神经网络不喜欢大数字（比如坐标 -400），归一化后学习更稳定。

---

## 第三部分：定义动作空间

调度器可以做的动作有 4 类：

| 动作类型 | 说明 | 条件 |
|----------|------|------|
| 不操作 | 这一步什么都不做 | 始终可选 |
| 分配列车 | 从车库派一辆车到某条线路 | 有空闲列车 + 目标线未满 |
| 调车 | 把一辆车从一条线调到另一条 | 该车空闲 + 目标线未满 |
| 加车厢 | 给某辆列车加一节车厢 | 有空闲车厢 |

### 3.1 动作编号

```python
class ActionSpace:
    """
    动作编号方案:
      0           : 不操作
      1 ~ L       : 分配列车到线路 0 ~ L-1
      L+1 ~ L+L   : 给线索引 0~L-1 上的第一辆空闲列车加车厢
      L+L+1 ~ ... : 调车 (train, target_line) 对

    实际实现中，我们简化为只考虑"给某条线路加车/加车厢"，
    调车动作由规则触发（当某线压力过小时自动调出）。
    """

    def __init__(self, max_lines=7):
        self.max_lines = max_lines
        # 简化动作空间: 不操作 + 给每条线分配列车 + 给每条线加车厢
        # 总共 1 + 7 + 7 = 15 个动作
        self.n_actions = 1 + max_lines * 2

    def get_action_meaning(self, action_id):
        if action_id == 0:
            return "noop"
        elif 1 <= action_id <= self.max_lines:
            return f"employ_train_to_line_{action_id - 1}"
        else:
            line_idx = action_id - 1 - self.max_lines
            return f"add_carriage_to_line_{line_idx}"

    def get_valid_mask(self, state_dict):
        """返回一个 boolean 数组，标记哪些动作当前合法"""
        mask = [True]  # 不操作始终合法

        available_trains = state_dict["available"]["trains"]
        available_carriages = state_dict["available"]["carriages"]

        # 线路信息
        line_train_count = {}
        line_max_trains = {}
        line_has_train = {}
        for line_info in state_dict["lines"]:
            lid = line_info["id"]
            line_train_count[lid] = line_info["train_count"]
            line_max_trains[lid] = line_info.get("max_trains", 2)
            line_has_train[lid] = line_info["train_count"] > 0

        for lid in range(self.max_lines):
            # 分配列车到线路 lid
            can_employ = (available_trains > 0 and
                         lid in line_train_count and
                         line_train_count[lid] < line_max_trains.get(lid, 2))
            mask.append(can_employ)

        for lid in range(self.max_lines):
            # 给线路 lid 上的列车加车厢
            can_add = (available_carriages > 0 and
                      lid in line_has_train and
                      line_has_train[lid])
            mask.append(can_add)

        # 补齐到 n_actions
        while len(mask) < self.n_actions:
            mask.append(False)

        return mask
```

**为什么简化动作空间？** 完整的调车动作空间是 168 维（20 辆车 × 7 条线），这对新手太难训练。先从 15 维开始能跑起来，后面再扩展。

---

## 第四部分：Dueling DQN 网络结构

```python
import torch
import torch.nn as nn

class DuelingDQN(nn.Module):
    """
    Dueling DQN 网络

    输入: 编码后的状态向量 (186 维)
    输出: 每个动作的 Q 值 (15 维)
    """

    def __init__(self, state_dim=186, n_actions=15, hidden_dim=256):
        super().__init__()

        # 共享特征提取层
        self.feature_layer = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
        )

        # 价值流 V(s): 状态本身有多好 → 输出 1 个标量
        self.value_stream = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 1),
        )

        # 优势流 A(s,a): 每个动作比平均水平好多少 → 输出 n_actions 个标量
        self.advantage_stream = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, n_actions),
        )

    def forward(self, x):
        features = self.feature_layer(x)
        value = self.value_stream(features)           # (batch, 1)
        advantage = self.advantage_stream(features)    # (batch, n_actions)

        # Q(s,a) = V(s) + A(s,a) - mean(A(s,a))
        # 减去均值是为了让 V 和 A 的分工更明确
        q_values = value + advantage - advantage.mean(dim=-1, keepdim=True)
        return q_values
```

**网络结构解读**：
- 输入 186 维状态 → 经过两层 256 维的全连接层提取特征
- 然后分成两路：一路算 V(s)（1 个数），一路算 A(s,a)（15 个数）
- 合并成 Q(s,a) = V(s) + A(s,a) - mean(A)

---

## 第五部分：经验回放缓冲区

```python
import random
from collections import deque

class ReplayBuffer:
    """存储和采样训练经验"""

    def __init__(self, capacity=100000):
        self.buffer = deque(maxlen=capacity)

    def push(self, state, action, reward, next_state, done):
        """存入一条经验"""
        self.buffer.append((state, action, reward, next_state, done))

    def sample(self, batch_size):
        """随机采样一批经验"""
        batch = random.sample(self.buffer, batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)
        return (
            torch.stack(states),
            torch.tensor(actions, dtype=torch.long),
            torch.tensor(rewards, dtype=torch.float32),
            torch.stack(next_states),
            torch.tensor(dones, dtype=torch.float32),
        )

    def __len__(self):
        return len(self.buffer)
```

---

## 第六部分：DQN 智能体

```python
class DQNAgent:
    """Dueling DQN 智能体"""

    def __init__(self, state_dim=186, n_actions=15, config=None):
        self.n_actions = n_actions
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # 在线网络 (每步更新)
        self.online_net = DuelingDQN(state_dim, n_actions).to(self.device)
        # 目标网络 (定期从在线网络复制，稳定训练)
        self.target_net = DuelingDQN(state_dim, n_actions).to(self.device)
        self.target_net.load_state_dict(self.online_net.state_dict())
        self.target_net.eval()  # 目标网络不参与梯度计算

        self.optimizer = torch.optim.Adam(self.online_net.parameters(), lr=1e-4)
        self.buffer = ReplayBuffer(capacity=100000)

        # 超参数
        self.gamma = 0.99           # 折扣因子：未来的奖励打多少折扣
        self.epsilon = 1.0          # 探索率：随机选动作的概率
        self.eps_min = 0.05         # 最低探索率
        self.eps_decay = 0.9995     # 每步衰减乘数
        self.batch_size = 64
        self.target_update_freq = 500  # 每 500 步更新目标网络
        self.step_count = 0

    def select_action(self, state_tensor, valid_mask):
        """
        选择动作 (ε-greedy)

        Args:
            state_tensor: 编码后的状态 (1, state_dim)
            valid_mask: list[bool], 哪些动作合法
        """
        # ε-greedy: 以 ε 概率随机探索
        if random.random() < self.epsilon:
            valid_actions = [i for i, v in enumerate(valid_mask) if v]
            return random.choice(valid_actions)

        # 否则选 Q 值最高的合法动作
        with torch.no_grad():
            q_values = self.online_net(state_tensor.to(self.device))
            # 非法动作的 Q 值设为极小值
            mask_tensor = torch.tensor(valid_mask, dtype=torch.bool).to(self.device)
            q_values[~mask_tensor] = -1e9
            return q_values.argmax().item()

    def update(self):
        """从 buffer 采样并更新网络"""
        if len(self.buffer) < self.batch_size:
            return  # 经验不够，不更新

        states, actions, rewards, next_states, dones = self.buffer.sample(self.batch_size)
        states = states.to(self.device)
        actions = actions.to(self.device)
        rewards = rewards.to(self.device)
        next_states = next_states.to(self.device)
        dones = dones.to(self.device)

        # 当前 Q 值: Q(s, a)
        current_q = self.online_net(states).gather(1, actions.unsqueeze(1)).squeeze(1)

        # 目标 Q 值: r + γ * max_a' Q_target(s', a')
        with torch.no_grad():
            next_q = self.target_net(next_states).max(dim=1)[0]
            target_q = rewards + self.gamma * next_q * (1 - dones)

        # 计算损失 (Huber Loss, 比 MSE 更鲁棒)
        loss = nn.SmoothL1Loss()(current_q, target_q)

        # 反向传播
        self.optimizer.zero_grad()
        loss.backward()
        # 梯度裁剪 (防止梯度爆炸)
        torch.nn.utils.clip_grad_norm_(self.online_net.parameters(), 10)
        self.optimizer.step()

        # 定期更新目标网络
        self.step_count += 1
        if self.step_count % self.target_update_freq == 0:
            self.target_net.load_state_dict(self.online_net.state_dict())

        # ε 衰减
        self.epsilon = max(self.eps_min, self.epsilon * self.eps_decay)

        return loss.item()
```

**关键概念解释**：

- **目标网络**：如果用同一个网络算当前 Q 和目标 Q，目标会随着网络更新一直在变，学不稳定。所以用另一个"冻结"的网络来算目标，定期从在线网络复制参数。
- **γ (gamma)**：折扣因子。γ=0.99 意味着 100 步后的奖励只考虑 0.99^100 ≈ 0.37 倍。让 AI 更看重眼前奖励，但也考虑未来。
- **SmoothL1Loss**：比 MSE 更温和的损失函数，大误差线性增长（不会爆炸），小误差平方增长（精确拟合）。

---

## 第七部分：奖励函数

奖励是 AI 的"指挥棒"，你给什么奖励，AI 就学什么。

```python
class RewardCalculator:
    """计算调度器的差分奖励"""

    def __init__(self, overcrowd_limit=50):
        self.overcrowd_limit = overcrowd_limit
        self.prev_total_waiting = None
        self.prev_at_risk = None

    def reset(self):
        """每个 episode 开始时调用"""
        self.prev_total_waiting = None
        self.prev_at_risk = None

    def compute(self, state_dict):
        """
        计算当前状态的奖励

        核心原则：用差分（变化量）而非绝对值，让 AI 学到"我的决策是否改善了局面"
        """
        reward = 0.0

        # --- 统计当前指标 ---
        total_waiting = state_dict["metrics"]["total_waiting"]
        at_risk = state_dict["metrics"]["at_risk_stations"]
        arrived_delta = 0  # 这一步新到达的乘客数 (差分计算需要记录)

        # 第一次调用，只记录基线
        if self.prev_total_waiting is None:
            self.prev_total_waiting = total_waiting
            self.prev_at_risk = at_risk
            return 0.0

        # 1. 等待人数变化 (+2 分/改善)
        waiting_change = self.prev_total_waiting - total_waiting
        reward += 2.0 * (waiting_change / self.overcrowd_limit)

        # 2. 拥堵风险站变化 (+3 分/改善)
        risk_change = self.prev_at_risk - at_risk
        reward += 3.0 * risk_change

        # 3. 游戏结束大惩罚
        if state_dict["game_over"]:
            reward -= 50.0

        # 更新记录
        self.prev_total_waiting = total_waiting
        self.prev_at_risk = at_risk

        return reward
```

**为什么用差分奖励？** 如果奖励 = "当前等待人数"，AI 可能学会什么都不做（因为做了可能更差）。用差分 = "等待人数减少了多少"，AI 学会"做什么能让局面变好"。

---

## 第八部分：动作执行（把动作编号变成游戏操作）

```python
class ActionExecutor:
    """把动作编号翻译成对 AIWorld 的调用"""

    def __init__(self, max_lines=7):
        self.max_lines = max_lines

    def execute(self, action_id, world, state_dict):
        """
        执行动作

        Args:
            action_id: 动作编号
            world: AIWorld 实例
            state_dict: 当前游戏状态

        Returns:
            bool: 是否成功执行
        """
        if action_id == 0:
            return True  # 不操作

        # 分配列车到线路
        if 1 <= action_id <= self.max_lines:
            line_idx = action_id - 1
            return self._employ_train(world, state_dict, line_idx)

        # 给线路上的列车加车厢
        if self.max_lines + 1 <= action_id <= self.max_lines * 2:
            line_idx = action_id - 1 - self.max_lines
            return self._add_carriage(world, state_dict, line_idx)

        return False

    def _employ_train(self, world, state_dict, line_idx):
        """从车库分配列车到指定线路"""
        line_info = self._find_line_by_idx(state_dict, line_idx)
        if line_info is None:
            return False

        line = world.findLineById(line_info["id"])
        if line is None:
            return False

        # 选该线路的第一个站点作为上车站
        if not line_info["station_ids"]:
            return False
        station = world.findStationById(line_info["station_ids"][0])
        if station is None:
            return False

        try:
            train = world.playerEmployTrain(line, station, direction=True)
            return train is not None
        except Exception:
            return False

    def _add_carriage(self, world, state_dict, line_idx):
        """给指定线路上的一辆列车加车厢"""
        line_info = self._find_line_by_idx(state_dict, line_idx)
        if line_info is None:
            return False

        # 找该线路上的一辆车
        train_id = None
        for train_info in state_dict["trains"]:
            if train_info["line_id"] == line_info["id"]:
                train_id = train_info["id"]
                break

        if train_id is None:
            return False

        train = world.findTrainById(train_id)
        if train is None:
            return False

        try:
            result = world.playerConnectCarriage(train)
            return result is not None
        except Exception:
            return False

    def _find_line_by_idx(self, state_dict, line_idx):
        """按索引找线路信息"""
        lines = sorted(state_dict["lines"], key=lambda l: l["id"])
        if line_idx < len(lines):
            return lines[line_idx]
        return None
```

---

## 第九部分：完整训练循环

把所有零件拼起来：

```python
from ai_world import AIWorld
from game_config import GameConfig

def train_scheduler(num_episodes=5000):
    """
    训练列车调度器

    每个 episode = 一天 (1200 tick)
    """

    # --- 初始化 ---
    cfg = GameConfig.for_ai_training()
    encoder = SchedulerEncoder(cfg)
    action_space = ActionSpace(max_lines=cfg.max_lines)
    agent = DQNAgent(
        state_dim=186,
        n_actions=action_space.n_actions,
    )
    executor = ActionExecutor(max_lines=cfg.max_lines)
    reward_calc = RewardCalculator(overcrowd_limit=cfg.overcrowd_limit)

    # 训练日志
    episode_rewards = []
    best_avg_reward = -float('inf')

    for episode in range(num_episodes):
        # --- 1. 重置环境 ---
        world = AIWorld(cfg)
        world.setup()

        # 用规则生成线路 (训练调度器时先用简单规则)
        rule_based_build_lines(world)

        # 放初始列车
        initial_placements = rule_based_place_trains(world)
        world.place_initial_trains(initial_placements)
        world.lock_lines()

        # --- 2. 运行一天 ---
        reward_calc.reset()
        state_dict = world.getGameState()
        state_tensor = encoder.encode(state_dict).unsqueeze(0)  # (1, 186)
        episode_reward = 0
        decision_step = 0

        for tick in range(cfg.day_length):
            if world.game_over:
                break

            world.updateOneTick()

            # 每 60 tick 决策一次
            if tick > 0 and tick % 60 == 0:
                # 获取新状态
                next_state_dict = world.getGameState()
                next_state_tensor = encoder.encode(next_state_dict).unsqueeze(0)

                # 计算奖励
                reward = reward_calc.compute(next_state_dict)

                # 存经验
                done = world.game_over
                agent.buffer.push(
                    state_tensor.squeeze(0),
                    last_action,
                    reward,
                    next_state_tensor.squeeze(0),
                    done
                )

                # 选择新动作
                valid_mask = action_space.get_valid_mask(next_state_dict)
                action = agent.select_action(next_state_tensor, valid_mask)
                executor.execute(action, world, next_state_dict)

                # 更新网络
                agent.update()

                # 记录
                episode_reward += reward
                state_tensor = next_state_tensor
                last_action = action
                decision_step += 1

        # --- 3. Episode 结束 ---
        episode_rewards.append(episode_reward)

        # 打印进度
        if (episode + 1) % 50 == 0:
            avg_reward = np.mean(episode_rewards[-50:])
            print(f"Episode {episode+1}/{num_episodes} | "
                  f"Avg Reward: {avg_reward:.2f} | "
                  f"Epsilon: {agent.epsilon:.3f} | "
                  f"Steps: {agent.step_count}")

            # 保存最佳模型
            if avg_reward > best_avg_reward:
                best_avg_reward = avg_reward
                torch.save({
                    'online_net': agent.online_net.state_dict(),
                    'target_net': agent.target_net.state_dict(),
                    'optimizer': agent.optimizer.state_dict(),
                    'epsilon': agent.epsilon,
                    'episode': episode,
                    'avg_reward': avg_reward,
                }, 'AI/checkpoints/best_scheduler.pt')

    return agent


# --- 辅助函数: 规则建线 (用于调度器训练) ---

def rule_based_build_lines(world):
    """用简单规则建线，给调度器训练用"""
    # 按类别分组
    from station import CATEGORY_RESIDENTIAL, CATEGORY_OFFICE, CATEGORY_COMMERCIAL
    from station import CATEGORY_SCHOOL, CATEGORY_HOSPITAL, CATEGORY_SCENIC

    stations = world.stations
    category_groups = {}
    for s in stations:
        category_groups.setdefault(s.category, []).append(s)

    # 简单策略: 把居民区→办公区→商业区串成线
    # 这只是训练调度器的辅助，线路规划器后面会单独训练
    lines_built = []
    residential = category_groups.get(CATEGORY_RESIDENTIAL, [])
    office = category_groups.get(CATEGORY_OFFICE, [])
    commercial = category_groups.get(CATEGORY_COMMERCIAL, [])
    school = category_groups.get(CATEGORY_SCHOOL, [])
    hospital = category_groups.get(CATEGORY_HOSPITAL, [])
    scenic = category_groups.get(CATEGORY_SCENIC, [])

    # 建几条简单的线
    if len(residential) >= 2 and len(office) >= 2:
        line_stations = residential[:3] + office[:3]
        lines_built.append(line_stations)

    if len(residential) >= 3 and len(commercial) >= 2:
        line_stations = residential[2:5] + commercial[:2]
        lines_built.append(line_stations)

    if len(office) >= 2 and len(commercial) >= 2:
        line_stations = office[1:3] + commercial[1:3]
        lines_built.append(line_stations)

    if len(school) >= 2 and residential:
        line_stations = school[:2] + [residential[0]]
        lines_built.append(line_stations)

    if hospital and residential:
        line_stations = hospital[:1] + residential[:2]
        lines_built.append(line_stations)

    if scenic and residential:
        line_stations = scenic[:2] + residential[3:5]
        lines_built.append(line_stations)

    for station_list in lines_built:
        world.playerNewLine(station_list)


def rule_based_place_trains(world):
    """给每条线路放初始列车"""
    placements = []
    for line in world.metroLine:
        if len(line.stationList) >= 2:
            # 每条线放 1 辆车 (最多 2 辆)
            first_station = line.stationList[0]
            placements.append({
                "line_id": line.number,
                "station_id": first_station.id,
                "direction": True,
            })
            # 如果线路够长，放第二辆
            if len(line.stationList) >= 4 and line.trainNm < 2:
                last_station = line.stationList[-1]
                placements.append({
                    "line_id": line.number,
                    "station_id": last_station.id,
                    "direction": False,
                })
    return placements


if __name__ == "__main__":
    train_scheduler(num_episodes=5000)
```

---

## 第十部分：训练过程会发生什么？

### 训练曲线解读

训练时关注两个指标：

1. **平均奖励**：应该逐渐上升（说明 AI 越来越会调度了）
2. **ε 值**：应该逐渐下降（从随机探索过渡到利用学到的策略）

典型训练过程：

```
Episode   50 | Avg Reward: -12.3 | Epsilon: 0.953   ← 还在随机乱试
Episode  200 | Avg Reward:  -5.1 | Epsilon: 0.814   ← 开始学到一点
Episode  500 | Avg Reward:   2.7 | Epsilon: 0.606   ← 明显改善
Episode 1000 | Avg Reward:   8.4 | Epsilon: 0.368   ← 稳定提升
Episode 2000 | Avg Reward:  15.2 | Epsilon: 0.135   ← 接近收敛
Episode 5000 | Avg Reward:  22.1 | Epsilon: 0.050   ← 收敛
```

### 奖励是什么含义？

- 正值 = 好决策（等待人数在减少、拥堵在缓解）
- 负值 = 坏决策（做了无效操作、或没及时处理拥堵）
- -50 = 游戏结束（某站过度拥堵）

---

## 第十一部分：怎么测试训练好的模型？

```python
def evaluate_scheduler(agent, num_episodes=10):
    """测试训练好的调度器"""

    cfg = GameConfig.for_ai_training()
    encoder = SchedulerEncoder(cfg)
    action_space = ActionSpace(max_lines=cfg.max_lines)
    executor = ActionExecutor(max_lines=cfg.max_lines)

    # 关闭探索
    agent.epsilon = 0.0

    for ep in range(num_episodes):
        world = AIWorld(cfg)
        world.setup()
        rule_based_build_lines(world)
        world.place_initial_trains(rule_based_place_trains(world))
        world.lock_lines()

        # 运行一天
        report = world.run_one_day(ai_callback=lambda w: _scheduler_step(
            w, agent, encoder, action_space, executor
        ))

        print(f"\n--- 测试 Episode {ep+1} ---")
        print(f"存活: {'是' if report['survived'] else '否'}")
        print(f"到达乘客: {report['passengers_arrived_today']}")
        print(f"平均等待: {report['avg_waiting_time']} tick")
        print(f"拥堵风险站: {report['at_risk_stations']}")
        print(f"利润: {report['profit']}")
        print(f"覆盖率: {report['overall_coverage_ratio']*100:.1f}%")


def _scheduler_step(world, agent, encoder, action_space, executor):
    """调度回调: 每次 AI 调用时执行"""
    state_dict = world.getGameState()
    state_tensor = encoder.encode(state_dict).unsqueeze(0)
    valid_mask = action_space.get_valid_mask(state_dict)
    action = agent.select_action(state_tensor, valid_mask)
    executor.execute(action, world, state_dict)
```

---

## 第十二部分：常见问题与调试

### Q1: 训练几百 episode 了奖励还是不涨？

可能原因和对策：
- **ε 衰减太快**：尝试把 `eps_decay` 从 0.9995 改成 0.9998（更慢衰减）
- **奖励太稀疏**：AI 做什么都不给奖励。检查 `RewardCalculator.compute()` 是否真的返回了有效奖励
- **学习率太大**：把 `lr=1e-4` 改成 `lr=5e-5`

### Q2: 训练中 loss 变成 NaN？

- 降低学习率
- 检查奖励值是否爆炸（加 `np.clip(reward, -10, 10)`）
- 确认状态编码没有 NaN 或 Inf

### Q3: AI 总是选"不操作"？

- 检查其他动作是否被 valid_mask 全部屏蔽了
- 增加"不操作"的小惩罚：`reward -= 0.1`（每次不操作）
- 确保奖励信号真的区别了"操作比不操作好"

### Q4: 怎么知道 AI 学到了有意义的东西？

- 看它的动作分布：如果前期全选"不操作"，后期开始主动分配→说明在学
- 看测试时的结算报告：到达乘客数和利润是否提升
- 在 TensorBoard 中画奖励曲线（加几行 `torch.utils.tensorboard` 代码）

### Q5: 需要 GPU 吗？

这个网络很小（186 输入，256 隐藏，15 输出），CPU 就能跑。但每个 episode 要模拟 1200 tick 的游戏，游戏模拟才是瓶颈。GPU 主要用来加速神经网络更新，但这里更新很快，所以 CPU 就够。

---

## 代码文件总结

```
AI/src/
├── scheduler_encoder.py     # 第二部分: 状态编码器
├── action_space.py          # 第三部分: 动作空间定义
├── dueling_dqn.py           # 第四部分: 网络结构
├── replay_buffer.py         # 第五部分: 经验回放
├── dqn_agent.py             # 第六部分: DQN 智能体
├── reward.py                # 第七部分: 奖励函数
├── action_executor.py       # 第八部分: 动作执行器
└── train_scheduler.py       # 第九部分: 训练循环
```

实现顺序建议：
1. 先写编码器和动作空间，手动测试编码是否正确
2. 写网络结构和 buffer
3. 写 Agent 和奖励函数
4. 写训练循环，跑起来
5. 观察训练曲线，调参
