# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.

from queue import Queue
###------------------------------------------>><<-----------------------------------------------------
##引入库
import sys

###------------------------------------------>><<-----------------------------------------------------
# 原子基础类
trainStatusList = {1: "passengerAlighting",  # 乘客落车
                   2: "passengerBoarding",  # 乘客上车
                   3: "idle",  # 空闲中
                   4: "running",  # 前往下一站中
                   5: "shunting"}  # 调车冷却中


# 注意列车状态是先下后上
class train:
    def __init__(self, number):
        self.number = number
        self.line = 0  # 0代表未放置
        self.status = 3
        self.carriageList = []
        self.stationNow = None

        self.nextStatusTime = -1  # 空闲状态如果不做操作,应该是无限保持.因此为-1
        self.nextStatus = 3

    def moveTrain(self, lineNo):
        self.line = lineNo

    def updateStatus(self):
        self.nextStatusTime -= 1
        if self.nextStatusTime == 0:  # 进入下一个状态
            self.status = self.nextStatus

    def trainArrive(self, station):
        self.status = 1
        self.nextStatusTime = countTrainBoardingTime(station)
        self.stationNow = station
        self.nextStatus = 2  # 下一状态改为落客

    def trainLeaveStation(self):
        self.status = 4
        self.nextStatus = 1
        self.nextStatusTime = calculateDistance()

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


class Station:
    def __init__(self, type, x, y):
        self.type = type  # 参考stationTypeList,目前只有1,2,3
        self.x = x
        self.y = y
        self.passengerNm = 0
        self.connections = []  # 存储连接的Station对象

    def printStation(self):
        print("Type:", end="")
        print(self.type)
        print("x:", self.x, " y:", self.y)


###------------------------------------------>><<-----------------------------------------------------
# 集合类
class trainInventory:  # 记录所有火车和车厢信息.以及注意:train代表动力不载人车头,carriage代表无动力载人车厢
    def __init__(self):
        self.trainNm = 0
        self.carriageNm = 0

        self.trainBusyList = []
        self.carriageBusyList = []
        self.trainAbleList = []
        self.carriageAbleList = []

    def addTrain(self):
        self.trainNm += 1
        newTrain = train(self.trainNm)
        self.trainAbleList.append(newTrain)

    def addCarriage(self):
        self.carriageNm += 1
        newCarr = carriage(self.carriageNm)
        self.carriageAbleList.append(newCarr)

    def employeeTrain(self, train, line, station):  # 移动列车到线路,进入状态1
        if line == 0 or line == train.line:
            print("FALSE LINE")
            sys.exit("FALSE LINE,in \"employeeTrain()\"")
        train.line = line
        train.status = 1  # 进入上客状态
        train.stationNow = station
        train.nextStatusTime = countTrainBoardingTime(station)


class MetroLine:
    def __init__(self, number, stList):
        self.number = number
        self.stations = stList
        self.trainNm = 0

    def distance(self):  # 单位为刻
        dis = 0
        for i in range(0, len(self.stations) - 1):
            dis = dis + calculateDistance(self.stations[i].x,
                                          self.stations[i].y,
                                          self.stations[i + 1].x,
                                          self.stations[i + 1].y)
        return dis

    def addTrainToLine(self, trainInventory):  # 返回是否成功,和加入火车的编号
        isSucc = False
        if trainInventory.trainAble > 0:
            # 减少一个火车和车厢

            # 注册车头车厢到线路

            # 记录车辆起始点和方向,注册速度

            # 注册上客和过站策略

            return isSucc
        else:
            sys.exit("火车余额不足!(在addTrainToLine)")


###------------------------------------------>><<-----------------------------------------------------
# 世界状态管理
class GameWorld:
    def __init__(self):
        self.stations = []  # Station实例列表
        self.trains = []  # Train实例列表
        self.metroLine = []

    def showInformation(self):
        count = 0
        for i in self.stations:
            print("station", count)
            i.printStation()
            count = count + 1


###------------------------------------------>><<-----------------------------------------------------
# 外部独立函数
def calculateDistance(x1, y1, x2, y2):
    d = round(((x1 - x2) ** 2 + (y1 - y2) ** 2) ** (1 / 2))
    return d


def claculateDistance(sta, stb):
    d = calculateDistance(sta.x, sta.y, stb.x, stb.y)
    return d


def countTrainBoardingTime(station):
    ticks = 5
    ticks += station.passengerNm * 5
    return ticks


###------------------------------------------>><<-----------------------------------------------------
# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    stationTypeList = {1: "square", 2: "triangel", 3: "circle"}
    print(stationTypeList)

    world = GameWorld()

    world.stations.append(Station(1, 0, 0))
    world.stations.append(Station(2, 232, 76))
    world.stations.append(Station(3, 125, 120))
    world.showInformation()
    print(calculateDistance(1, 2, 3, 4))
    trainTest = train(1)
    trainTest.printTrain()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
