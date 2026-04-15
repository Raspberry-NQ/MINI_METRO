# MINI METRO

一个简单的地铁模拟游戏

## 项目结构

- 根目录: 包含所有游戏核心模块的源代码文件
- `tests/` 目录: 包含所有测试文件

## 文件说明

### 核心游戏模块

- `main.py` - 游戏入口点，初始化一个小的世界进行演示
- `run.py` - 完整的游戏运行器，使用城市生成器创建初始站点，包含玩家操作接口和观察接口，支持 `--visual` 可视化模式
- `visualizer.py` - pygame 可视化模块，提供图形化游戏界面和鼠标交互
- `world.py` - 游戏世界类，管理站点、线路和整体游戏状态
- `game_config.py` - 游戏配置类，集中管理所有可调参数（站点类别、日调度乘客生成、资源增长、时间计算、可视化等）
- `station.py` - 站点类，表示地铁站的信息和状态，支持功能类别（居民区/商业区/办公区/医院/景区/学校）
- `city_generator.py` - 城市生成器，按类别聚集生成初始城市站点布局
- `train.py` - 列车类，管理列车状态、车厢和运行逻辑
- `carriage.py` - 车厢类，表示载客的车厢
- `line.py` - 线路类，管理地铁线路和站点关系，支持动态添加/插入/移除站点
- `passenger.py` - 乘客类，管理乘客状态、路径规划和行为
- `passengerManager.py` - 乘客管理器，负责生成乘客和处理上下车逻辑
- `trainInventory.py` - 列车库存管理器，管理所有列车和车厢资源
- `route_planner.py` - 路径规划器，为乘客计算最优路径
- `timer_scheduler.py` - 定时调度器，管理列车状态转换的定时事件
- `external_functions.py` - 外部函数模块，包含各种时间计算函数，支持 GameConfig 参数

### 测试文件

- `tests/test_all.py` - 综合测试所有模块功能
- `tests/test_shunt.py` - 专门测试调车功能

## 用户操作指南

### 运行游戏

1. 运行简单演示世界：
   ```bash
   python main.py
   ```

2. 运行完整游戏（文本模式）：
   ```bash
   python run.py
   ```

3. 运行可视化游戏（推荐）：
   ```bash
   python run.py --visual
   ```
   依赖：`pip install pygame`

### 运行测试

```bash
# 运行所有测试
python tests/test_all.py
python tests/test_shunt.py
```

## 游戏更新机制

按游戏刻来更新.

每一刻需要更新的有:

- 地图:根据日调度按时段和 O-D 流量模式生成乘客（淡化动态站点生成）
- 已有站点:按类别和时段安排乘客出行
- 车辆状态:行驶或上客落客
- 资源增长:按配置定期发放列车/车厢/线路额度

## 站点类别系统

站点分为 6 个功能类别，每个类别对应独特形状：

| 类别 | 英文 | 形状 | 典型客流 |
|------|------|------|---------|
| 居民区 | residential | triangle | 早高峰出发，晚高峰到达 |
| 商业区 | commercial | diamond | 午间/晚间高峰 |
| 办公区 | office | square | 早高峰到达，晚高峰出发 |
| 医院 | hospital | pentagon | 全天少量客流 |
| 景区 | scenic | star | 晚间出发/到达 |
| 学校 | school | circle | 早高峰到达，晚高峰出发 |

城市生成器在游戏开始时按类别聚集生成 18-20 个站点，AI/玩家需要立即规划线路。

## 日调度乘客生成

一天 = 300 ticks，分为 7 个时段：

| 时段 | 大致对应 | 主要 O-D 方向 |
|------|---------|--------------|
| 夜间 | 0:00-5:00 | 极少量，居民→医院 |
| 早高峰 | 5:00-8:24 | 居民区→办公区/学校 |
| 上午 | 8:24-12:00 | 办公→商业，医院→居民 |
| 午间 | 12:00-14:24 | 办公→商业(午餐) |
| 晚高峰 | 14:24-18:00 | 办公→居民区，学校→居民 |
| 晚间 | 18:00-21:07 | 商业→居民，景区→居民 |
| 深夜 | 21:07-24:00 | 商业→居民 |

