# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.


#
###------------------------------------------>><<-----------------------------------------------------
##引入库
import sys
import time

import heapq
from queue import Queue

###------------------------------------------>><<-----------------------------------------------------
# 原子基础类
trainStatusList = {1: "passengerAlighting",  # 乘客落车
                   2: "passengerBoarding",  # 乘客上车
                   3: "idle",  # 空闲中
                   4: "running",  # 前往下一站中
                   5: "shunting"}  # 调车冷却中


#
# 注意列车状态是先下后上
class train:
    def __init__(self, number):
        self.number = number
        self.line = 0  # 0代表未放置
        self.carriageList = []

        self.status = 3

        self.stationNow = None

        self.nextStatusTime = -1  # 空闲状态如果不做操作,应该是无限保持.因此为-1
        self.nextStatus = 3

    def __str__(self):
        return f" TRAIN[No.{self.number}] /{trainStatusList[self.status]}/LINE[{self.line}]/{len(self.carriageList)} carriage/ "

    def connectCarriage(self, carriage):
        self.carriageList.append(carriage)

    '''
    以下五个函数写明了操作火车进入新的状态,并且返回在新的状态持续的时间,注意不是从上个状态转移到新状态的时间
    也就是说,在调用这五个函数时,上个状态应当以及结束了
    '''

    def setAlighting(self, station):
        if self.status != 4:
            sys.exit("落客前状态不对,在SETALIGHTING")
        self.status = 1
        self.stationNow = station
        self.nextStatusTime = countTrainAlightingTime(self)
        self.nextStatus = 2  # 下一个状态一般是2
        return self.nextStatusTime

    def setBoarding(self, station):
        if self.status not in (1, 5):
            sys.exit("上客前状态不对,在setboarding")
        self.status = 2
        self.stationNow = station
        self.nextStatusTime = countTrainBoardingTime(station)
        self.nextStatus = 4  # 下一个状态一般是2
        return self.nextStatusTime

    def setIdle(self):
        print("TRAIN ", self.number, "移入车库待命")
        self.status = 3
        self.stationNow = None
        self.nextStatusTime = countTrainIdleTime()
        self.nextStatus = 3  # 下一个状态一般是3
        return self.nextStatusTime

    def setRunning(self, nextStation):
        if self.status != 2:
            sys.exit("出站前状态不对,在setrunning")
        self.status = 4
        # 不修改当前station,直到落客才修改
        self.nextStatusTime = countTrainRunningTime(self.stationNow, nextStation)
        self.nextStatus = 1  # 下一个状态一般是3
        return self.nextStatusTime

    def setShunting(self, nextLine):
        # 需要先进站落客再调车
        self.status = 5
        self.stationNow = None
        self.nextStatusTime = countTrainShuntingime(self.line, nextLine)
        self.nextStatus = 2  # 下一个状态一般是也就是到站直接上客,无需等待落客
        return self.nextStatusTime

    def printTrain(self):
        print("车头编号:", self.number)
        print("车辆状态:", trainStatusList[self.status])
        if self.status in (4, 1, 2):
            print("所在线路:", self.line)
            print("挂载车厢:", self.carriageList)
        if self.status == 5:
            print("调车冷却中!")


class carriage:
    def __init__(self, number):
        self.number = number
        self.line = 0
        self.capacity = 6  # 车厢容量,默认为6
        self.currNum = 0  # 当前人数

    def moveCarriage(self, lineNo):  ###<<----------------
        # 注意此操作后,要到下一个站点才能正式操作
        # 先落客,然后判断去掉后是否为空车头,然后再修改
        self.line = lineNo


class station:
    def __init__(self, type, x, y):
        self.type = type  # 参考stationTypeList,目前只有1,2,3
        self.x = x
        self.y = y
        self.passengerNm = 0
        self.connections = []  # 存储连接的Station对象

    def __str__(self):
        return f"TYPE:{self.type} / x:{self.x} y:{self.y} / "

    def printStation(self):
        print("Type:", end="")
        print(self.type,end=" / ")
        print("x:", self.x, " y:", self.y,end=" /")


###------------------------------------------>><<-----------------------------------------------------
# 集合类
class TrainInventory:  # 记录所有火车和车厢信息.以及注意:train代表动力不载人车头,carriage代表无动力载人车厢
    def __init__(self):
        self.trainNm = 0
        self.carriageNm = 0

        self.trainBusyList = []
        self.carriageBusyList = []
        self.trainAbleList = []
        self.carriageAbleList = []

        self.trainTimer = TimerScheduler()

    def addTrain(self):
        self.trainNm += 1
        newTrain = train(self.trainNm)
        self.trainAbleList.append(newTrain)

    def addCarriage(self):
        self.carriageNm += 1
        newCarr = carriage(self.carriageNm)
        self.carriageAbleList.append(newCarr)

    def getFreeTrain(self):
        if len(self.trainAbleList) == 0:
            sys.exit("火车余额不足!(在addTrainToLine)")
        newtrain = self.trainAbleList[0]
        self.trainAbleList.remove(newtrain)
        self.trainBusyList.append(newtrain)
        return newtrain

    def getFreeCarriage(self):
        if len(self.carriageAbleList) == 0:
            sys.exit("车厢余额不足!(在addTrainToLine)")
        newcarriage = self.carriageAbleList[0]
        self.carriageAbleList.remove(newcarriage)
        self.carriageBusyList.append(newcarriage)
        return newcarriage

    def employTrain(self, line, station):  # 移动列车到线路,进入状态1
        if line == 0 or line == train.line:
            print("FALSE LINE")
            sys.exit("FALSE LINE,in \"employTrain()\"")

        train.line = line
        train.status = 1  # 进入上客状态
        train.stationNow = station
        train.nextStatusTime = countTrainBoardingTime(station)


