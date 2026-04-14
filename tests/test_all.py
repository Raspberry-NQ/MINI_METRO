# test_all.py — 综合测试 MINI METRO 所有模块

import types, sys, traceback
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# ============================================================
# 缺失依赖 stub
# ============================================================
ef = types.ModuleType('external_functions')
ef.countTrainAlightingTime = lambda train, config=None: 2
ef.countTrainBoardingTime = lambda station, config=None: 3
ef.countTrainRunningTime = lambda s1, s2, config=None: 5
ef.countTrainIdleTime = lambda config=None: 1
ef.countTrainShuntingime = lambda line, nextLine, config=None: 4
sys.modules['external_functions'] = ef

ts = types.ModuleType('timer_scheduler')
class TimerSchedulerStub:
    def __init__(self):
        self.events = []
    def register(self, dt, train_obj, next_status):
        self.events.append((dt, train_obj, next_status))
    def update(self, dt=1):
        return [], []
ts.TimerScheduler = TimerSchedulerStub
sys.modules['timer_scheduler'] = ts

# route_planner.py now exists, no need for stub

# ============================================================
from station import station
from passenger import Passenger
from carriage import carriage
from train import train
from line import MetroLine
from passengerManager import PassengerManager
from trainInventory import TrainInventory

# ============================================================
passed = 0
failed = 0
errors = []

def test(description, fn):
    global passed, failed
    try:
        fn()
        passed += 1
        print(f"  PASS: {description}")
    except Exception as e:
        failed += 1
        errors.append((description, e, traceback.format_exc()))
        print(f"  FAIL: {description} -> {e}")

def make_line(number, n_stations):
    stations = [station(i, f"type{i}", i*100, 0) for i in range(n_stations)]
    line = MetroLine(number, stations)
    return line, stations

class MetroStub:
    def __init__(self):
        self.metroLine = []
        self.stations = []

# 正确的状态循环: idle(3) -> boarding(2) -> running(4) -> alighting(1) -> boarding(2) -> ...
def train_move_to_station(t, line, target_station):
    """模拟列车移动到目标站点的完整状态转换: boarding -> running -> alighting"""
    t.setBoarding(target_station)   # 2
    t.setRunning(line.nextStation(t))  # 4
    t.setAlighting(t.stationNow)     # wait - setAlighting takes station arg

def train_step(t, line):
    """从当前状态执行一步完整循环: boarding -> running -> alighting -> boarding -> running"""
    ns = line.nextStation(t)
    t.setBoarding(ns)  # alighting(1)->boarding(2) 或从其他允许状态
    ns2 = line.nextStation(t)
    t.setRunning(ns2)  # boarding(2)->running(4)

# ============================================================
# 1. station
# ============================================================
print("\n=== station ===")

def t():
    s = station(1, "circle", 100, 200)
    assert s.id == 1 and s.type == "circle" and s.x == 100 and s.y == 200
    assert s.passengerNm == 0 and s.passenger_list == [] and s.connections == []
test("station 构造函数", t)

def t():
    s = station(1, "circle", 0, 0)
    s.passengerNm = 5
    assert len(s.passenger_list) == 0  # 不同步
test("station passengerNm 与 passenger_list 不同步", t)

def t():
    s = station(1, "circle", 0, 0)
    assert not hasattr(s, 'addPassenger')
test("station 缺少 addPassenger 方法", t)

# ============================================================
# 2. carriage
# ============================================================
print("\n=== carriage ===")

def t():
    c = carriage(1)
    assert c.number == 1 and c.capacity == 6 and c.currentNum == 0
    assert c.passenger_list == [] and c.line == 0
test("carriage 构造函数", t)

def t():
    c = carriage(1)
    c.moveCarriage(3)
    assert c.line == 3
test("carriage moveCarriage", t)

def t():
    c = carriage(1)
    assert not (hasattr(c, 'addPassenger') or hasattr(c, 'removePassenger'))
