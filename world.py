# world.py

import random
from station import station
from line import MetroLine
from passengerManager import PassengerManager
from trainInventory import TrainInventory


class GameWorld:
    def __init__(self):
        self.stations = []  # 所有Station
        self.metroLine = []  # 所有线路

        self.passenger_manager = PassengerManager(self)
        self.trainInventory = TrainInventory(self.passenger_manager)

    def worldInit(self, trainNm=1, carriageNm=1, stationNm=2):
        print("世界初始化,车头", trainNm, "车厢", carriageNm, "站点", stationNm)
        # 初始化资源
        for i in range(0, trainNm):
            self.trainInventory.addTrain()
        for i in range(0, carriageNm):
            self.trainInventory.addCarriage()
        nsta = station(1, 1, 0, 0)
        nstb = station(2, 2, 0, 10)
        self.stations.append(nsta)
        self.stations.append(nstb)

        linea = MetroLine(1, self.stations)
        self.metroLine.append(linea)

        self.trainInventory.employTrain(linea, nsta)

        for i in range(0, len(self.metroLine)):
            print("线路", i)
            self.metroLine[i].printLine()

    def playerTrainShunt(self):
        pass

    def playerLineExtension(self):
        pass

    def playerLineInsert(self):
        pass

    def playerPassTick(self):
        pass

    def generate_random_passenger(self):
        """生成随机乘客"""
        if len(self.stations) >= 2:
            origin = random.choice(self.stations)
            destination = random.choice([s for s in self.stations if s != origin])
            preference = random.choice(["fastest", "least_transfer", "balanced"])
            return self.passenger_manager.generate_passenger(origin, destination, preference)
        return None

    def updateOneTick(self):
        self.trainInventory.updateAllTrain()

        # 更新乘客状态
        self.passenger_manager.update_all_passengers()

        # 随机生成新乘客（每10个tick生成一个）
        if random.randint(1, 10) == 1:
            self.generate_random_passenger()
        self.printInformation()
        print("---------------------------------------")

    def updateWorld(self):
        pass

    def printInformation(self):
        """打印当前系统状态"""
        print("车库信息")
        print("在运行车辆：", self.trainInventory.trainBusyList.__len__())
        for i in self.trainInventory.trainBusyList:
            print(i)
        print("站点线路信息")
        for i in self.stations:
            print(i)
        print("乘客信息")
        print("定时器状态")
        print("游戏状态")
