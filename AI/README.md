# AI 设计文档

基于机器学习的地铁线路规划与列车调度系统。

## 核心约束

- **站点一次性生成**：世界开始时生成全部站点，后续不再新增
- **线路一次性规划**：规划阶段一次建好所有线路，`lock_lines()` 后不可修改
- **只运行一天**：一个 episode = 一天 (1200 tick)，结算后结束

## 架构总览

```
游戏环境 (AIWorld)                ← ai_world.py: AI 专用训练世界
    │
    │  1. setup()        生成城市，一次性给齐所有站点和资源
    │  2. 规划阶段        AI 调用 build_lines() + place_initial_trains()
    │  3. lock_lines()   锁定线路，此后只能调度不能改线
    │  4. run_one_day()   模拟一天(1200 tick)，每小时调度一次，返回结算报告
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
    │     一次性决策 (规划阶段)        高频决策 (每60 tick/每小时)
    │              │                         │
    │              ▼                         ▼
    │     线路结构动作              资源调度动作
    │     (新建线路 only)           (调车/分配列车/加车厢)
    │              │                         │
    │              └────────────┬────────────┘
    │                           ▼
    │                    动作执行器 → playerXxx() 调用
    │
    └── 奖励信号 ← 每日结算报告 (客流、成本、利润、覆盖率等)
```

## AI 世界的核心规则

| 规则 | 说明 |
|------|------|
| 站点一次性生成 | 游戏开始时生成全部站点，后续不再新增 |
| 线路锁定 | 规划阶段结束后锁定线路，不可新建/延伸/插入 |
| 1 tick ≈ 1 分钟 | day_length=1200 (20 小时)，两站间运行约 5-8 tick |
| 初始资源全给 | 全部列车/车厢在 setup 时就给齐，无渐进增长 |
| 一天结算 | 运行一天 (1200 tick) 后结算，计算开支、客流、利润等指标 |
| 同线列车上限 | 每条线路最多 2 辆列车同时运营 |

## AI 输入输出接口

### 输入: `getGameState()` 返回的状态快照

```python
{
    "tick": int,                    # 当前总 tick
    "game_over": bool,
    "day_count": int,               # 第几天 (AI 专用)
    "tick_in_day": int,             # 当天第几个 tick (AI 专用)
    "lines_locked": bool,           # 线路是否已锁定 (AI 专用)

    "time_of_day": {
        "tick_in_day": int,
        "day_length": 1200,
        "period": str,              # "night"/"morning_rush"/"morning"/"midday"/"evening_rush"/"evening"/"late_night"
        "active_od_patterns": [{"origin": str, "destination": str, "weight": int}],
    },

    "stations": [{
        "id": int, "type": str, "category": str,
        "x": int, "y": int,
        "passenger_count": int,
        "connecting_lines": [int],
        "passengers_by_dest_category": {str: int},
    }],

    "lines": [{
        "id": int,
        "station_ids": [int],
        "station_categories": [str],
        "train_count": int,
        "train_ids": [int],         # (AI 专用) 线路上的列车 ID
        "max_trains": 2,            # (AI 专用) 该线列车上限
    }],

    "trains": [{
        "id": int, "line_id": int|None, "station_id": int|None,
        "status": int,              # 1=落客 2=上客 3=空闲 4=运行 5=调车 6=等待
        "direction": bool|None,
        "carriage_count": int,
        "passenger_count": int,
        "capacity": int,
    }],

    "available": {"trains": int, "carriages": int, "lines_remaining": int},
    "metrics": { ... },             # 全局指标
}
```

### 输出: 规划阶段

```python
# 1. 建线路
line_definitions = [[1,3,5,7], [2,3,4,6], ...]  # 每个子列表=一条线路的站点 ID 序列
world.build_lines(line_definitions)

# 2. 放列车
train_placements = [
    {"line_id": 1, "station_id": 1, "direction": True},
    {"line_id": 1, "station_id": 7, "direction": False},
    ...
]
world.place_initial_trains(train_placements)

# 3. 锁线
world.lock_lines()
```

### 输出: 调度阶段 (每 60 tick/每小时)

```python
# 调车 (仍在调度阶段可用)
world.playerTrainShunt(train_obj, goalLine, direction, station_obj)

# 分配列车
world.playerEmployTrain(line, station_obj, direction)

# 加车厢
world.playerConnectCarriage(train_obj)
```

### 每日结算报告

```python
{
    "day": int,                     # 第几天
    "survived": bool,               # 是否存活
    "ticks_today": int,             # 当天运行 tick 数

    "passengers_arrived_today": int,
    "passengers_on_train": int,
    "passengers_waiting": int,
    "avg_waiting_time": float,
    "max_waiting_time": int,

    "active_trains": int,
    "total_trains_in_service": int,
    "total_carriages_in_service": int,
    "train_km": int,                # 列车总里程 (tick-km)
    "lines_count": int,

    "category_coverage": {str: {"connected": int, "total": int, "lines": [int]}},
    "overall_coverage_ratio": float,

    "at_risk_stations": int,
    "max_station_passengers": int,

    "revenue": int,                 # 票价收入
    "cost_fixed": int,              # 固定成本
    "cost_variable": int,           # 变动成本
    "total_cost": int,
    "profit": int,                  # revenue - total_cost
}
```

## 两层决策系统的分工

| | 线路规划器 | 列车调度器 |
|---|---|---|
| 决策频率 | 一次性（规划阶段） | 高频（每60 tick / 每小时） |
| 动作空间 | build_lines (playerNewLine) | playerTrainShunt, playerEmployTrain, playerConnectCarriage |
| 观察重点 | 站点拓扑、O-D流量模式、类别覆盖 | 站点候车分布、列车位置/载客率、时段 |
| 决策粒度 | 线路级：决定哪些站点串成线路 | 资源级：决定列车和车厢分配 |

## 时间尺度 (1 tick ≈ 1 分钟)

| 参数 | 值 | 说明 |
|------|-----|------|
| day_length | 1200 | 20 小时 × 60 = 1200 tick |
| running_base_time | 3 | 两站基础运行 3 分钟 |
| train_running_speed | 0.04 | 80px 站距 ≈ 2 分钟距离贡献 |
| boarding 时间 | 2-7 tick | 基础 2 + 每乘客 1 |
| alighting 时间 | 2-7 tick | 基础 2 + 每乘客 1 |
| 调车时间 | 15-30 tick | 同线路 15 / 跨线路 30 |

## 详细设计见各子文档

- [01_state_encoding.md](01_state_encoding.md) — 状态表示与特征工程
- [02_line_planner.md](02_line_planner.md) — 线路规划器算法设计
- [03_train_scheduler.md](03_train_scheduler.md) — 列车调度器算法设计
- [04_training_framework.md](04_training_framework.md) — 训练框架与奖励设计

## 代码文件

- `ai_world.py` — AIWorld 类，AI 训练专用世界
- `run.py` — MetroWorld 类，原始游戏世界（AIWorld 的父类）
- `game_config.py` — GameConfig.for_ai_training() 工厂方法