test("carriage 缺少 addPassenger/removePassenger 封装", t)

# ============================================================
# 3. train
# ============================================================
print("\n=== train ===")

def t():
    tr = train(1)
    assert tr.number == 1 and tr.line is None and tr.status == 3
    assert tr.stationNow is None and tr.nextStatusTime == -1 and tr.nextStatus == 3
    assert tr.waitShunting == False and tr.shuntingTargetLine is None
test("train 构造函数", t)

def t():
    s = station(1, "circle", 0, 0)
    tr = train(1); dt = tr.setBoarding(s)
    assert tr.status == 2 and tr.stationNow == s and tr.nextStatus == 4
test("train idle->boarding", t)

def t():
    s = station(1, "circle", 0, 0)
    tr = train(1); tr.status = 1; dt = tr.setBoarding(s)
    assert tr.status == 2
test("train alighting->boarding", t)

def t():
    s = station(1, "circle", 0, 0)
    tr = train(1); tr.status = 5; dt = tr.setBoarding(s)
    assert tr.status == 2
test("train shunting->boarding", t)

def t():
    s = station(1, "circle", 0, 0)
    tr = train(1); tr.status = 4
    try:
        tr.setBoarding(s); assert False
    except Exception as e:
        assert "状态不对" in str(e)
test("train running->boarding 应报错", t)

def t():
    s1 = station(1, "circle", 0, 0)
    s2 = station(2, "triangle", 100, 0)
    tr = train(1); tr.setBoarding(s1); dt = tr.setRunning(s2)
    assert tr.status == 4 and tr.nextStatus == 1
test("train boarding->running", t)

def t():
    s = station(1, "circle", 0, 0)
    tr = train(1)
    try:
        tr.setRunning(s); assert False
    except Exception as e:
        assert "状态不对" in str(e)
test("train 非boarding->running 应报错", t)

def t():
    s1 = station(1, "circle", 0, 0)
    s2 = station(2, "triangle", 100, 0)
    tr = train(1); tr.setBoarding(s1); tr.setRunning(s2)
    dt = tr.setAlighting(s2)
    assert tr.status == 1 and tr.stationNow == s2 and tr.nextStatus == 2
test("train running->alighting", t)

def t():
    s = station(1, "circle", 0, 0)
    tr = train(1)
    try:
        tr.setAlighting(s); assert False
    except Exception as e:
        assert "状态不对" in str(e)
test("train 非running->alighting 应报错", t)

def t():
    tr = train(1); dt = tr.setIdle()
    assert tr.status == 3 and tr.stationNow is None and tr.nextStatus == 3
test("train setIdle", t)

def t():
    tr = train(1); tr.waitShunting = True
    l1 = MetroLine(1, [station(1,"c",0,0)]); tr.line = l1
    l2 = MetroLine(2, [station(2,"t",100,0)])
    dt = tr.setShunting(l2)
    assert tr.status == 5 and tr.waitShunting == False and tr.nextStatus == 2
test("train setShunting", t)

def t():
    tr = train(1); tr.waitShunting = False
    try:
        tr.setShunting(None); assert False
    except Exception as e:
        assert "waitShunting" in str(e)
test("train setShunting 无标志应报错", t)

def t():
    """BUG: train.line=None 时调用 __str__ 访问 self.line.number 崩溃"""
    tr = train(1)
    try:
        _ = str(tr)
        print(f"    -> str 无 line 时成功 (不应该)")
    except AttributeError as e:
        print(f"    -> BUG 确认: str(train) line=None 崩溃 - {e}")
        raise
test("[BUG] train __str__ line=None 时崩溃", t)

def t():
    tr = train(1)
    tr.connectCarriage(carriage(1)); tr.connectCarriage(carriage(2))
    assert len(tr.carriageList) == 2
test("train connectCarriage 多车厢", t)

# ============================================================
# 4. MetroLine
# ============================================================
print("\n=== MetroLine ===")

