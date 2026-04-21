# AI 设计文档

基于机器学习的地铁线路规划与列车调度系统。

## 架构总览

```
游戏环境 (MetroWorld)
    │
    ├── getGameState() ──→ 状态编码器 (StateEncoder)
    │                         │
    │                         ▼
    │                    ┌─────────────┐
    │                    │  共享特征层  │  ← 图神经网络 (GNN) 编码站点拓扑
    │                    └──────┬──────┘
    │                           │
    │              ┌────────────┼────────────┐
    │              ▼                         ▼
    │     线路规划器 (LinePlanner)    列车调度器 (TrainScheduler)
    │     低频决策 (每300 tick)       高频决策 (每10 tick)
    │              │                         │
    │              ▼                         ▼
    │     线路结构动作              资源调度动作
    │     (新建/延伸/插入线路)       (调车/分配列车/加车厢)
    │              │                         │
    │              └────────────┬────────────┘
    │                           ▼
    │                    动作执行器 → playerXxx() 调用
    │
    └── 奖励信号 ← 游戏指标 (等待时间、到达数、拥堵等)
```

## 两层决策系统的分工

| | 线路规划器 | 列车调度器 |
|---|---|---|
| 决策频率 | 低频（新线路额度时 / 每日评估时） | 高频（每10 tick） |
| 动作空间 | playerNewLine, playerLineExtension, playerLineInsert | playerTrainShunt, playerEmployTrain, playerConnectCarriage |
| 观察重点 | 站点拓扑、O-D流量模式、类别覆盖 | 站点候车分布、列车位置/载客率、时段 |
| 决策粒度 | 线路级：决定哪些站点串成线路 | 资源级：决定列车和车厢分配 |

## 详细设计见各子文档

- [01_state_encoding.md](01_state_encoding.md) — 状态表示与特征工程
- [02_line_planner.md](02_line_planner.md) — 线路规划器算法设计
- [03_train_scheduler.md](03_train_scheduler.md) — 列车调度器算法设计
- [04_training_framework.md](04_training_framework.md) — 训练框架与奖励设计