## 玩家/AI 操作接口

`MetroWorld` 提供以下操作方法供玩家或 AI 调用：

| 方法 | 说明 |
|---|---|
| `playerTrainShunt(train, goalLine, direction, station)` | 调车：将列车从当前线路调到目标线路 |
| `playerLineExtension(line, station, append=True)` | 延伸线路：在线路末端或起点添加站点 |
| `playerLineInsert(line, index, station)` | 在线路中间插入站点 |
| `playerNewLine(station_list)` | 创建新线路 |
| `playerEmployTrain(line, station, direction)` | 从车库分配列车到线路 |
| `playerConnectCarriage(train)` | 给列车联挂一节车厢 |

## 游戏观察接口

`MetroWorld.getGameState()` 返回标准化状态快照，包含：

- `tick` — 当前 tick
- `time_of_day` — 当前日时段信息（时段名称、活跃 O-D 模式）
- `stations` — 各站点候车人数、类别、坐标、连接线路、候车乘客目的地类别分布
- `lines` — 各线路站点列表、站点类别、列车数量
- `trains` — 各列车位置、状态、方向、载客/容量
- `available` — 可用资源（列车/车厢/线路额度）
- `metrics` — 全局指标（最大候车人数、平均等待时间、拥堵风险站点数、未连接站点数等）

## 可视化操作

运行 `python run.py --visual` 进入图形化界面，支持以下操作：

| 按键/鼠标 | 功能 |
|---|---|
| `Space` | 暂停/继续 |
| `+` / `-` | 加速/减速模拟 |
| 滚轮 | 缩放视图 |
| 左键拖拽 | 平移视图 |
| `L` | 创建新线路（点击站点选择，Enter 确认） |
| `E` | 延伸线路（点击站点添加到线路末端，Enter 确认） |
| `T` | 添加列车到最需车的线路 |
| `C` | 给列车联挂车厢 |
| 右键点击站点 | 自动将站点连接到最近线路 |
| `R` | 重置视图位置和缩放 |
| `Esc` | 退出（编辑模式时取消编辑） |

### 视觉元素说明

- **站点形状**: circle / triangle / square / diamond / star / pentagon 对应不同类型
- **站点周围小形状**: 等候乘客的目标站点类型
- **站点红色脉冲**: 候车人数接近上限（70%以上）
- **彩色线条**: 线路路径，不同颜色代表不同线路
- **列车矩形**: 显示载客数/容量，白色三角指示方向
- **左上角 HUD**: tick 数、速度、站点/线路/列车数、拥堵警告、指标
- **右上角 HUD**: 可用资源（列车/车厢/线路额度）

## 游戏配置 (GameConfig)

所有数值参数均可通过 `GameConfig` 调整，主要配置项：

- **站点类别**: 6种类别定义、类别→形状映射、各类别颜色和中文标签
- **城市布局**: 站点数、城市范围、各类别站点数量范围、聚集半径
- **日调度**: 一天tick数、时段定义、时段基础生成率、O-D流量模式
- **动态站点**: 生成间隔（已淡化）、概率、类型列表
- **资源增长**: 调度表 `[(间隔tick, 资源类型, 数量), ...]`，支持 train/carriage/line/tunnel
- **列车/车厢**: 容量、每列车默认车厢数
- **时间计算**: 行驶速度倍率、上客/落客/空闲/调车时间
- **乘客**: 默认耐心值、换乘惩罚时间
- **可视化**: 窗口尺寸、帧率、模拟速度、站点/列车/乘客绘制大小、线路颜色、类别颜色

---

# 思考:

## 20250913

可以安排一个全局更新机,内置一个定时器,每个车头等在其中注册一条定时计划,然后每个tick更新机检查定时器,将到时间的注册者更新状态
或者,每个状态的定时由车头自己计算,然后每次更新所有车头的状态

感觉第一种会好一点.
可以用**最小堆**,剩余时间最少的在上面.由于等待时间只会按顺序变小(除了调车),
因此可以每次从顶端检查是否到时间.若没有则进入下一个循环,如果有就删除堆顶,安排新的堆顶后再立即检查堆顶是否到时间(
因为有可能和旧堆顶时间相等)

