# line.py
from external_functions import countTrainRunningTime

class MetroLine:
    def __init__(self, number, stList):
        self.number = number
        self.stationList = stList
        self.trainNm = 0
        self.trainDirection = {}

    def distance(self):
        dis = 0
        for i in range(len(self.stationList) - 1):
            dis += countTrainRunningTime(self.stationList[i], self.stationList[i + 1])
        return dis

    def addNewTrainToLine(self, train, station, direction):
        train.line = self
        self.trainDirection[train] = direction
        self.trainNm += 1

    def removeTrainFromLine(self, train):
        if train in self.trainDirection:
            self.trainNm -= 1
            self.trainDirection.pop(train)

    def shuntTrainToLine(self, train, direction, station):
        self.trainNm += 1
        self.trainDirection[train] = direction
        lt = train.setBoarding(station)
        return lt

    def nextStation(self, train):
        dire = self.trainDirection[train]
        if dire:
            p = self.stationList.index(train.stationNow)
            if p == len(self.stationList) - 1:
                print("终点站")
                self.trainDirection[train] = False
                return self.stationList[p - 1]
            else:
                return self.stationList[p + 1]
        else:
            p = self.stationList.index(train.stationNow)
            if p == 0:
                print("终点站")
                self.trainDirection[train] = True
                return self.stationList[p + 1]
            else:
                return self.stationList[p - 1]

    def printLine(self):
        print("正向起点", end="")
        for i, station in enumerate(self.stationList):
            if i > 0:
                print(" -> ", end="")
            print(f" ( [{i}]{station} ) ", end="")
        print(" -> 正向终点")