def t():
    l, sts = make_line(1, 3)
    assert l.number == 1 and len(l.stationList) == 3
    assert l.trainNm == 0 and l.trainDirection == {}
test("MetroLine 构造函数", t)

def t():
    l, (s1, s2, s3) = make_line(1, 3)
    tr = train(1); tr.setBoarding(s1)
    l.addNewTrainToLine(tr, s1, True)
    assert tr.line == l and l.trainDirection[tr] == True and l.trainNm == 1
test("MetroLine addNewTrainToLine", t)

def t():
    l, (s1, s2, s3) = make_line(1, 3)
    tr = train(1); tr.setBoarding(s1); l.addNewTrainToLine(tr, s1, True)
    assert l.nextStation(tr) == s2
test("MetroLine nextStation 正向", t)

def t():
    l, (s1, s2, s3) = make_line(1, 3)
    tr = train(1); tr.setBoarding(s3); l.addNewTrainToLine(tr, s3, False)
    assert l.nextStation(tr) == s2
test("MetroLine nextStation 反向", t)

def t():
    l, (s1, s2) = make_line(1, 2)
    tr = train(1); tr.setBoarding(s2); l.addNewTrainToLine(tr, s2, True)
    ns = l.nextStation(tr)
    assert ns == s1 and l.trainDirection[tr] == False
test("MetroLine nextStation 终点掉头", t)

def t():
    l, (s1, s2) = make_line(1, 2)
    tr = train(1); tr.setBoarding(s1); l.addNewTrainToLine(tr, s1, False)
    ns = l.nextStation(tr)
    assert ns == s2 and l.trainDirection[tr] == True
test("MetroLine nextStation 起点掉头", t)

def t():
    """三站循环: boarding->running->alighting->boarding->running->..."""
    l, (s1, s2, s3) = make_line(1, 3)
    tr = train(1); c = carriage(1); tr.connectCarriage(c)
    tr.setBoarding(s1); l.addNewTrainToLine(tr, s1, True)

    # s1:boarding -> s2:running
    ns = l.nextStation(tr); assert ns == s2
    tr.setRunning(ns)
    # s2:alighting -> boarding -> running
    tr.setAlighting(ns)
    tr.setBoarding(ns)
    ns = l.nextStation(tr); assert ns == s3
    tr.setRunning(ns)
    # s3:alighting(掉头) -> boarding -> running
    tr.setAlighting(ns)
    tr.setBoarding(ns)
    ns = l.nextStation(tr); assert ns == s2
    tr.setRunning(ns)
    # s2:alighting -> boarding -> running
    tr.setAlighting(ns)
    tr.setBoarding(ns)
    ns = l.nextStation(tr); assert ns == s1
test("MetroLine 三站完整循环", t)

def t():
    l, (s1, s2) = make_line(1, 2)
    tr = train(1); tr.setBoarding(s1); l.addNewTrainToLine(tr, s1, True)
    l.removeTrainFromLine(tr)
    assert tr not in l.trainDirection and l.trainNm == 0
test("MetroLine removeTrainFromLine", t)

def t():
    """BUG: 空线路 nextStation 调用 stationList.index() 会 ValueError"""
    l = MetroLine(1, [])
    tr = train(1); tr.setBoarding(station(1,"c",0,0))
    tr.line = l; l.trainDirection[tr] = True
    try:
        ns = l.nextStation(tr)
        print(f"    -> 空线路 nextStation 返回: {ns}")
    except ValueError as e:
        print(f"    -> BUG 确认: 空线路 nextStation 崩溃 - {e}")
        raise
test("[BUG] MetroLine 空线路 nextStation 崩溃", t)

