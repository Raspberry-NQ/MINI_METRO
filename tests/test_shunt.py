# test_shunt.py — 测试调车功能
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
    pm = PassengerManager(metro)
    ti = TrainInventory(pm)

    return ti, pm, line1, line2, (sA, sB, sC, sD, sE, sF)

# ================================================================
print("=== 1. 从车库调车到线路 ===")
# ================================================================

def t():
    """车库有空车时, employTrain 应正常工作"""
    ti, pm, l1, l2, (sA, sB, sC, sD, sE, sF) = make_system()
    ti.addTrain(); ti.addCarriage()
    assert len(ti.trainAbleList) == 1 and len(ti.carriageAbleList) == 1

    ti.employTrain(l1, sA)
    assert len(ti.trainAbleList) == 0
    assert len(ti.trainBusyList) == 1
    tr = ti.trainBusyList[0]
    assert tr.line == l1 and tr.stationNow == sA and tr.status == 2
test("employTrain 从车库调车", t)

def t():
    """车库有额外车头+车厢时, 可以再调一辆"""
    ti, pm, l1, l2, (sA, sB, sC, sD, sE, sF) = make_system()
    ti.addTrain(); ti.addTrain()
    ti.addCarriage(); ti.addCarriage()

    ti.employTrain(l1, sA)
    ti.employTrain(l2, sE)
    assert len(ti.trainBusyList) == 2
    assert ti.trainBusyList[0].line == l1
    assert ti.trainBusyList[1].line == l2
test("employTrain 调两辆到不同线路", t)

def t():
    """车库无车时 getFreeTrain 抛出 ResourceError"""
    ti, pm, l1, l2, _ = make_system()
    try:
        ti.getFreeTrain()
        assert False
    except Exception as e:
        assert "火车余额不足" in str(e)
test("车库无车时 getFreeTrain 报错", t)

def t():
    """车库无车厢时 getFreeCarriage 抛出 ResourceError"""
    ti, pm, l1, l2, _ = make_system()
    try:
        ti.getFreeCarriage()
        assert False
    except Exception as e:
        assert "车厢余额不足" in str(e)
test("车库无车厢时 getFreeCarriage 报错", t)

def t():
    """employTrain 只分配1节车厢, 但 run.py 给每列车2节"""
    ti, pm, l1, l2, (sA, sB, sC, sD, sE, sF) = make_system()
    ti.addTrain()
    ti.addCarriage(); ti.addCarriage()
    ti.employTrain(l1, sA)
    tr = ti.trainBusyList[0]
    # employTrain 只连接了1节车厢
    assert len(tr.carriageList) == 1
    # 手动加第2节
    ti.addCarriage()
    tr.connectCarriage(ti.getFreeCarriage())
    assert len(tr.carriageList) == 2
test("employTrain 车厢数量 + 手动扩展", t)

# ================================================================
print("\n=== 2. 线路之间调车 (shuntTrain) ===")
# ================================================================

def t():
    """基本调车: train 从 line1 调到 line2"""
    ti, pm, l1, l2, (sA, sB, sC, sD, sE, sF) = make_system()
    ti.addTrain(); ti.addCarriage()
    ti.employTrain(l1, sA)
    tr = ti.trainBusyList[0]

    # 先让列车跑到换乘站 sC
    # sA -> running -> sB -> alighting -> boarding -> running -> sC -> alighting
    # 手动推进状态
    tr.setRunning(sB)  # sA->sB
    tr.setAlighting(sB)  # 到sB
    tr.setBoarding(sB)  # sB boarding
    tr.setRunning(sC)  # sB->sC
    tr.setAlighting(sC)  # 到sC, status=1

    # 现在调车到 line2
    print(f"    before shunt: line={tr.line.number}, station={tr.stationNow.id}, status={tr.status}")

    # shuntTrain 需要 train 处于可以 setBoarding 的状态 (1,3,5)
    assert tr.status == 1  # alighting, 可以 setBoarding
    ti.shuntTrain(tr, l2, False, sC)

    assert tr.line == l2
    assert l1.trainNm == 0  # 从 line1 移除
    assert l2.trainNm == 1  # 加入 line2
    assert tr not in l1.trainDirection
    assert tr in l2.trainDirection
    assert l2.trainDirection[tr] == False
    print(f"    after shunt: line={tr.line.number}, direction={l2.trainDirection[tr]}")
