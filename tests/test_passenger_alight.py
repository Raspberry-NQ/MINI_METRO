# test_passenger_alight.py — 测试乘客下车/换乘逻辑（修复消失bug的验证）
import sys, types, traceback
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# stub external_functions
ef = types.ModuleType('external_functions')
ef.countTrainAlightingTime = lambda t, config=None: 2
ef.countTrainBoardingTime = lambda s, config=None: 3
ef.countTrainRunningTime = lambda a, b, config=None: 5
ef.countTrainIdleTime = lambda config=None: 1
ef.countTrainShuntingime = lambda l, n, config=None: 4
sys.modules['external_functions'] = ef

ts = types.ModuleType('timer_scheduler')
class TimerSchedulerStub:
    def __init__(self):
        self.events = []
    def register(self, dt, train_obj, next_status):
        self.events.append([dt, train_obj, next_status])
        train_obj.nextStatusTime = dt
    def update(self, dt=1):
        up_trains, up_statuses = [], []
        remaining = []
        for ev in self.events:
            ev[0] -= dt
            if ev[0] <= 0:
                up_trains.append(ev[1])
                up_statuses.append(ev[2])
            else:
                remaining.append(ev)
        self.events = remaining
        return up_trains, up_statuses
ts.TimerScheduler = TimerSchedulerStub
sys.modules['timer_scheduler'] = ts

rp = types.ModuleType('route_planner')
class RPStub:
    def __init__(self, ms=None, config=None): pass
    def find_route(self, o, d, p="f"): return None
rp.RoutePlanner = RPStub
sys.modules['route_planner'] = rp

from station import station
from carriage import carriage
from train import train
from line import MetroLine
from trainInventory import TrainInventory
from passengerManager import PassengerManager
from passenger import Passenger

passed = 0
failed = 0
errors = []

def test(desc, fn):
    global passed, failed
    try:
        fn()
        passed += 1
        print(f"  PASS: {desc}")
    except Exception as e:
        failed += 1
        errors.append((desc, e, traceback.format_exc()))
        print(f"  FAIL: {desc} -> {e}")

class Metro:
    def __init__(self):
        self.metroLine = []
        self.stations = []

def make_system():
    """创建一个有两条线路、换乘站的系统"""
    sA = station(1, "circle",   0,   0)
    sB = station(2, "triangle", 100, 0)
    sC = station(3, "square",   200, 0)  # 换乘站
    sD = station(4, "diamond",  300, 0)
    sE = station(5, "star",     200, -150)
    sF = station(6, "pentagon", 200, -300)

    line1 = MetroLine(1, [sA, sB, sC, sD])
    line2 = MetroLine(2, [sE, sC, sF])

    metro = Metro()
    metro.metroLine = [line1, line2]
    metro.stations = [sA, sB, sC, sD, sE, sF]
    pm = PassengerManager(metro)
    ti = TrainInventory(pm)

    return ti, pm, line1, line2, (sA, sB, sC, sD, sE, sF)


# ================================================================
print("=== 1. 直达路线（多站经过）：乘客在目的站正确下车 ===")
# ================================================================

def t():
    """A->D 直达路线，经过 B,C，在 D 正确下车"""
    ti, pm, l1, l2, (sA, sB, sC, sD, sE, sF) = make_system()
    ti.addTrain(); ti.addCarriage()
    ti.employTrain(l1, sA)
    tr = ti.trainBusyList[0]
    c = tr.carriageList[0]

    # 构造 A->D 的路线（模拟 route_planner 输出）
    p = Passenger(1, sA, sD, "fastest")
    p.planned_route = [
        {'station': sA, 'line': None, 'direction': None, 'transfer': False},  # 0: 起点
        {'station': sB, 'line': l1, 'direction': True, 'transfer': False},    # 1
        {'station': sC, 'line': l1, 'direction': True, 'transfer': False},    # 2
        {'station': sD, 'line': l1, 'direction': True, 'transfer': False},    # 3
    ]
    p._update_current_target()  # target_line=l1, target_direction=True

    # 乘客在 sA 等待，上车
    sA.passenger_list.append(p)
    p.status = "waiting"
    pm.passenger_list.append(p)

    # 乘客上车
    pm.process_passenger_boarding(tr)
    assert p.status == "on_train"
    assert p.current_route_index == 1  # board_train 跳过 line=None 的步骤
    assert p not in sA.passenger_list
    assert p in c.passenger_list
