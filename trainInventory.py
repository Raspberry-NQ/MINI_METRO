# train_inventory.py
import sys
from timer_scheduler import TimerScheduler
from train import train
from carriage import carriage

class TrainInventory:
    def __init__(self, passenger_manager=None):
        self.trainNm = 0
        self.carriageNm = 0
        self.trainBusyList = []
        self.carriageBusyList = []
        self.trainAbleList = []
        self.carriageAbleList = []
        self.trainTimer = TimerScheduler()
        self.passenger_manager = passenger_manager

    def addTrain(self):
        self.trainNm += 1
        newTrain = train(self.trainNm)
        self.trainAbleList.append(newTrain)

    def addCarriage(self):
        self.carriageNm += 1
        newCarr = carriage(self.carriageNm)
        self.carriageAbleList.append(newCarr)

    def getFreeTrain(self):
        if not self.trainAbleList:
            sys.exit("火车余额不足!(在addTrainToLine)")
        newtrain = self.trainAbleList.pop(0)
        self.trainBusyList.append(newtrain)
        return newtrain

    def getFreeCarriage(self):
        if not self.carriageAbleList:
            sys.exit("车厢余额不足!(在addTrainToLine)")
        newcarriage = self.carriageAbleList.pop(0)
        self.carriageBusyList.append(newcarriage)
        return newcarriage

    def employTrain(self, line, station):
        train_obj = self.getFreeTrain()
        carriage_obj = self.getFreeCarriage()
        train_obj.connectCarriage(carriage_obj)
        if line == 0 or line == train_obj.line:
            sys.exit("FALSE LINE,in \"employTrain()\"")
        dt = train_obj.setBoarding(station)
        line.addNewTrainToLine(train_obj, station, True)
        self.trainTimer.register(dt, train_obj, train_obj.nextStatus)

    def shuntTrain(self, train, goalLine, direction, station):
        originLine = train.line
        originLine.removeTrainFromLine(train)
        stime = goalLine.shuntTrainToLine(train, direction, station)
        self.trainTimer.register(stime, train, train.nextStatus)

    def updateAllTrain(self):
        updateTrain, updateStatus = self.trainTimer.update(dt=1)
        if updateTrain:
            print("-------------\n！！！有更新！！！\n---------------")
        for i in range(len(updateTrain)):
            print(updateTrain[i])
            print(updateStatus[i])
            if updateStatus[i] == 1:  # 落客
                if updateTrain[i].status != 4:
                    sys.exit("前状态有误,1")
                if self.passenger_manager:
                    self.passenger_manager.process_passenger_alighting(updateTrain[i])
                dt = updateTrain[i].setAlighting(updateTrain[i].line.nextStation(updateTrain[i]))
                self.trainTimer.register(dt, updateTrain[i], updateTrain[i].nextStatus)
            elif updateStatus[i] == 2:  # 上客
                if self.passenger_manager is None:
                    sys.exit("passengermanager is None")
                else:
                    self.passenger_manager.process_passenger_boarding(updateTrain[i])
                if updateTrain[i].waitShunting:
                    updateTrain[i].waitShunting = False
                    dt = updateTrain[i].setShunting(updateTrain[i].shuntingTargetLine)
                    self.trainTimer.register(dt, updateTrain[i], updateTrain[i].nextStatus)
                else:
                    next_station = updateTrain[i].stationNow
                    dt = updateTrain[i].setBoarding(next_station)
                    self.trainTimer.register(dt, updateTrain[i], updateTrain[i].nextStatus)
            elif updateStatus[i] == 3:  # 等待
                if updateTrain[i].line and updateTrain[i].line.nextStation(updateTrain[i]):
                    dt = updateTrain[i].setBoarding(updateTrain[i].line.nextStation(updateTrain[i]))
                else:
                    dt = updateTrain[i].setIdle()
                self.trainTimer.register(dt, updateTrain[i], updateTrain[i].nextStatus)
            elif updateStatus[i] == 4:  # running
                dt = updateTrain[i].setRunning(updateTrain[i].line.nextStation(updateTrain[i]))
                self.trainTimer.register(dt, updateTrain[i], updateTrain[i].nextStatus)
            else:
                sys.exit("error nextstatus")
