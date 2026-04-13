# world.py
import random
from station import station
from line import MetroLine
from train_inventory import TrainInventory
from passenger_manager import PassengerManager

class GameWorld:
    def __init__(self):
        self.stations = []
        self.metroLine = []
        self.passenger_manager = PassengerManager(self)
        self.trainInventory = TrainInventory(self.passenger_manager)

    def worldInit(self, trainNm=1, carriageNm=1, stationNm=2):
        print("世界初始化,车头", trainNm, "车厢", carriageNm, "站点", stationNm)
        for i in range(trainNm):
            self.trainInventory.addTrain()
        for i in range(carriageNm):
            self.trainInventory.addCarriage()
        nsta = station(1, 1, 0, 0)
        nstb = station(2, 2, 0, 10)
        self.stations.extend([nsta, nstb])
        linea = MetroLine(1, self.stations)
        self.metroLine.append(linea)
        self.trainInventory.employTrain(linea, nsta)
        for i, line in enumerate(self.metroLine):
            print("线路", i)
            line.printLine()

    def generate_random_passenger(self):
        if len(self.stations) >= 2:
            origin = random.choice(self.stations)
            destination = random.choice([s for s in self.stations if s != origin])
            preference = random.choice(["fastest", "least_transfer", "balanced"])
            return self.passenger_manager.generate_passenger(origin, destination, preference)
        return None

    def updateOneTick(self):
        self.trainInventory.updateAllTrain()
        self.passenger_manager.update_all_passengers()
        if random.randint(1, 10) == 1:
            self.generate_random_passenger()
        self.printInformation()
        print("---------------------------------------")

    def printInformation(self):
        print("车库信息")
        print("在运行车辆：", len(self.trainInventory.trainBusyList))
        for train in self.trainInventory.trainBusyList:
            print(train)
        print("站点线路信息")
        for station in self.stations:
            print(station)
        print("乘客信息")
        print("定时器状态")
        print("游戏状态")
