# 01 - 状态表示与特征工程

## 核心问题

`getGameState()` 返回的原始状态是混合类型的字典（站点坐标、类别字符串、乘客分布、列车状态码……），无法直接输入神经网络。需要一个编码器将游戏状态转为张量。

## 状态的两层抽象

线路规划器和列车调度器关注的信息不同，但底层特征可以共享。设计一个**共享特征提取层**，两个决策器各自从共享特征中取所需的部分。

## 方案：图神经网络 (GNN) 编码站点拓扑

### 为什么选 GNN

地铁系统天然是图结构：站点是节点，线路连接是边。站点之间的空间关系和连通性是决策的关键输入。传统 MLP/CNN 无法自然处理这种拓扑。

### 图的构建

**节点特征矩阵** — 每个站点一个节点，特征向量维度 ~20：

| 特征 | 维度 | 说明 |
|------|------|------|
| category_onehot | 6 | 站点类别 one-hot |
| position_xy | 2 | 归一化坐标 (x/800, y/600) |
| passenger_count | 1 | 当前候车人数 / overcrowd_limit |
| passengers_by_dest | 6 | 按目标类别分组的候客数 / overcrowd_limit |
| connecting_line_count | 1 | 经过该站的线路数 / max_lines |
| is_terminal | 1 | 是否为某条线路的端点站 |
| congestion_risk | 1 | 候车人数是否 > 70% overcrowd_limit |

**边** — 两种边：

1. **空间邻接边**：通过 K-近邻（K=5）连接空间上相近的站点。边特征：归一化欧氏距离（1维）。
2. **线路边**：同一线路上的相邻站点。边特征：所属线路 id one-hot（7维） + 线路上列车数/总列车数（1维）。

### GNN 架构

```
Input: 节点特征 (N, 20), 边索引, 边特征
  │
  ├─ GATConv (20 → 64) + ReLU     ← 图注意力，学习站点间关联权重
  ├─ GATConv (64 → 64) + ReLU     ← 二阶邻居信息
  │
  ▼
节点嵌入 (N, 64)  ← 每个站点的上下文感知表示
```

选用 **GAT (Graph Attention Network)** 而非 GCN 的原因：GAT 能通过注意力权重学习哪些邻居站点更重要（比如换乘站比普通站更重要），这对线路规划和调度都有价值。

### 全局特征

除节点级特征外，还需要一些全局信息：

| 特征 | 维度 | 说明 |
|------|------|------|
| tick_in_day / day_length | 1 | 日内时间进度 |
| period_onehot | 7 | 当前时段 |
| next_period_onehot | 7 | 下一时段（用于预判） |
| available_trains / max_trains | 1 | 可用列车比例 |
| available_carriages / max_carriages | 1 | 可用车厢比例 |
| lines_remaining / max_lines | 1 | 剩余线路额度比例 |
| avg_waiting_time | 1 | 平均等待时间 |
| at_risk_stations_ratio | 1 | 拥堵风险站比例 |
| total_arrived_rate | 1 | 近期到达率 |

全局特征通过读出操作（readout）获得：`global = concat(mean_pool(node_embed), max_pool(node_embed), manual_global_features)`，维度约 64+64+17 = 145。

### 列车状态编码（调度器专用）

列车调度器还需要感知列车的位置和状态。每辆列车编码为：

| 特征 | 维度 | 说明 |
|------|------|------|
| line_id_onehot | 7 | 所在线路 |
| station_embedding | 64 | 当前所在站点的 GNN 嵌入（直接索引获取） |
| status_onehot | 6 | 列车状态码 |
| direction | 1 | 运行方向 |
| load_ratio | 1 | passenger_count / capacity |
| carriage_count | 1 | 车厢数 |

列车嵌入通过将列车"锚定"到其当前站点来获得空间上下文——利用 GNN 已编码的节点嵌入，无需额外图结构。

## 技术选型

- **框架**: PyTorch Geometric (PyG) — GNN 的事实标准库
- **GNN 层**: `torch_geometric.nn.GATConv`
- **图构建**: 每次决策时动态构建（因为站点可能新增）

## 输出

编码器的输出供两个下游模块使用：
- **线路规划器**：使用节点嵌入 (N, 64) + 全局特征 (145)
- **列车调度器**：使用节点嵌入 (N, 64) + 全局特征 (145) + 列车嵌入 (M, 80)
