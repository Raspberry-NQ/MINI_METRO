# line.py

from external_functions import countTrainRunningTime


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

    def addNewTrainToLine(self, train, station, direction):
        """添加新车到线路"""
        train.line = self
        self.trainDirection[train] = direction
        self.trainNm += 1

    def removeTrainFromLine(self, train):
        """从线路移除列车（调车时使用），会清空 train.line"""
        if train in self.trainDirection:
            self.trainNm -= 1
            self.trainDirection.pop(train)
        train.line = None

    def shuntTrainToLine(self, train, direction, station):
        """调车到本线路，设置 train.line"""
        self.trainNm += 1
        self.trainDirection[train] = direction
        train.line = self
        lt = train.setBoarding(station)
        return lt

    def nextStation(self, train):
        """返回列车在当前方向上的下一站，到达终点站时自动掉头"""
        dire = self.trainDirection[train]
        if dire == True:
            p = self.stationList.index(train.stationNow)
            if p == len(self.stationList) - 1:
                self.trainDirection[train] = False
                return self.stationList[p - 1]
            else:
                return self.stationList[p + 1]
        else:
            p = self.stationList.index(train.stationNow)
            if p == 0:
                self.trainDirection[train] = True
                return self.stationList[p + 1]
            else:
                return self.stationList[p - 1]

    def isAtDestination(self, train):
        dire = self.trainDirection[train]
        if dire == True:
            p = self.stationList.index(train.stationNow)
            return p == len(self.stationList) - 1
        else:
            p = self.stationList.index(train.stationNow)
            return p == 0

    def printLine(self):
        print("正向起点", end="")
        for i, station in enumerate(self.stationList):
            if i > 0:
                print(" -> ", end="")
            print(f" ( [{i}]{station} ) ", end="")
        print(" -> 正向终点")