test("直达路线上车", t)

def t():
    """A->D 乘客经过 B, C 不下车，到 D 下车"""
    ti, pm, l1, l2, (sA, sB, sC, sD, sE, sF) = make_system()
    ti.addTrain(); ti.addCarriage()
    ti.employTrain(l1, sA)
    tr = ti.trainBusyList[0]
    c = tr.carriageList[0]

    p = Passenger(1, sA, sD, "fastest")
    p.planned_route = [
        {'station': sA, 'line': None, 'direction': None, 'transfer': False},
        {'station': sB, 'line': l1, 'direction': True, 'transfer': False},
        {'station': sC, 'line': l1, 'direction': True, 'transfer': False},
        {'station': sD, 'line': l1, 'direction': True, 'transfer': False},
    ]
    p._update_current_target()

    # 上车
    sA.passenger_list.append(p); p.status = "waiting"
    pm.passenger_list.append(p)
    pm.process_passenger_boarding(tr)

    # 到 sB — 乘客不应下车
    tr.stationNow = sB
    alighted = pm.process_passenger_alighting(tr)
    assert len(alighted) == 0, f"乘客不应在 sB 下车，但 alighted={alighted}"
    assert p.status == "on_train", f"乘客应仍在车上，但 status={p.status}"
    assert p in c.passenger_list

    # 到 sC — 乘客不应下车
    tr.stationNow = sC
    alighted = pm.process_passenger_alighting(tr)
    assert len(alighted) == 0, f"乘客不应在 sC 下车，但 alighted={alighted}"
    assert p.status == "on_train"
    assert p in c.passenger_list

    # 到 sD — 乘客应下车
    tr.stationNow = sD
    alighted = pm.process_passenger_alighting(tr)
    assert len(alighted) == 1, f"乘客应在 sD 下车"
    assert p.status == "arrived"
    assert p not in c.passenger_list
test("直达路线经过中间站到目的站下车", t)

# ================================================================
print("\n=== 2. 换乘路线：乘客在换乘站正确下车并等待换乘 ===")
# ================================================================

def t():
    """A->F 路线: A(line1)->C(换乘)->F(line2), 在 C 换乘"""
    ti, pm, l1, l2, (sA, sB, sC, sD, sE, sF) = make_system()
    ti.addTrain(); ti.addCarriage()
    ti.employTrain(l1, sA)
    tr1 = ti.trainBusyList[0]
    c = tr1.carriageList[0]

    p = Passenger(1, sA, sF, "fastest")
    p.planned_route = [
        {'station': sA, 'line': None, 'direction': None, 'transfer': False},  # 0
        {'station': sB, 'line': l1, 'direction': True, 'transfer': False},    # 1
        {'station': sC, 'line': l1, 'direction': True, 'transfer': False},    # 2
        {'station': sC, 'line': l2, 'direction': True, 'transfer': True},     # 3: 换乘步
        {'station': sF, 'line': l2, 'direction': True, 'transfer': False},    # 4
    ]
    p._update_current_target()

    # 上车
    sA.passenger_list.append(p); p.status = "waiting"
    pm.passenger_list.append(p)
    pm.process_passenger_boarding(tr1)
    assert p.current_route_index == 1

    # 到 sB — 不下
    tr1.stationNow = sB
    pm.process_passenger_alighting(tr1)
    assert p.status == "on_train"

    # 到 sC — 应下车换乘
    tr1.stationNow = sC
    alighted = pm.process_passenger_alighting(tr1)
    assert len(alighted) == 1
    assert p.status == "transferring", f"应处于换乘状态，实际: {p.status}"
    assert p.transfer_waiting == True
    assert p.target_line == l2, f"换乘后目标线路应为 l2，实际: {p.target_line}"
    assert p.target_direction == True
    assert p in sC.passenger_list, "换乘乘客应在站点等待"
test("换乘路线上车 → 换乘站下车 → 目标线路更新", t)