test("shuntTrain 从 line1 调到 line2", t)

def t():
    """调车后 shunting 完成时，line2.nextStation 返回正确方向"""
    ti, pm, l1, l2, (sA, sB, sC, sD, sE, sF) = make_system()
    ti.addTrain(); ti.addCarriage()
    ti.employTrain(l1, sA)
    tr = ti.trainBusyList[0]

    # 推到 sC
    tr.setRunning(sB); tr.setAlighting(sB)
    tr.setBoarding(sB); tr.setRunning(sC); tr.setAlighting(sC)

    # 清空 timer
    ti.trainTimer.events.clear()

    # 调到 line2, 反向
    ti.shuntTrain(tr, l2, False, sC)

    # shuntTrain 走 setShunting 流程，status=5, stationNow=None
    assert tr.status == 5
    assert tr.stationNow is None

    # 模拟 shunting 完成：手动推进到 boarding 状态
    # 先设 stationNow 为目标站（模拟 updateAllTrain 中状态2的处理）
    tr.stationNow = sC
    tr.status = 2  # boarding

    # line2: [sE(0), sC(1), sF(2)]
    # direction=False 意味着 sC -> sE
    ns = l2.nextStation(tr)
    assert ns == sE
    print(f"    shunted train nextStation: sC -> {ns}")
test("调车后 line2.nextStation 正确", t)

def t():
    """调车后列车可以继续循环运行（shunting 完成后）"""
    ti, pm, l1, l2, (sA, sB, sC, sD, sE, sF) = make_system()
    ti.addTrain(); ti.addCarriage()
    ti.employTrain(l1, sA)
    tr = ti.trainBusyList[0]

    # 推到 sC
    tr.setRunning(sB); tr.setAlighting(sB)
    tr.setBoarding(sB); tr.setRunning(sC); tr.setAlighting(sC)

    # 清空 timer
    ti.trainTimer.events.clear()

    # 调到 line2, 正向
    ti.shuntTrain(tr, l2, True, sC)

    # shuntTrain 走 setShunting 流程，status=5, stationNow=None
    assert tr.status == 5  # shunting

    # 手动推进：shunting 完成后恢复到 boarding
    tr.stationNow = sC
    tr.status = 2  # boarding

    # sC boarding -> running to sF (正向)
    ns = l2.nextStation(tr)
    assert ns == sF
    tr.setRunning(sF); tr.setAlighting(sF)

    # sF alighting -> boarding -> running to sC (掉头)
    tr.setBoarding(sF)
    ns = l2.nextStation(tr)
    assert ns == sC
    tr.setRunning(sC); tr.setAlighting(sC)

    # sC -> sD...but we're on line2, direction now reversed
    # line2: [sE(0), sC(1), sF(2)], reversed from sC means sC -> sE
    tr.setBoarding(sC)
    ns = l2.nextStation(tr)
    assert ns == sE
    print(f"    shunted train making full loop on line2 OK")
test("调车后列车在 line2 上完整循环", t)