class MetroLine:
    def __init__(self, number, stList):
        self.number = number
        self.stationList = stList

        self.trainNm = 0
        self.trainDirection = {}  # True为正向,False为反向

    def distance(self):  # 单位为刻
        dis = 0
        for i in range(0, len(self.stationList) - 1):
            dis = dis + countTrainRunningTime(self.stationList[i], self.stationList[i + 1])
        return dis

    def addTrainToLine(self, trainInventory, direction):  # 返回是否成功,和加入火车的编号

        nCarriage = trainInventory.getFreeCarriage()
        nTrain = trainInventory.getFreeTrain()
        nTrain.connectCarriage(nCarriage)
        self.trainDirection[nTrain] = direction
        self.trainNm += 1

    def removeTrainFromLine(self, train):  # 只有在调车时才会用到
        if self.trainDirection[train] != None:
            self.trainNm -= 1
            self.trainDirection.pop(train)

    def printLine(self):
        print("正向起点", end="")
        for i, station in enumerate(self.stationList):
            if i > 0:
                print(" -> ", end="")
            print(f" ( [{i}]{station} ) ", end="")
        print(" -> 正向终点")


###------------------------------------------>><<-----------------------------------------------------

class TimerScheduler:
    def __init__(self):
        self.events = []  # 最小堆: (trigger_time, train_id, action)
        self.current_time = 0  # 游戏时间(秒)

    def register(self, delay, train, nextStatus):
        """注册定时事件
        delay: 延迟时间(秒)
        train_id: 列车标识
        action: 状态变更函数
        """
        trigger_time = self.current_time + delay
        heapq.heappush(self.events, (trigger_time, train, nextStatus))

    def update(self, dt):
        """更新所有定时事件
        dt: 距离上次更新的时间增量(秒)
        """
        updateTrain = []
        updateStatus = []
        self.current_time += dt
        while self.events and self.events[0][0] <= self.current_time:
            _, trainout, nextStatus = heapq.heappop(self.events)
            updateTrain.append(trainout)
            updateStatus.append(nextStatus)
        print("需要更新的火车有", len(updateTrain), "个")
        return updateTrain, updateStatus


# 世界状态管理
class GameWorld:
    def __init__(self):
        self.stations = []  # 所有Station

        self.metroLine = []  # 所有线路

        self.trainInventory = TrainInventory()

    def worldInit(self, trainNm=1, carriageNm=1, stationNm=2):
        print("世界初始化,车头", trainNm, "车厢", carriageNm, "站点", stationNm)
        # 初始化资源
        for i in range(0, trainNm):
            self.trainInventory.addTrain()
        for i in range(0, carriageNm):
            self.trainInventory.addCarriage()
        nsta = station(1, 0, 0)
        nstb = station(2, 0, 10)
        self.stations.append(nsta)
        self.stations.append(nstb)

        linea=MetroLine(1, self.stations)
        self.metroLine.append(linea)

        for i in range(0,len(self.metroLine)):
            print("线路",i)
            self.metroLine[i].printLine()


    def printInformation(self):
        count = 0
        for i in self.stations:
            print("station", count,end=">>")
            i.printStation()
            print("")
            count = count + 1


###------------------------------------------>><<-----------------------------------------------------
# 外部独立函数


def countTrainRunningTime(sta, stb):
    x1 = sta.x
    x2 = stb.x
    y1 = sta.y
    y2 = stb.y
    d = round(((x1 - x2) ** 2 + (y1 - y2) ** 2) ** (1 / 2))
    return d


def countTrainBoardingTime(station):
    ticks = 5
    ticks += station.passengerNm * 5
    return ticks


def countTrainAlightingTime(train):
    ticks = 5
    l = len(train.carriageList)
    for i in range(0, l):
        ticks += train.carriageList[i].currentNum * 5
    return ticks


def countTrainIdleTime():
    return 9999


def countTrainShuntingime(lineA, lineB):
    if lineA == lineB:
        return 10
    return 20


###------------------------------------------>><<-----------------------------------------------------
# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    stationTypeList = {1: "square", 2: "triangel", 3: "circle"}
    print(stationTypeList)

    world = GameWorld()
    world.worldInit(trainNm=1, carriageNm=1, stationNm=2)

    world.printInformation()

    tr=train(1)
    print(tr)

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
