# 04 - 训练框架与奖励设计

## 训练架构总览

线路规划器和列车调度器不能独立训练——线路规划决定了调度的难度，调度的效果反映了规划的质量。但联合训练两个网络风险太高（一个不收敛会拖垮另一个），所以采用**分阶段训练 → 联合微调**的策略。

## 阶段 1：线路规划器预训练

### 目标
让线路规划器学会生成"结构合理"的线路，不要求最优，但要求覆盖所有类别且有换乘点。

### 方法：行为克隆 (Behavior Cloning) → RL 微调

**Step 1: 用规则生成的"专家数据"做行为克隆**

虽然最终要 RL，但纯 RL 从零学习组合优化极其低效。先用规则生成一批合理的线路规划作为"伪专家数据"：

```
规则线路生成器（启发式，非 ML）:
  1. 按 O-D 权重排序所有 (category_A, category_B) 对
  2. 对权重最高的 O-D 对，找最短连接路径，生成一条线路
  3. 标记已覆盖站点，对下个 O-D 对重复
  4. 直到线路额度用完或所有 O-D 对已覆盖
```

采集 10000 组 (站点布局 → 线路规划) 对，训练 Pointer Network 做监督学习。

**Step 2: PPO 微调**

在行为克隆的初始化基础上，用 PPO 做在线微调：
- 每次规划后放入环境运行 300 tick（一天）
- 用 02_line_planner.md 中的奖励信号更新策略
- 初始 learning rate 降低到 1e-5（避免破坏已学到的知识）

### 数据增强

城市生成器本身就有随机性，每次生成不同的站点布局就是天然的训练数据。额外增强：
- 站点坐标添加高斯噪声（σ=10）
- 随机丢弃 1-2 个站点
- 站点类别保持不变，位置打乱

## 阶段 2：列车调度器训练

### 目标
在固定线路规划下，学会动态分配列车和车厢资源。

### 方法：Dueling DQN 从零训练

调度器不需要行为克隆初始化，因为：
1. 动作空间是离散的、有限的
2. 环境反馈即时（等待人数变化可以马上观测到）
3. ε-greedy 足以提供初始探索

但是需要一个合理的线路规划来做训练环境。用阶段 1 训好的线路规划器生成环境。

### 训练配置

| 参数 | 值 |
|------|-----|
| Replay buffer 大小 | 100,000 |
| Batch size | 64 |
| Learning rate | 1e-4 |
| γ (折扣因子) | 0.99 |
| ε 起始 / 终止 | 1.0 / 0.05 |
| ε 衰减步数 | 50,000 |
| Target network 更新频率 | 1,000 steps |
| τ (软更新系数) | 0.005 |
| PER α | 0.6 |
| PER β (起始/终止) | 0.4 / 1.0 |

### Episode 设计

每个 episode：
1. 用城市生成器生成地图
2. 用线路规划器生成初始线路
3. 运行调度器直到 game_over 或 1500 tick
4. 重启

每个 episode 的总奖励 = Σ(r_t * γ^t)，用于评估调度策略的质量。

## 阶段 3：联合微调

### 目标
两个网络协同工作，线路规划器根据调度效果调整规划。

### 方法：交替训练

```
repeat:
  # 冻结调度器，更新规划器
  for i in range(5):
    生成线路规划
    固定调度器运行环境 300 tick
    计算规划器奖励，PPO 更新规划器

  # 冻结规划器，更新调度器
  for i in range(20):
    固定规划器生成线路
    调度器运行并采集经验
    Dueling DQN 更新

  # 每 10 轮联合微调
  两个网络同时解冻，降低 learning rate (0.1x)
  端到端运行，两网络各自接收自己的奖励信号
```

### 奖励信号的归属

两个网络共享环境，但奖励需要合理归属：