def t():
    """换乘乘客可以坐新线路继续旅程"""
    ti, pm, l1, l2, (sA, sB, sC, sD, sE, sF) = make_system()
    ti.addTrain(); ti.addCarriage()
    # line1 车
    ti.employTrain(l1, sA)
    tr1 = ti.trainBusyList[0]
    c1 = tr1.carriageList[0]

    # line2 车
    ti.addTrain(); ti.addCarriage()
    ti.employTrain(l2, sC)
    tr2 = ti.trainBusyList[1]
    c2 = tr2.carriageList[0]

    p = Passenger(1, sA, sF, "fastest")
    p.planned_route = [
        {'station': sA, 'line': None, 'direction': None, 'transfer': False},
        {'station': sB, 'line': l1, 'direction': True, 'transfer': False},
        {'station': sC, 'line': l1, 'direction': True, 'transfer': False},
        {'station': sC, 'line': l2, 'direction': True, 'transfer': True},
        {'station': sF, 'line': l2, 'direction': True, 'transfer': False},
    ]
    p._update_current_target()

    # 上车 line1
    sA.passenger_list.append(p); p.status = "waiting"
    pm.passenger_list.append(p)
    pm.process_passenger_boarding(tr1)

    # 到 sC 下车换乘
    tr1.stationNow = sC
    pm.process_passenger_alighting(tr1)
    assert p.status == "transferring"
    assert p.target_line == l2

    # 换乘: 乘客应能上 line2 的车
    assert p.should_board_train(tr2) == True
    pm.process_passenger_boarding(tr2)
    assert p.status == "on_train"
    assert p.current_route_index == 3  # 指向换乘步 (line=l2)
test("换乘乘客坐新线路继续旅程", t)

def t():
    """换乘后到达目的站 F"""
    ti, pm, l1, l2, (sA, sB, sC, sD, sE, sF) = make_system()
    ti.addTrain(); ti.addCarriage()
    ti.employTrain(l1, sA)
    tr1 = ti.trainBusyList[0]
    c1 = tr1.carriageList[0]
    ti.addTrain(); ti.addCarriage()
    ti.employTrain(l2, sC)
    tr2 = ti.trainBusyList[1]
    c2 = tr2.carriageList[0]

    p = Passenger(1, sA, sF, "fastest")
    p.planned_route = [
        {'station': sA, 'line': None, 'direction': None, 'transfer': False},
        {'station': sB, 'line': l1, 'direction': True, 'transfer': False},
        {'station': sC, 'line': l1, 'direction': True, 'transfer': False},
        {'station': sC, 'line': l2, 'direction': True, 'transfer': True},
        {'station': sF, 'line': l2, 'direction': True, 'transfer': False},
    ]
    p._update_current_target()

    # 上车 line1 → 到 sC 换乘 → 上 line2
    sA.passenger_list.append(p); p.status = "waiting"
    pm.passenger_list.append(p)
    pm.process_passenger_boarding(tr1)
    tr1.stationNow = sC
    pm.process_passenger_alighting(tr1)
    pm.process_passenger_boarding(tr2)

    # 到 sF 应到达
    tr2.stationNow = sF
    alighted = pm.process_passenger_alighting(tr2)
    assert len(alighted) == 1
    assert p.status == "arrived"
test("换乘后到达目的站", t)

# ================================================================
print("\n=== 3. route_planner 不生成换乘步时的兜底（line变化检测）===")
# ================================================================

def t():
    """route_planner 不生成换乘步时，line 变化仍触发换乘下车"""
    ti, pm, l1, l2, (sA, sB, sC, sD, sE, sF) = make_system()
    ti.addTrain(); ti.addCarriage()
    ti.employTrain(l1, sA)
    tr = ti.trainBusyList[0]
    c = tr.carriageList[0]

    p = Passenger(1, sA, sF, "fastest")
    # 模拟不带换乘步的路线（旧 route_planner 实际输出格式）
    p.planned_route = [
        {'station': sA, 'line': None, 'direction': None, 'transfer': False},
        {'station': sB, 'line': l1, 'direction': True, 'transfer': False},
        {'station': sC, 'line': l1, 'direction': True, 'transfer': False},
        {'station': sF, 'line': l2, 'direction': True, 'transfer': False},  # 直接跳到 l2
    ]
    p._update_current_target()

    # 上车
    sA.passenger_list.append(p); p.status = "waiting"
    pm.passenger_list.append(p)
    pm.process_passenger_boarding(tr)

    # 到 sB — 不下
    tr.stationNow = sB
    pm.process_passenger_alighting(tr)
    assert p.status == "on_train"

    # 到 sC — 下一步 line 变了 (l1 → l2)，应换乘客下车
    tr.stationNow = sC
    alighted = pm.process_passenger_alighting(tr)
    assert len(alighted) == 1
    assert p.status == "transferring", f"应处于换乘状态，实际: {p.status}"
    assert p.target_line == l2, f"目标线路应为 l2，实际: {p.target_line}"