def t():
    """调车时乘客应该被强制下车"""
    ti, pm, l1, l2, (sA, sB, sC, sD, sE, sF) = make_system()
    ti.addTrain(); ti.addCarriage()
    ti.employTrain(l1, sA)
    tr = ti.trainBusyList[0]
    c = tr.carriageList[0]

    # 添加一个乘客 (sA->sD 在 line1 上)
    p = Passenger.__new__(Passenger)
    p.passenger_id = 1; p.origin_station = sA; p.destination_station = sD
    p.current_station = None; p.waiting_time = 0; p.status = "on_train"
    p.preference = "fastest"
    p.planned_route = [{'line': l1, 'direction': True, 'transfer': False, 'station': sD}]
    p.current_route_index = 0; p.target_line = l1; p.target_direction = True
    p.transfer_waiting = False
    c.passenger_list.append(p); c.currentNum = 1

    # 推到 sC
    tr.setRunning(sB); tr.setAlighting(sB)
    tr.setBoarding(sB); tr.setRunning(sC); tr.setAlighting(sC)

    # 调车 — shuntTrain 应该强制乘客下车
    ti.shuntTrain(tr, l2, True, sC)

    # 乘客应该下车了
    assert len(c.passenger_list) == 0
    assert c.currentNum == 0
    print(f"    乘客在调车时被正确强制下车, 车厢空了")
test("调车时乘客被强制下车", t)

def t():
    """removeTrainFromLine 清空 train.line"""
    ti, pm, l1, l2, (sA, sB, sC, sD, sE, sF) = make_system()
    ti.addTrain(); ti.addCarriage()
    ti.employTrain(l1, sA)
    tr = ti.trainBusyList[0]
    assert tr.line == l1

    l1.removeTrainFromLine(tr)
    assert tr.line is None  # 现在会清空
    assert l1.trainNm == 0
    assert tr not in l1.trainDirection
test("removeTrainFromLine 清空 train.line", t)

# ================================================================
print("\n=== 3. updateAllTrain 中的调车流程 (waitShunting) ===")
# ================================================================

def t():
    """waitShunting 标志: 列车需要调车时设此标志"""
    tr = train(1)
    assert tr.waitShunting == False
    assert tr.shuntingTargetLine is None

    tr.waitShunting = True
    tr.shuntingTargetLine = MetroLine(2, [])
    tr.line = MetroLine(1, [])

    # setShunting 检查 waitShunting
    assert tr.waitShunting == True
    tr.setShunting(tr.shuntingTargetLine)
    assert tr.status == 5  # shunting
    assert tr.waitShunting == False
test("waitShunting 标志和 setShunting", t)

def t():
    """updateAllTrain 中 updateStatus==2 时检查 waitShunting"""
    ti, pm, l1, l2, (sA, sB, sC, sD, sE, sF) = make_system()
    ti.addTrain(); ti.addCarriage()
    ti.employTrain(l1, sA)
    tr = ti.trainBusyList[0]

    # 推到 sC
    tr.setRunning(sB); tr.setAlighting(sB)
    tr.setBoarding(sB); tr.setRunning(sC); tr.setAlighting(sC)

    # 设置 waitShunting
    tr.waitShunting = True
    tr.shuntingTargetLine = l2

    # 注册 nextStatus=2 事件 (alighting 后)
    ti.trainTimer.register(1, tr, 2)

    # updateAllTrain 应该走 setShunting 分支
    ti.updateAllTrain()

    # setShunting 会调 removeTrainFromLine 和设 train.line = l2
    print(f"    status={tr.status}, line={tr.line.number if tr.line else None}")
    assert tr.status == 5  # shunting
test("updateAllTrain 中 waitShunting 分支", t)

def t():
    """通过 TrainInventory.shuntTrain 调车，train.line 正确设为目标线路"""
    ti, pm, l1, l2, (sA, sB, sC, sD, sE, sF) = make_system()
    ti.addTrain(); ti.addCarriage()
    ti.employTrain(l1, sA)
    tr = ti.trainBusyList[0]

    # 推到 sC，状态为 alighting
    tr.setRunning(sB); tr.setAlighting(sB)
    tr.setBoarding(sB); tr.setRunning(sC); tr.setAlighting(sC)

    # 通过 shuntTrain 调到 line2
    ti.shuntTrain(tr, l2, True, sC)
    assert tr.line == l2
