# 03 - 列车调度器算法设计

## 问题定义

每 60 tick（约 1 小时）观察一次环境状态，决定：
1. 是否将列车从一条线调到另一条线（playerTrainShunt）
2. 是否从车库分配列车到某条线（playerEmployTrain）
3. 是否给某列车加车厢（playerConnectCarriage）

约束：
- 列车总数有限（max_trains=20, max_carriages=40）
- 每条线路最多 2 辆列车同时运营（max_trains_per_line=2）
- 调车有冷却时间（同线 15 tick / 跨线 30 tick）
- 决策要有惯性避免振荡
- 一天共 1200 tick，20 个决策步

**关键约束**：线路在规划阶段已锁定，调度器只能做资源调度（调车、分配列车、加车厢），不能改线路。

## 算法选择：注意力驱动的线路级决策 + Dueling DQN

### 为什么是线路级视角

每条线路可以看作一个"资源需求方"，它需要列车和车厢。"调车"本质上是把资源从低需求线路转移到高需求线路。各线路的需求是动态且相互竞争的。

### 为什么用 DQN 而非策略梯度

- 调度动作是**离散的**（调车/不调车、分配到哪条线、加不加车厢），DQN 天然适合
- DQN 的经验回放可以高效利用历史数据
- 调度决策之间有独立性（同时给两条线加列车不冲突），适合并行 Q 值估计

### 模型架构

```
输入:
  - GNN 节点嵌入 (N, 64)
  - 全局特征 (145)
  - 列车嵌入 (M, 80)
      │
      ▼
┌───────────────────────────────────────────────┐
│  线路需求评估器                                │
│                                                │
│  对每条线路 l:                                  │
│    line_stations_embed = 聚合该线路上所有站点嵌入 │
│                         = mean(node_embed[line_stations])  (64) │
│    line_trains_info = 聚合该线路上列车嵌入       │
│                      = mean(train_embed[on_line_l]) (80)        │
│    line_feature = concat(line_stations_embed,  │
│                          line_trains_info,     │
│                          [train_count/max_trains_per_line,      │
│                           avg_load_ratio,      │
│                           total_waiting_on_line])               │
│                → MLP(64+80+3 → 128)            │
│                                                │
│  线路间注意力:                                   │
│    对所有线路的 128 维特征，做多头自注意力         │
│    让每条线路"看到"其他线路的状态，               │
│    理解全局资源竞争关系                           │
│    → MultiHeadAttention(128, num_heads=4)       │
│    → 每条线路的上下文感知特征 (128)               │
└───────────────────────────────────────────────┘
      │
      ▼
┌───────────────────────────────────────────────┐
│  动作决策头 (3 个并行头)                         │
│                                                │
│  头1: 分配列车 (playerEmployTrain)              │
│    Q(line_l) = MLP(context_l, global) → 标量   │
│    动作: argmax_l Q(l) 当 available_train > 0   │
│          且 line_l.train_count < max_trains_per_line │
│    或 "不分配"                                  │
│                                                │
│  头2: 调车 (playerTrainShunt)                  │
│    Q(train_m, target_line_l) = MLP(train_m,    │
│                                    context_l)  │
│                                  → 标量         │
│    动作: argmax_{m,l} Q(m,l) 的有效调车方案      │
│    约束: target_line_l 列车数 < max_trains_per_line │
│    或 "不调车"                                  │
│                                                │
│  头3: 加车厢 (playerConnectCarriage)            │
│    Q(train_m) = MLP(train_m, global) → 标量    │
│    动作: argmax_m Q(m) 当 available_carriage>0  │
│    或 "不加车厢"                                │
└───────────────────────────────────────────────┘
```

### 动作空间详情

每个决策步，调度器最多执行 1 个动作（保守策略，避免连锁反应）：

```
动作枚举:
  0: 不操作（等待观察）
  1..L: 从车库分配列车到线路 1..L
  L+1..L+M: 给列车 1..M 加车厢
  L+M+1..L+M+M*L: 将列车 m 调到线路 l

总动作数: 1 + L + M + M*L (约 1+7+20+140 = 168)
```

