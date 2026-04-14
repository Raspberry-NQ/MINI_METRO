# train.py

from external_functions import (
    countTrainAlightingTime,
    countTrainBoardingTime,
    countTrainRunningTime,
    countTrainIdleTime,
    countTrainShuntingime,
)


class TrainError(Exception):
    """列车状态错误"""
    pass


trainStatusList = {
    1: "passengerAlighting",  # 乘客落车
    2: "passengerBoarding",   # 乘客上车
    3: "idle",                # 空闲中
    4: "running",             # 前往下一站中
    5: "shunting",            # 调车冷却中
}


class train:
    def __init__(self, number, config=None):
        self.number = number
        self.config = config
        self.line = None  # None代表未放置
        self.carriageList = []

        self.status = 3  # 初始空闲

        self.stationNow = None

        self.nextStatusTime = -1  # 空闲状态如果不做操作,应该是无限保持.因此为-1
        self.nextStatus = 3
        self.waitShunting = False       # 接到调车指令后，running和alighting时为True
        self.shuntingTargetLine = None  # 调车目标线路
        self.shuntingTargetStation = None  # 调车目标站点
        self.shuntingTargetDirection = None  # 调车目标方向
        self._shunting_arrival_station = None  # shunting完成后到达的站

    def __str__(self):
        line_str = str(self.line.number) if self.line else "None"
        station_str = str(self.stationNow.id) if self.stationNow else "None"
        return (f"<TRAIN/ID:{self.number}/{trainStatusList[self.status]}"
                f"/LINE[{line_str}]"
                f"/station ID:{station_str}"
                f"/carriageNum:{len(self.carriageList)}"
                f"/time:{self.nextStatusTime}/>")

    def connectCarriage(self, carriage):
        self.carriageList.append(carriage)

    def disconnectCarriage(self, carriage):
        """断开指定车厢"""
        if carriage in self.carriageList:
            self.carriageList.remove(carriage)
        else:
            raise TrainError(f"车厢 {carriage.number} 不在列车 {self.number} 上")

    '''
    以下五个函数写明了操作火车进入新的状态,并且返回在新的状态持续的时间,注意不是从上个状态转移到新状态的时间
    也就是说,在调用这五个函数时,上个状态应当以及结束了
    '''

    def setAlighting(self, station):
        if self.status != 4:
            raise TrainError(f"落客前状态不对,期望running(4),实际为{self.status}({trainStatusList[self.status]})")
        self.status = 1
        self.stationNow = station
        self.nextStatusTime = countTrainAlightingTime(self, self.config)
        self.nextStatus = 2  # 下一个状态一般是2
        return self.nextStatusTime

    def setBoarding(self, station):
        if self.status not in (1, 3, 5):
            raise TrainError(f"上客前状态不对,期望alighting/idle/shunting,实际为{self.status}({trainStatusList[self.status]})")
        self.status = 2
        self.stationNow = station
        self.nextStatusTime = countTrainBoardingTime(station, self.config)
        self.nextStatus = 4  # 下一个状态是4（运行）
        return self.nextStatusTime

    def setIdle(self):
        print("TRAIN ", self.number, "移入车库待命")
        self.status = 3
        self.stationNow = None
        self.nextStatusTime = countTrainIdleTime(self.config)
        self.nextStatus = 3  # 下一个状态一般是3
        return self.nextStatusTime

    def setRunning(self, nextStation):
        if self.status != 2:
            raise TrainError(f"出站前状态不对,期望boarding(2),实际为{self.status}({trainStatusList[self.status]})")
        self.status = 4
        # 不修改当前station,直到落客才修改
        self.nextStatusTime = countTrainRunningTime(self.stationNow, nextStation, self.config)
        self.nextStatus = 1  # 下一个状态一般是1
        return self.nextStatusTime

    def setShunting(self, nextLine, arrival_station=None):
        # 需要先进站落客再调车
        if not self.waitShunting:
            raise TrainError("调车前未设置waitShunting标志")
        self._shunting_arrival_station = arrival_station  # shunting完成后到达的站
        self.waitShunting = False
        self.shuntingTargetLine = None
        self.shuntingTargetStation = None
        self.shuntingTargetDirection = None
        self.status = 5
        self.stationNow = None
        self.nextStatusTime = countTrainShuntingime(self.line, nextLine, self.config)
        self.nextStatus = 2  # 下一个状态一般是到站直接上客,无需等待落客
        return self.nextStatusTime

    def printTrain(self):
        print("车头编号:", self.number)
        print("车辆状态:", trainStatusList[self.status])
        if self.status in (4, 1, 2):
            print("所在线路:", self.line)
            print("挂载车厢:", self.carriageList)
        if self.status == 5:
            print("调车冷却中!")