test("无换乘步时 line 变化触发换乘", t)

# ================================================================
print("\n=== 4. 乘客不会无故消失 ===")
# ================================================================

def t():
    """直达乘客在车上不会被 update 移除"""
    ti, pm, l1, l2, (sA, sB, sC, sD, sE, sF) = make_system()
    ti.addTrain(); ti.addCarriage()
    ti.employTrain(l1, sA)
    tr = ti.trainBusyList[0]

    p = Passenger(1, sA, sD, "fastest")
    p.planned_route = [
        {'station': sA, 'line': None, 'direction': None, 'transfer': False},
        {'station': sB, 'line': l1, 'direction': True, 'transfer': False},
        {'station': sC, 'line': l1, 'direction': True, 'transfer': False},
        {'station': sD, 'line': l1, 'direction': True, 'transfer': False},
    ]
    p._update_current_target()

    sA.passenger_list.append(p); p.status = "waiting"
    pm.passenger_list.append(p)
    pm.process_passenger_boarding(tr)

    # 乘客在车上，update 不应移除 on_train 乘客
    for _ in range(50):
        pm.update_all_passengers()

    assert p in pm.passenger_list, f"车上的乘客不应被移除"
    assert p.status == "on_train"
test("车上乘客不会被 update 移除", t)

def t():
    """换乘乘客等待时不会被误判为 waiting 而遗忘 target_line"""
    ti, pm, l1, l2, (sA, sB, sC, sD, sE, sF) = make_system()
    ti.addTrain(); ti.addCarriage()
    ti.employTrain(l1, sA)
    tr = ti.trainBusyList[0]

    p = Passenger(1, sA, sF, "fastest")
    p.planned_route = [
        {'station': sA, 'line': None, 'direction': None, 'transfer': False},
        {'station': sB, 'line': l1, 'direction': True, 'transfer': False},
        {'station': sC, 'line': l1, 'direction': True, 'transfer': False},
        {'station': sC, 'line': l2, 'direction': True, 'transfer': True},
        {'station': sF, 'line': l2, 'direction': True, 'transfer': False},
    ]
    p._update_current_target()

    sA.passenger_list.append(p); p.status = "waiting"
    pm.passenger_list.append(p)
    pm.process_passenger_boarding(tr)

    # 到 sC 换乘
    tr.stationNow = sC
    pm.process_passenger_alighting(tr)

    # 乘客应在 sC 等待，状态为 transferring，target_line 为 l2
    assert p.status == "transferring"
    assert p.target_line == l2
    assert p in sC.passenger_list

    # 几个 tick 后不消失
    for _ in range(10):
        pm.update_all_passengers()
    assert p in pm.passenger_list
    assert p.target_line == l2
test("换乘乘客等待时目标线路正确且不消失", t)

# ================================================================
print("\n=== 5. force_alight_all (调车强制下车) ===")
# ================================================================

def t():
    """调车强制下车时乘客目标线路正确更新"""
    ti, pm, l1, l2, (sA, sB, sC, sD, sE, sF) = make_system()
    ti.addTrain(); ti.addCarriage()
    ti.employTrain(l1, sA)
    tr = ti.trainBusyList[0]

    p = Passenger(1, sA, sD, "fastest")
    p.planned_route = [
        {'station': sA, 'line': None, 'direction': None, 'transfer': False},
        {'station': sB, 'line': l1, 'direction': True, 'transfer': False},
        {'station': sC, 'line': l1, 'direction': True, 'transfer': False},
        {'station': sD, 'line': l1, 'direction': True, 'transfer': False},
    ]
    p._update_current_target()

    sA.passenger_list.append(p); p.status = "waiting"
    pm.passenger_list.append(p)
    pm.process_passenger_boarding(tr)

    # 强制在 sB 下车
    pm.force_alight_all(tr, sB)

    assert p.status == "waiting"
    assert p.target_line == l1, f"强制下车后 target_line 应仍为 l1，实际: {p.target_line}"
    assert p in sB.passenger_list
test("强制下车后目标线路正确", t)

# ================================================================
# 汇总
# ================================================================
print("\n" + "=" * 60)
print(f"结果: {passed} 通过, {failed} 失败")
print("=" * 60)

if errors:
    print("\n失败详情:")
    for desc, e, tb in errors:
        print(f"\n  [{desc}]")
        for line in tb.strip().split('\n')[-3:]:
            print(f"    {line}")
