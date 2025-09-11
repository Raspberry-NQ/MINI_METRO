# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.


def print_hi(name):
    # Use a breakpoint in the code line below to debug your script.
    print(f'Hi, {name}')  # Press Ctrl+F8 to toggle the breakpoint.


def goOneTick():
    print("update")


class Station:
    def __init__(self, type, x, y):
        self.type = type  # 参考stationTypeList,目前只有1,2,3
        self.x = x
        self.y = y
        self.passengers = []
        self.connections = []  # 存储连接的Station对象

    def printStation(self):
        print("Type:", end="")
        print(self.type)
        print("x:", self.x, " y:", self.y)


class trainInventory:  # 记录所有火车和车厢信息.以及注意:train代表动力不载人车头,carriage代表无动力载人车厢
    def __init__(self):
        self.trainList = []
        self.trainNm = 0
        self.carriageList = []
        self.carriageNm = 0
        self.capacity = 6  # 车厢容量,默认为6

        self.trainAble = 0
        self.carriageAble = 0

    def addTrain(self, Nm=1):
        self.trainNm += Nm
        self.carriageNm += Nm
        self.trainAble += Nm
        self.carriageAble += Nm


class MetroLine:
    def __init__(self, number, stList):
        self.number = number
        self.stations = stList
        self.trainNm = 0

    def distance(self):
        dis = 0
        for i in range(0, len(self.stations) - 1):
            dis = dis + calculateDistance(self.stations[i].x, self.stations[i].y, self.stations[i + 1].x,
                                          self.stations[i + 1].y)
        return dis

    def addTrain(self, trainInventory):  # 返回是否成功,和加入火车的编号
        isSucc = False
        if trainInventory.trainNm
            return isSucc


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


def calculateDistance(x1, y1, x2, y2):
    d = round(((x1 - x2) ** 2 + (y1 - y2) ** 2) ** (1 / 2))
    return d


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    stationTypeList = {}
    stationTypeList[1] = "square"
    stationTypeList[2] = "triangel"
    stationTypeList[3] = "circle"
    print(stationTypeList)

    world = GameWorld()

    world.stations.append(Station(1, 0, 0))
    world.stations.append(Station(2, 232, 76))
    world.stations.append(Station(3, 125, 120))
    world.showInformation()
    print(calculateDistance(1, 2, 3, 4))

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