test("shuntTrainToLine 设置 train.line", t)

def t():
    """完整 shuntTrain 流程: train.line 正确设为 l2"""
    ti, pm, l1, l2, (sA, sB, sC, sD, sE, sF) = make_system()
    ti.addTrain(); ti.addCarriage()
    ti.employTrain(l1, sA)
    tr = ti.trainBusyList[0]

    # 推到 sC
    tr.setRunning(sB); tr.setAlighting(sB)
    tr.setBoarding(sB); tr.setRunning(sC); tr.setAlighting(sC)

    ti.shuntTrain(tr, l2, True, sC)
    assert tr.line == l2
test("完整 shuntTrain 流程 train.line 已修复", t)

# ================================================================
print("\n=== 4. 车厢调度 (不同列车之间) ===")
# ================================================================

def t():
    """基本车厢连接和断开"""
    tr = train(1)
    c1 = carriage(1); c2 = carriage(2); c3 = carriage(3)
    tr.connectCarriage(c1); tr.connectCarriage(c2); tr.connectCarriage(c3)
    assert len(tr.carriageList) == 3

    # disconnect — 不存在此方法!
    has_disconnect = hasattr(tr, 'disconnectCarriage') or hasattr(tr, 'removeCarriage')
    print(f"    -> train.disconnectCarriage 存在: {has_disconnect}")
    if not has_disconnect:
        raise AttributeError("train 缺少 disconnectCarriage 方法")
test("train 缺少 disconnectCarriage 方法", t)

def t():
    """手动模拟车厢调度: 从 train1 移一节车厢到 train2"""
    ti, pm, l1, l2, (sA, sB, sC, sD, sE, sF) = make_system()
    ti.addTrain(); ti.addTrain()
    ti.addCarriage(); ti.addCarriage(); ti.addCarriage()

    ti.employTrain(l1, sA)
    ti.employTrain(l2, sE)

    tr1 = ti.trainBusyList[0]
    tr2 = ti.trainBusyList[1]

    # tr1 有1节车厢, 给它再加1节
    ti.addCarriage()
    tr1.connectCarriage(ti.getFreeCarriage())
    assert len(tr1.carriageList) == 2

    # 手动从 tr1 移除1节并给 tr2
    c = tr1.carriageList.pop()
    tr2.connectCarriage(c)
    assert len(tr1.carriageList) == 1
    assert len(tr2.carriageList) == 2
    print(f"    tr1 carriages: {len(tr1.carriageList)}, tr2: {len(tr2.carriageList)}")
test("手动车厢调度", t)

def t():
    """车厢上有乘客时转移车厢, 乘客跟着车厢走"""
    ti, pm, l1, l2, (sA, sB, sC, sD, sE, sF) = make_system()
    ti.addTrain(); ti.addTrain()
    ti.addCarriage(); ti.addCarriage(); ti.addCarriage()

    ti.employTrain(l1, sA)
    ti.employTrain(l2, sE)

    tr1 = ti.trainBusyList[0]
    tr2 = ti.trainBusyList[1]

    # 给 tr1 加一节车厢
    ti.addCarriage()
    tr1.connectCarriage(ti.getFreeCarriage())

    # 在 tr1 的第二节车厢放乘客
    from passenger import Passenger as P
    c = tr1.carriageList[1]
    p = P.__new__(P)
    p.status = "on_train"; p.current_station = None
    p.planned_route = [{'line': l1, 'direction': True, 'transfer': False, 'station': sD}]
    p.current_route_index = 0
    c.passenger_list.append(p); c.currentNum = 1

    # 转移车厢
    c_moved = tr1.carriageList.pop()
    tr2.connectCarriage(c_moved)

    # 乘客现在在 tr2 的车厢里, 但乘客的 target_line 还是 l1
    assert p in tr2.carriageList[-1].passenger_list
    print(f"    乘客 target_line={p.target_line if hasattr(p, 'target_line') else 'N/A'}, 但在 train2(line={tr2.line.number}) 上")
    print(f"    -> 乘客路线与列车线路不匹配 (设计问题)")