所有可以先不考虑调车,即列车和线路不能更改已安排的部分,只能延长.

## 20250914

列车的状态转移的具体操作可以写在train类,但是判断是否要转移,以及转移前的操作等等,可以写在trainInventory或者gameWorld里.
也就是, *举例*: 在train里做一个setBoarding函数,只把状态改到boarding.然后在(比如)trainInventory里写一个setTrainStatus(
train,status), 里面判断冷却时间等等

另外timeschedule的更新可以放到world的update函数里,每个tick运行一次

应该是,每次在inventory调用改变列车状态的函数时,注册一个新的倒计时

还有,列车在终点站自动掉头,应当是先落客完,然后掉头,再上客.
因此一列车的完整周期是:
*boarding->running->alighting->(boarding->running->alighting)... ->(destination)alighting-> change direction ->boarding->...*
如果有调车,则是*(boarding->)running->**get shunting command**->alighting->shunting->boarding->...like upon*

~~所以换向判断应该写在boarding里面,因为调车和终点站都要操作行驶方向,这俩也都是从boarding开始~~

**不太行,由于换向啥的是在line里面息息相关的,放在line类里面更合适**

可以在line里面用一个字典记录每个列车的方向

## 20250915

调动列车时也可以包括同线路换向这一操作

ALIGHTING   -<  (running)
BOARDING    -<  (alighting,shunting,idle)
RUNNING     -<  (BOARDING)
SHUNTING    -<  (ALIGHTING)
也就是,只有running->alighting/shunting->borading/idle->boarding
这三种情况才需要修改stationNow

## 20250918
在train添加了一个waitshunting的flag，以及targetline，来记录是否处于侯调车状态

## 20260414

完善游戏基础能力，为 AI 设计做准备：
- 新增 `game_config.py`：集中管理所有可调参数（资源增长、站点生成、时间计算等）
- `line.py`：新增 `addStation()`/`insertStation()`/`removeStation()`，自动维护 `station.connections`
- `run.py`：实现玩家操作接口（调车/延伸线路/插入站点/新建线路/分配列车/联挂车厢）；`getGameState()` 观察接口；动态站点生成；资源增长机制；`ai_callback` 参数
- `timer_scheduler.py`：用序列号打破 heap 平局，修复 train 对象比较问题
- `route_planner.py`：修复 Dijkstra 中 station 对象无法比较的问题
- `train.py`：支持 config 参数，修复 `__str__` line=None 崩溃
- `carriage.py`：支持可配置容量
- `passenger.py`：支持可配置耐心值
- `external_functions.py`：所有函数支持可选 config 参数

## 20260415

新增面向人类玩家的可视化界面：
- 新增 `visualizer.py`：基于 pygame 的实时可视化渲染器
  - 站点按类型绘制不同形状（circle/triangle/square/diamond/star/pentagon）
  - 线路以不同颜色绘制，列车实时显示位置、方向、载客/容量
  - 乘客候车以目标站点小形状环绕站点显示
  - 拥堵站点红色脉冲警告
  - HUD 显示游戏指标、可用资源
  - 游戏结束统计画面
- 交互操作：鼠标缩放/平移、键盘快捷键（Space暂停、+/-调速）、创建线路(L)、延伸线路(E)、添加列车(T)、添加车厢(C)、右键快速连接站点
- `run.py` 新增 `--visual` 命令行参数启动可视化模式
- `game_config.py` 新增可视化相关配置项（窗口尺寸、帧率、颜色、绘制参数）

站点类别系统 & 日调度乘客生成：
- `station.py`：新增 category 字段，6 种功能类别（居民区/商业区/办公区/医院/景区/学校），类别→形状映射
- `city_generator.py`：城市生成器，按类别聚集生成 18-20 个初始站点
- `game_config.py`：日调度系统（day_length=300 ticks/天，7 时段，O-D 流量模式），类别颜色/标签，城市布局参数
- `run.py`：setup() 改用城市生成器；_spawn_passengers_scheduled() 替代随机生成；getGameState() 增加时段信息/类别覆盖/乘客分布；AI 辅助方法（getUnconnectedStations/getCategoryCoverage/findNearestStation 等）
- `visualizer.py`：站点类别底色、类别图例、时段显示、未连接站点警告
- 动态站点生成已淡化（间隔 200，概率 0.3）

