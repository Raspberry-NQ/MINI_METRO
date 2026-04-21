# 03 - 列车调度器算法设计

## 问题定义

每 10 tick 观察一次环境状态，决定：
1. 是否将列车从一条线调到另一条线（playerTrainShunt）
2. 是否从车库分配列车到某条线（playerEmployTrain）
3. 是否给某列车加车厢（playerConnectCarriage）

约束：列车总数有限、调车有冷却时间、决策要有惯性避免振荡。

## 算法选择：注意力驱动的多智能体决策 + DQN

### 为什么是多智能体视角

每条线路可以看作一个"智能体"，它需要列车和车厢资源。"调车"本质上是把资源从低需求线路转移到高需求线路。各线路的需求是动态且相互竞争的。

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
│                          [train_count, avg_load_ratio, │
│                           total_waiting_on_line])     │
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
│    或 "不分配"                                  │
│                                                │
│  头2: 调车 (playerTrainShunt)                  │
│    Q(train_m, target_line_l) = MLP(train_m,    │
│                                    context_l)  │
│                                  → 标量         │
│    动作: argmax_{m,l} Q(m,l) 的有效调车方案      │
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

总动作数: 1 + L + M + M*L (约 1+7+15+105 = 128)
```

实际可用动作用**动作掩码**（action mask）过滤：
- available_trains == 0 → 掩码所有分配动作
- available_carriages == 0 → 掩码所有加车厢动作
- 列车正在 shunting/running → 掩码该车调车动作（调车需要列车空闲）

### 时段感知机制

调度器必须在时段切换前预判：

```
时段嵌入 = Embedding(period_id, dim=16) + Embedding(next_period_id, dim=16)
```

这 32 维特征拼入全局特征。模型通过训练学习：
- 晚高峰前 20 tick 将列车调到办公→居民线路
- 午间前 10 tick 增加办公→商业方向运力

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

调度中， rare 但关键的决策（如即将拥堵前正确调车）比常规决策更有学习价值。PER 让这些高 TD-error 的经验被更频繁地回放。

### 奖励设计（每 10 tick）

| 奖励项 | 计算 | 权重 |
|--------|------|------|
| waiting_change | (上期总等待 - 本期总等待) / overcrowd_limit | +2.0 |
| arrived_count | 本期到达目的地乘客数 | +1.0 |
| overcrowd_avoidance | 拥堵风险站数是否减少 | +3.0 |
| load_efficiency | 列车平均载客率变化 | +0.5 |
| shunting_cost | 调车动作 | -0.5 |

奖励的关键是**差分形式**（变化量而非绝对值），让模型关注"我的决策是否改善了局面"。

### 训练流程

```
1. 用当前线路规划器生成初始线路
2. 运行调度器，每 10 tick 采集 (s, a, r, s') 四元组
3. 存入 PER buffer
4. 每 100 tick 从 buffer 采样一批，更新 Dueling DQN
5. ε-greedy 探索：ε 从 1.0 线性衰减到 0.05
6. 目标网络每 1000 步软更新
7. 一次 episode = 500~1500 tick，结束后重启
```

## 备选方案对比

| 方案 | 优点 | 缺点 | 结论 |
|------|------|------|------|
| Dueling DQN + PER | 稳定、高效、适合离散动作 | 需要仔细调参 | **采用** |
| PPO (策略梯度) | 在连续空间有优势 | 调度是离散动作，PPO 无优势 | 排除 |
| 规则 + 学习混合 | 可解释 | 规则难以穷举 | 后备方案 |
| AlphaZero 式 MCTS | 最优决策 | 计算量大、工程复杂 | 备选（资源充足时） |