实际可用动作用**动作掩码**（action mask）过滤：
- available_trains == 0 → 掩码所有分配动作
- available_carriages == 0 → 掩码所有加车厢动作
- 列车正在 shunting/running → 掩码该车调车动作（调车需要列车空闲）
- 目标线路列车数已达 max_trains_per_line (2) → 掩码该线的分配/调车动作

### 时段感知机制

调度器必须在时段切换前预判。一天 1200 tick 有 7 个时段（见 daily_periods 配置）：

```
时段嵌入 = Embedding(period_id, dim=16) + Embedding(next_period_id, dim=16)
```

这 32 维特征拼入全局特征。模型通过训练学习：
- 早高峰 (tick 240~420) 前将列车调到居民→办公/学校线路
- 晚高峰 (tick 720~900) 前将列车调到办公→居民线路
- 夜间 (tick 0~240) 减少运行列车，节省成本

### 决策惯性

为避免振荡调车，在 Q 值基础上加**惯性惩罚**：

```
Q_inertial(m, l) = Q(m, l) - λ * (1 / ticks_since_last_shunt_on_line_l)
```

最近刚调过车的线路，再次调车的 Q 值被压低。λ 通过训练自动调优。

## 训练方式：Dueling DQN + Prioritized Experience Replay

### Dueling DQN

将 Q(s,a) 分解为 V(s) + A(s,a)：
- V(s) 评估状态本身的好坏（全局拥堵程度）
- A(s,a) 评估在该状态下各动作的相对优势

这比普通 DQN 更好地学习了状态价值，在"大部分动作都不好"的拥堵状态下更稳健。

### Prioritized Experience Replay

调度中，rare 但关键的决策（如即将拥堵前正确调车）比常规决策更有学习价值。PER 让这些高 TD-error 的经验被更频繁地回放。

### 奖励设计（每 60 tick / 每小时）

| 奖励项 | 计算 | 权重 |
|--------|------|------|
| waiting_change | (上期总等待 - 本期总等待) / overcrowd_limit | +2.0 |
| arrived_count | 本期到达目的地乘客数 | +1.0 |
| overcrowd_avoidance | 拥堵风险站数是否减少 | +3.0 |
| load_efficiency | 列车平均载客率变化 | +0.5 |
| shunting_cost | 调车动作 | -0.5 |

奖励的关键是**差分形式**（变化量而非绝对值），让模型关注"我的决策是否改善了局面"。

### Episode 设计

每个 episode = 一天的运营：

```
1. AIWorld.setup() → 生成城市
2. 用线路规划器生成初始线路 → lock_lines()
3. place_initial_trains()
4. run_one_day():
     - 1200 tick
     - 每 60 tick (1 小时) 调度器决策一次，共 20 步
     - 采集 (s, a, r, s') 四元组
5. 一天结束，读取结算报告
6. 重启下一个 episode
```

### 训练流程

```
1. 用当前线路规划器生成初始线路
2. 运行调度器，每 60 tick 采集 (s, a, r, s') 四元组
3. 存入 PER buffer
4. 每 100 tick 从 buffer 采样一批，更新 Dueling DQN
5. ε-greedy 探索：ε 从 1.0 线性衰减到 0.05
6. 目标网络每 1000 步软更新
7. 一次 episode = 1200 tick (一天)，结束后重启
```

## 备选方案对比

| 方案 | 优点 | 缺点 | 结论 |
|------|------|------|------|
| Dueling DQN + PER | 稳定、高效、适合离散动作 | 需要仔细调参 | **采用** |
| PPO (策略梯度) | 在连续空间有优势 | 调度是离散动作，PPO 无优势 | 排除 |
| 规则 + 学习混合 | 可解释 | 规则难以穷举 | 后备方案 |
| AlphaZero 式 MCTS | 最优决策 | 计算量大、工程复杂 | 备选（资源充足时） |