test("车厢转移时乘客路线不匹配", t)

# ================================================================
print("\n=== 5. setShunting 状态转接 ===")
# ================================================================

def t():
    """setShunting 后 timer 注册 nextStatus=2, 下一步是 boarding"""
    tr = train(1)
    tr.waitShunting = True
    tr.line = MetroLine(1, [station(1,"c",0,0)])

    l2 = MetroLine(2, [station(2,"c",100,0)])
    dt = tr.setShunting(l2)
    assert tr.status == 5  # shunting
    assert tr.nextStatus == 2  # boarding
    assert tr.waitShunting == False
    assert tr.stationNow is None  # shunting 时不在任何站
test("setShunting 状态检查", t)

def t():
    """shunting 完成后 (updateStatus=2), 走 boarding 分支，在新线路上"""
    ti, pm, l1, l2, (sA, sB, sC, sD, sE, sF) = make_system()
    ti.addTrain(); ti.addCarriage()
    ti.employTrain(l1, sA)
    tr = ti.trainBusyList[0]

    # 清空 timer（手动推进不用 timer）
    ti.trainTimer.events.clear()

    # 手动推到 sC 并设置调车
    tr.setRunning(sB); tr.setAlighting(sB)
    tr.setBoarding(sB); tr.setRunning(sC); tr.setAlighting(sC)

    # 设置调车标志 + 目标站 + 方向
    tr.waitShunting = True
    tr.shuntingTargetLine = l2
    tr.shuntingTargetStation = sC
    tr.shuntingTargetDirection = True

    # 注册 nextStatus=2 事件（模拟 alighting 完成后）
    ti.trainTimer.register(1, tr, 2)
    ti.updateAllTrain()

    assert tr.status == 5  # shunting
    assert len(ti.trainTimer.events) > 0
    shunting_event = ti.trainTimer.events[0]
    print(f"    shunting event: dt={shunting_event[0]}, nextStatus={shunting_event[2]}")

    # 推进到 shunting 结束
    for _ in range(shunting_event[0]):
        ti.updateAllTrain()

    # 应该进入 boarding 状态, 在 line2 上, 在 sC 站
    print(f"    after shunting: status={tr.status}, line={tr.line.number if tr.line else None}, station={tr.stationNow.id if tr.stationNow else None}")
    assert tr.status == 2  # boarding
    assert tr.line == l2
    assert tr.stationNow == sC
test("调车完成后列车在新线路上 boarding", t)

# ================================================================
print("\n=== 6. setShunting 中 self.line 访问问题 ===")
# ================================================================

def t():
    """setShunting line=None 时不会崩溃（countTrainShuntingime 处理了 None），
       但从车库调车应该用 employTrain"""
    tr = train(1)
    tr.waitShunting = True
    l2 = MetroLine(2, [station(1,"c",0,0)])
    dt = tr.setShunting(l2)
    assert tr.status == 5
    # setShunting 不改变 self.line，line 通过 addNewTrainToLine 设置
    assert tr.line is None
    print(f"    -> setShunting line=None 可用但不设 train.line, 应使用 employTrain")
test("setShunting line=None 可用但不完善", t)

def t():
    """从车库调车到线路: 列车初始 line=None, setShunting 无法使用
       应该用 employTrain 而非 shunt"""
    ti, pm, l1, l2, _ = make_system()
    ti.addTrain(); ti.addCarriage()

    # 从车库调车用 employTrain, 不走 shunting
    ti.employTrain(l1, station(1,"c",0,0))
    tr = ti.trainBusyList[0]
    assert tr.line == l1
    print(f"    -> 从车库调车应用 employTrain, 不走 shunting")
test("从车库调车应该用 employTrain", t)

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
