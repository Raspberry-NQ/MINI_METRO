# world.py — 游戏世界核心类
#
# 提供游戏世界的基本框架，包括站点、线路、列车和乘客管理。

import random
from core.station import station
from core.line import MetroLine
from core.passengerManager import PassengerManager
from core.trainInventory import TrainInventory


class GameWorld:
    """游戏世界类，管理所有游戏对象和资源

    属性:
        stations: 所有站点列表
        metroLine: 所有线路列表
        passenger_manager: 乘客管理器
        trainInventory: 列车库存管理器
    """

    def __init__(self):
        self.stations = []  # 所有Station
        self.metroLine = []  # 所有线路

        self.passenger_manager = PassengerManager(self)
        self.trainInventory = TrainInventory(self.passenger_manager)

    def worldInit(self, trainNm=1, carriageNm=1, stationNm=2):
        """初始化世界，创建初始资源

        参数:
            trainNm: 初始列车数量
            carriageNm: 初始车厢数量
            stationNm: 初始站点数量
        """
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
        """生成随机乘客

        返回:
            Passenger: 新生成的乘客对象，如果站点不足则返回 None
        """
        if len(self.stations) >= 2:
            origin = random.choice(self.stations)
            destination = random.choice([s for s in self.stations if s != origin])
            preference = random.choice(["fastest", "least_transfer", "balanced"])
            return self.passenger_manager.generate_passenger(origin, destination, preference)
        return None

    def updateOneTick(self):
        """更新一个游戏刻，包括列车、乘客状态和随机生成新乘客"""
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
        """打印当前系统状态，包括车库、站点、线路、乘客和定时器信息"""
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
