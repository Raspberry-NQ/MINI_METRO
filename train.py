# train.py
import sys
from external_functions import (
    countTrainAlightingTime,
    countTrainBoardingTime,
    countTrainRunningTime,
    countTrainIdleTime,
    countTrainShuntingime
)

trainStatusList = {
    1: "passengerAlighting",
    2: "passengerBoarding",
    3: "idle",
    4: "running",
    5: "shunting"
}

class train:
    def __init__(self, number):
        self.number = number
        self.line = None
        self.carriageList = []
        self.status = 3
        self.stationNow = None
        self.nextStatusTime = -1
        self.nextStatus = 3
        self.waitShunting = False
        self.shuntingTargetLine = None

    def __str__(self):
        if self.stationNow:
            return f"<TRAIN/ID:{self.number}/{trainStatusList[self.status]}/LINE[{self.line.number}]/station ID:{self.stationNow.id}/carriageNum:{len(self.carriageList)}/time:{self.nextStatusTime}/>"
        else:
            return f"<TRAIN/ID:{self.number}/{trainStatusList[self.status]}/LINE[{self.line.number}]/station ID:None/carriageNum:{len(self.carriageList)}/time:{self.nextStatusTime}/>"

    def connectCarriage(self, carriage):
        self.carriageList.append(carriage)

    def setAlighting(self, station):
        if self.status != 4:
            sys.exit("落客前状态不对,在SETALIGHTING")
        self.status = 1
        self.stationNow = station
        self.nextStatusTime = countTrainAlightingTime(self)
        self.nextStatus = 2
        return self.nextStatusTime

    def setBoarding(self, station):
        if self.status not in (1, 3, 5):
            sys.exit("上客前状态不对,在setboarding")
        self.status = 2
        self.stationNow = station
        self.nextStatusTime = countTrainBoardingTime(station)
        self.nextStatus = 4
        return self.nextStatusTime

    def setIdle(self):
        print("TRAIN ", self.number, "移入车库待命")
        self.status = 3
        self.stationNow = None
        self.nextStatusTime = countTrainIdleTime()
        self.nextStatus = 3
        return self.nextStatusTime

    def setRunning(self, nextStation):
        if self.status != 2:
            sys.exit("出站前状态不对,在setrunning")
        self.status = 4
        self.nextStatusTime = countTrainRunningTime(self.stationNow, nextStation)
        self.nextStatus = 1
        return self.nextStatusTime

    def setShunting(self, nextLine):
        if not self.waitShunting:
            sys.exit("invalid")
        self.waitShunting = False
        self.status = 5
        self.stationNow = None
        self.nextStatusTime = countTrainShuntingime(self.line, nextLine)
        self.nextStatus = 2
        return self.nextStatusTime