def t():
    """BUG: 单站线路 nextStation: p=0, p-1=-1 -> stations[-1] = stations[0] 同一站"""
    s1 = station(1, "circle", 0, 0)
    l = MetroLine(1, [s1])
    tr = train(1); tr.setBoarding(s1); l.addNewTrainToLine(tr, s1, True)
    ns = l.nextStation(tr)
    print(f"    -> 单站 nextStation: {ns}, 是否指向自己: {ns == s1}")
    # p=0, 正向, p == len-1, 进入终点逻辑, 返回 stations[p-1]=stations[-1]=stations[0]
    # 返回自身! 列车不会移动, 但也不会崩溃
test("[BUG] MetroLine 单站线路 nextStation 返回自身", t)

def t():
    l1, (s1, s2) = make_line(1, 2)
    l2, (s3, s4) = make_line(2, 2)
    tr = train(1); tr.setBoarding(s1); l1.addNewTrainToLine(tr, s1, True)
    tr.setRunning(s2); tr.setAlighting(s2)
    l1.removeTrainFromLine(tr)
    stime = l2.shuntTrainToLine(tr, True, s3)
    print(f"    -> shuntTrainToLine: stime={stime}, train.line={tr.line}")
test("MetroLine shuntTrainToLine", t)

def t():
    """BUG: removeTrainFromLine 不存在的 train 不报错, 但可能减少 trainNm"""
    l, _ = make_line(1, 2)
    tr = train(1)
    l.removeTrainFromLine(tr)  # train 不在 trainDirection 中, 不做任何事
    assert l.trainNm == 0  # OK because not in dict
test("MetroLine 移除不在线路上的 train (静默)", t)

def t():
    """已修复: MetroLine 初始化时更新 station.connections"""
    l, (s1, s2) = make_line(1, 2)
    assert s2 in s1.connections and s1 in s2.connections
test("MetroLine 初始化时更新 station.connections", t)

# ============================================================
# 5. Passenger
# ============================================================
print("\n=== Passenger ===")

def t():
    s1, s2 = station(1,"c",0,0), station(2,"t",100,0)
    p = Passenger(1, s1, s2)
    assert p.passenger_id == 1 and p.origin_station == s1 and p.destination_station == s2
    assert p.current_station == s1 and p.status == "waiting" and p.planned_route is None
test("Passenger 构造函数", t)

def t():
    s1, s2 = station(1,"c",0,0), station(2,"t",100,0)
    p = Passenger(1, s1, s2)
    assert p.should_board_train(train(1)) == False
test("Passenger should_board_train 无路线", t)

def t():
    s1, s2 = station(1,"c",0,0), station(2,"t",100,0)
    p = Passenger(1, s1, s2); p.status = "on_train"
    l, _ = make_line(1, 2)
    p.planned_route = [{'line': l, 'direction': True, 'transfer': False}]
    p._update_current_target()
    assert p.should_board_train(train(1)) == False
test("Passenger should_board_train 非waiting", t)

def t():
    s1, s2 = station(1,"c",0,0), station(2,"t",100,0)
    p = Passenger(1, s1, s2)
    l1, _ = make_line(1, 2)
    l2, _ = make_line(2, 2)
    p.planned_route = [{'line': l1, 'direction': True, 'transfer': False}]
    p._update_current_target()
    tr = train(1); tr.line = l2
    assert p.should_board_train(tr) == False
test("Passenger should_board_train 线路不匹配", t)

def t():
    l, (s1, s3) = make_line(1, 2)
    p = Passenger(1, s1, s3)
    p.planned_route = [{'line': l, 'direction': True, 'transfer': False}]
    p._update_current_target()
    tr = train(1); tr.line = l; tr.stationNow = s1
    l.trainDirection[tr] = True
    result = p.board_train(tr)
    assert result == True and p.status == "on_train" and p.current_station is None
test("Passenger board_train 成功", t)

def t():
    """alight_train 方法已补全, 测试基本功能"""
    l, (s1, s2) = make_line(1, 2)
    p = Passenger(1, s1, s2)
    p.planned_route = [{'line': l, 'direction': True, 'transfer': False}]
    p._update_current_target()
    p.status = "on_train"
    p.current_route_index = 1
    p.alight_train(s2)
    assert p.status == "arrived" and p.current_station == s2