---

# AI 架构设计

## 整体思路

AI 的核心挑战是：在游戏开始时就需要根据站点类别布局规划线路，后续根据日调度周期动态调车。AI 需要两层决策——**线路规划层**（低频，大改）和**调度层**（高频，微调）。

## 三层架构

### 第 1 层：初始线路规划器 (Line Planner)

**触发时机**: 游戏开始时一次性执行（或获得新线路额度时补充）

**核心逻辑**:
1. 读取城市布局：各类别站点的位置和数量
2. 根据 O-D 流量模式识别关键走廊：
   - 居民区↔办公区（早/晚高峰主走廊）
   - 居民区↔学校（早高峰）
   - 办公区↔商业区（午间/晚间）
   - 各类别↔医院（全天零散）
3. 为每条走廊设计线路，保证：
   - 尽量覆盖同类别所有站点
   - 在换乘站交汇（优先选择类别交界处的站点）
   - 线路不要过长（避免单线过长导致列车周转慢）
4. 分配初始列车：每条线路 1-2 列，优先给主走廊

**输出**: `playerNewLine()`, `playerEmployTrain()`, `playerConnectCarriage()`

### 第 2 层：反应式调度器 (Reactive Dispatcher)

**触发时机**: 每 N tick 执行一次（如每 10 tick）

**核心逻辑**:
1. 读取 `getGameState()`，重点关注：
   - 各站点乘客数和 `passengers_by_dest_category`
   - 当前时段和即将到来的时段（预判）
   - 各列车位置、载客率、方向
2. 拥堵响应：
   - 某站接近拥堵 → 考虑调车到该线路
   - 空闲列车 → 分配到乘客最多的线路
3. 时段预判调度：
   - 早高峰快到 → 提前将列车调到居民区→办公区的线路
   - 晚高峰快到 → 提前调车到办公区→居民区的线路
4. 车厢优化：给载客率高的列车加车厢

**输出**: `playerTrainShunt()`, `playerEmployTrain()`, `playerConnectCarriage()`

**决策约束**:
- 不做线路结构修改（不延伸/插入/删站），保持线路稳定
- 只做列车和车厢资源的再分配
- 决策要有惯性，避免来回调车

### 第 3 层：评估器 (Evaluator)

**触发时机**: 每次调度决策前评估，定期汇总

**核心逻辑**:
1. 评估当前线路网络的效率：
   - 各线路覆盖的类别组合是否完整
   - 各类别站点的连接率 (`getCategoryCoverage()`)
   - 乘客平均等车时间
   - 列车利用率（载客率 / 运行比例）
2. 识别瓶颈：
   - 哪些 O-D 对缺少直达或换乘路径
   - 哪些站点是换乘瓶颈
   - 哪些线路列车不够
3. 当评估器发现线路结构有根本性问题时，触发第 1 层重新规划

## 信息流

```
getGameState() ──→ 评估器 ──→ 线路规划器 (低频)
                      │
                      ├──→ 反应式调度器 (高频) ──→ 玩家操作接口
                      │
                      └──→ 时段预判 ──→ 调度器
```

## 调度策略细节

### 时段感知

AI 需要维护一个"预判窗口"——不只看当前时段，还要看未来 1-2 个时段：
- 当前 `morning_rush`，下一个是 `morning` → 不需要急着调车方向
- 当前 `morning`，下一个是 `midday` → 开始准备办公→商业方向的运力
- 当前 `evening_rush`，下一个是 `evening` → 逐步减少办公线运力

### 资源约束

- 列车总数有限，调车有冷却时间
- 调车决策要考虑：调车耗时 vs 原地等乘客
- 新增车厢优先级：高客流线路 > 低客流线路

### 与日调度的配合

日调度以 300 tick 为一个周期。AI 应该：
- 在一天的前几个 tick 就设好基本线路（第 1 层输出）
- 每天在关键时段前 10-20 tick 做预判调度
- 积累经验：如果某天早高峰运力不足，次日提前调车

---



---