- **线路规划器的奖励**：关注长期、结构性指标（类别覆盖率、O-D 可达性、换乘便利度、存活 tick 数）
- **调度器的奖励**：关注短期、操作性指标（等待人数变化、载客效率、拥堵避免）

关键原则：**不给调度器奖励因为线路规划差而导致的惩罚**——这不公平，调度器无法改变线路结构。

## 与游戏环境的交互接口

### 训练循环

```python
class TrainingEnv:
    """训练环境封装 MetroWorld"""

    def reset(self):
        self.world = MetroWorld(config=self.config)
        self.world.setup()
        # 用线路规划器生成初始线路
        self._plan_initial_lines()
        return self._get_observation()

    def step(self, action):
        """执行一个调度动作，运行 10 tick，返回 (obs, reward, done)"""
        self._execute_action(action)
        for _ in range(10):
            self.world.updateOneTick()
            if self.world.game_over:
                break
        obs = self._get_observation()
        reward = self._compute_reward()
        return obs, reward, self.world.game_over

    def _get_observation(self):
        state = self.world.getGameState()
        return self.state_encoder.encode(state)

    def _compute_reward(self):
        # 差分奖励，详见各模块的奖励设计
        ...
```

### 模型保存与加载

- 每 1000 episode 保存 checkpoint
- 保存内容：两个网络的权重、优化器状态、训练步数、最佳 reward
- 命名：`checkpoint_line_planner_ep5000.pt`, `checkpoint_scheduler_ep5000.pt`

## 硬件与资源估算

| 资源 | 用途 | 估算 |
|------|------|------|
| GPU | GNN + Pointer Network + DQN 训练 | 1x RTX 3090 或同等级 |
| 内存 | Replay buffer (100K × obs_size) | ~4 GB |
| 磁盘 | Checkpoints + 训练日志 | ~10 GB |
| 训练时间 (阶段1) | 线路规划器 | ~4-8 小时 |
| 训练时间 (阶段2) | 列车调度器 | ~8-16 小时 |
| 训练时间 (阶段3) | 联合微调 | ~4-8 小时 |

## 评估指标

| 指标 | 说明 | 目标 |
|------|------|------|
| 存活 tick 中位数 | 单次 episode 存活多久 | > 800 tick |
| 类别覆盖率 | 各类别站点被线路覆盖的比例 | > 90% |
| 平均等待时间 | 乘客从等待到上车的 tick 数 | < 30 tick |
| 列车利用率 | 列车载客率均值 | 40%-70% |
| 拥堵率 | 拥堵风险站在全部站中的比例 | < 10% |
| 到达率 | 乘客成功到达目的地的比例 | > 80% |

## 可视化训练进度

用 TensorBoard 记录：
- 每个 episode 的总奖励
- 各奖励分项的变化趋势
- ε 值衰减曲线
- 存活 tick 数分布
- 动作分布（调度器各类动作的频率）

## 目录结构规划

```
AI/
├── README.md                    # 架构总览 (已有)
├── 01_state_encoding.md         # 状态表示 (已有)
├── 02_line_planner.md           # 线路规划器 (已有)
├── 03_train_scheduler.md        # 列车调度器 (已有)
├── 04_training_framework.md     # 训练框架 (本文件)
│
├── src/                         # 源代码 (待实现)
│   ├── state_encoder.py         # GNN 状态编码器
│   ├── line_planner.py          # 线路规划器 (Pointer Network + PPO)
│   ├── train_scheduler.py       # 列车调度器 (Dueling DQN)
│   ├── training_env.py          # 训练环境封装
│   ├── reward.py                # 奖励函数
│   ├── rule_based_planner.py    # 规则规划器 (用于行为克隆)
│   └── models/                  # 网络模型定义
│       ├── gnn_encoder.py
│       ├── pointer_network.py
│       └── dueling_dqn.py
│
├── train.py                     # 训练入口脚本
├── evaluate.py                  # 评估脚本
└── checkpoints/                 # 模型检查点
```