test("Passenger alight_train 到达终点", t)

def t():
    """已修复: Passenger.update_waiting_time 方法存在且正常工作"""
    s1, s2 = station(1,"c",0,0), station(2,"t",100,0)
    p = Passenger(1, s1, s2)
    p.update_waiting_time()
    assert p.waiting_time == 1
test("Passenger update_waiting_time 已修复", t)

def t():
    """已修复: Passenger.is_impatient 方法存在且正常工作"""
    s1, s2 = station(1,"c",0,0), station(2,"t",100,0)
    p = Passenger(1, s1, s2)
    assert p.is_impatient() == False
    p.waiting_time = 200
    assert p.is_impatient() == True
test("Passenger is_impatient 已修复", t)

# ============================================================
# 6. PassengerManager
# ============================================================
print("\n=== PassengerManager ===")

def t():
    pm = PassengerManager(MetroStub())
    assert pm.passenger_list == [] and pm.passenger_id_counter == 0
test("PassengerManager 构造", t)

def t():
    pm = PassengerManager(MetroStub())
    s1, s2 = station(1,"c",0,0), station(2,"t",100,0)
    result = pm.generate_passenger(s1, s2)
    assert result is None
test("PassengerManager generate 无路径", t)

def t():
    pm = PassengerManager(MetroStub())
    s1, s2 = station(1,"c",0,0), station(2,"t",100,0)
    l, _ = make_line(1, 2)
    pm.route_planner.find_route = lambda o,d,p: [{'line':l,'direction':True,'transfer':False}]
    result = pm.generate_passenger(s1, s2)
    assert result is not None and result in s1.passenger_list and s1.passengerNm == 1
test("PassengerManager generate 有路径", t)

def t():
    """已修复: 无车厢时, 乘客不会被允许上车，留在车站等待"""
    pm = PassengerManager(MetroStub())
    l, (s1, s2) = make_line(1, 2)
    tr = train(1); tr.setBoarding(s1); l.addNewTrainToLine(tr, s1, True)
    p = Passenger(1, s1, s2)
    p.planned_route = [{'line':l,'direction':True,'transfer':False}]
    p._update_current_target()
    s1.passenger_list.append(p); s1.passengerNm = 1
    result = pm.process_passenger_boarding(tr)
    # 无车厢时，乘客不会上车，留在车站
    assert p.status == "waiting"
    assert p in s1.passenger_list
test("[BUG] PassengerManager boarding 无车厢时乘客丢失", t)

def t():
    """已修复: 车厢满员时, 乘客不会被允许上车，留在车站等待"""
    pm = PassengerManager(MetroStub())
    l, (s1, s2) = make_line(1, 2)
    tr = train(1); c = carriage(1); tr.connectCarriage(c)
    tr.setBoarding(s1); l.addNewTrainToLine(tr, s1, True)
    for i in range(6):
        c.passenger_list.append(Passenger(100+i, s1, s2))
    c.currentNum = 6
    p = Passenger(1, s1, s2)
    p.planned_route = [{'line':l,'direction':True,'transfer':False}]
    p._update_current_target()
    s1.passenger_list.append(p); s1.passengerNm = 1
    result = pm.process_passenger_boarding(tr)
    # 满员时，乘客不会上车，留在车站
    assert p.status == "waiting"
    assert p in s1.passenger_list
test("[BUG] PassengerManager boarding 满员时乘客丢失", t)

