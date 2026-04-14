# MINI METRO

一个简单的地铁模拟游戏

## 项目结构

- 根目录: 包含所有游戏核心模块的源代码文件
- `tests/` 目录: 包含所有测试文件

## 文件说明

### 核心游戏模块

- `main.py` - 游戏入口点，初始化一个小的世界进行演示
- `run.py` - 完整的游戏运行器，设置两条线路和多列车的复杂世界，包含玩家操作接口和观察接口
- `world.py` - 游戏世界类，管理站点、线路和整体游戏状态
- `game_config.py` - 游戏配置类，集中管理所有可调参数（资源增长、站点生成、时间计算等）
- `station.py` - 站点类，表示地铁站的信息和状态
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

2. 运行完整游戏：
   ```bash
   python run.py
   ```

### 运行测试

```bash
# 运行所有测试
python tests/test_all.py
python tests/test_shunt.py
```

## 游戏更新机制

按游戏刻来更新.

每一刻需要更新的有:

- 地图:随机产生新的站点
- 已有站点:随机更换站点类型,随机增加乘客
- 车辆状态:行驶或上客落客
- 资源增长:按配置定期发放列车/车厢/线路额度

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

- `stations` — 各站点候车人数、类型、连接线路
- `lines` — 各线路站点列表、列车数量
- `trains` — 各列车位置、状态、方向、载客/容量
- `available` — 可用资源（列车/车厢/线路额度）
- `metrics` — 全局指标（最大候车人数、平均等待时间、拥堵风险站点数等）

## 游戏配置 (GameConfig)

所有数值参数均可通过 `GameConfig` 调整，主要配置项：

- **乘客生成**: 基础概率、增长速率、上限、额外生成起始tick
- **动态站点**: 生成间隔、概率、类型列表、坐标范围、最小距离、最大数量
- **资源增长**: 调度表 `[(间隔tick, 资源类型, 数量), ...]`，支持 train/carriage/line/tunnel
- **列车/车厢**: 容量、每列车默认车厢数
- **时间计算**: 行驶速度倍率、上客/落客/空闲/调车时间
- **乘客**: 默认耐心值、换乘惩罚时间

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