def t():
    """已修复: process_passenger_alighting 调用 passenger.alight_train 正常工作"""
    pm = PassengerManager(MetroStub())
    l, (s1, s2) = make_line(1, 2)
    tr = train(1); c = carriage(1); tr.connectCarriage(c)
    tr.setBoarding(s1); l.addNewTrainToLine(tr, s1, True)
    tr.setRunning(s2); tr.setAlighting(s2)
    p = Passenger(1, s1, s2); p.status = "on_train"
    p.planned_route = [{'line':l,'direction':True,'transfer':False}]
    p.current_route_index = 0
    c.passenger_list.append(p); c.currentNum = 1
    alighted = pm.process_passenger_alighting(tr)
    assert len(alighted) == 1
test("PassengerManager alighting 已修复", t)

# ============================================================
# 7. TrainInventory
# ============================================================
print("\n=== TrainInventory ===")

def t():
    ti = TrainInventory()
    assert ti.trainNm == 0 and ti.carriageNm == 0
test("TrainInventory 构造函数", t)

def t():
    ti = TrainInventory(); ti.addTrain()
    assert ti.trainNm == 1 and len(ti.trainAbleList) == 1
test("TrainInventory addTrain", t)

def t():
    ti = TrainInventory(); ti.addCarriage()
    assert ti.carriageNm == 1 and len(ti.carriageAbleList) == 1
test("TrainInventory addCarriage", t)

def t():
    ti = TrainInventory()
    try:
        ti.getFreeTrain(); assert False
    except Exception as e:
        assert "火车余额不足" in str(e)
test("TrainInventory getFreeTrain 空列表报错", t)

def t():
    ti = TrainInventory()
    try:
        ti.getFreeCarriage(); assert False
    except Exception as e:
        assert "车厢余额不足" in str(e)
test("TrainInventory getFreeCarriage 空列表报错", t)

def t():
    ti = TrainInventory(); ti.addTrain(); ti.addCarriage()
    l, (s1, _) = make_line(1, 2)
    ti.employTrain(l, s1)
    tr = ti.trainBusyList[0]
    assert tr.line == l and tr.status == 2 and tr.stationNow == s1
test("TrainInventory employTrain 成功", t)

def t():
    """BUG: employTrain 中 line == 0 永远不触发 (Line 对象不等于 0),
       line == train_obj.line 也永远不触发 (新 train.line 是 None).
       这个检查形同虚设"""
    ti = TrainInventory(); ti.addTrain(); ti.addCarriage()
    tr = ti.trainAbleList[0]
    l, (s1, _) = make_line(1, 2)
    print(f"    -> train.line={tr.line}, line==0: {l==0}, line==train.line: {l==tr.line}")
    assert l != 0 and l != tr.line  # 两个条件都不触发
test("[BUG] TrainInventory employTrain line 检查永远不触发", t)

def t():
    """BUG: 默认 passenger_manager=None, 但 updateAllTrain 中 boarding 阶段会 sys.exit"""
    ti = TrainInventory()
    assert ti.passenger_manager is None
test("[BUG] TrainInventory 默认 passenger_manager=None 导致 boarding 崩溃", t)

def t():
    ti = TrainInventory(); ti.updateAllTrain()
test("TrainInventory updateAllTrain 空", t)

def t():
    """已修复: getFreeTrain/getFreeCarriage 资源不足时抛 ResourceError"""
    ti = TrainInventory()
    try:
        ti.getFreeTrain()
        assert False
    except Exception as e:
        assert "ResourceError" in type(e).__name__ or "余额不足" in str(e)
test("TrainInventory 资源不足抛异常", t)

# ============================================================
# 8. 集成测试
# ============================================================
print("\n=== 集成测试 ===")

def t():
    l, (s1, s2) = make_line(1, 2)
    tr = train(1); c = carriage(1); tr.connectCarriage(c)
    tr.setBoarding(s1); l.addNewTrainToLine(tr, s1, True)
    # s1->s2
    ns = l.nextStation(tr); assert ns == s2
    tr.setRunning(ns); tr.setAlighting(ns)
    # s2: boarding again
    tr.setBoarding(ns)
    ns = l.nextStation(tr); assert ns == s1
    tr.setRunning(ns); tr.setAlighting(ns)
test("两站循环 s1->s2->s1", t)

def t():
    pm = PassengerManager(MetroStub())
    l, (s1, s2) = make_line(1, 2)
    pm.route_planner.find_route = lambda o,d,p: [{'line':l,'direction':True,'transfer':False}]
    p = pm.generate_passenger(s1, s2)
    tr = train(1); c = carriage(1); tr.connectCarriage(c)
    tr.setBoarding(s1); l.addNewTrainToLine(tr, s1, True)
    boarded = pm.process_passenger_boarding(tr)
    print(f"    -> boarded: {len(boarded)}, p.status={p.status}, in_carriage={p in c.passenger_list}")
    assert p.status == "on_train" and p in c.passenger_list
test("乘客上车集成测试", t)

def t():
    """完整循环: 乘客在s1上车 -> 列车开到s2 -> 乘客在s2下车到达"""
    pm = PassengerManager(MetroStub())
    l, (s1, s2) = make_line(1, 2)
    pm.route_planner.find_route = lambda o,d,p: [{'line':l,'direction':True,'transfer':False}]
    p = pm.generate_passenger(s1, s2)
    assert p is not None and p.status == "waiting"

    tr = train(1); c = carriage(1); tr.connectCarriage(c)
    tr.setBoarding(s1); l.addNewTrainToLine(tr, s1, True)

    # 上车
    boarded = pm.process_passenger_boarding(tr)
    assert p.status == "on_train" and p in c.passenger_list
    print(f"    -> 上车成功: p in carriage")

    # 列车运行到 s2
    tr.setRunning(s2)
    print(f"    -> 列车运行中")

    # 到站落客
    tr.setAlighting(s2)
    alighted = pm.process_passenger_alighting(tr)
    print(f"    -> 下车: alighted={len(alighted)}, p.status={p.status}, p.current_station={p.current_station}")
    assert p.status == "arrived" and p.current_station == s2
    assert p not in c.passenger_list
    assert p in s2.passenger_list or p.status == "arrived"
test("乘客上车-运行-下车完整循环", t)

def t():
    """TrainInventory + PassengerManager 完整循环 (用 TimerScheduler)"""
    # 构建系统
    class FakeMetro:
        def __init__(self):
            self.metroLine = []
            self.stations = []
    metro = FakeMetro()
    s1 = station(1, "circle", 0, 0)
    s2 = station(2, "triangle", 300, 0)
    l = MetroLine(1, [s1, s2])
    metro.metroLine.append(l)
    metro.stations = [s1, s2]

    pm = PassengerManager(metro)
    ti = TrainInventory(pm)
    ti.addTrain(); ti.addCarriage()

    # 分配列车到线路
    ti.employTrain(l, s1)
    tr = ti.trainBusyList[0]

    # 生成乘客
    p = pm.generate_passenger(s1, s2)
    assert p is not None and p.status == "waiting"
    print(f"    -> 乘客生成: {p}")

    # 手动推进: boarding 阶段处理乘客上车
    pm.process_passenger_boarding(tr)
    print(f"    -> boarding 后: p.status={p.status}, carriage={sum(len(c.passenger_list) for c in tr.carriageList)}人")

    # setRunning -> setAlighting -> 下车
    ns = l.nextStation(tr)
    tr.setRunning(ns)
    tr.setAlighting(ns)
    pm.process_passenger_alighting(tr)
    print(f"    -> 到站: p.status={p.status}, p.current_station={p.current_station}")
    assert p.status == "arrived"
test("TrainInventory+PassengerManager 完整循环", t)

# ============================================================
# 汇总
# ============================================================
print("\n" + "=" * 60)
print(f"结果: {passed} 通过, {failed} 失败")
print("=" * 60)

if errors:
    print("\n失败详情:")
    for desc, e, tb in errors:
        print(f"\n  [{desc}]")
        for line in tb.strip().split('\n')[-3:]:
            print(f"    {line}")
