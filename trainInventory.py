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
        # 调车前先让所有乘客下车
        if self.passenger_manager and train.stationNow:
            self.passenger_manager.process_passenger_alighting(train)
        # 清空剩余乘客（不在当前站下车的也强制下车）
        for c in train.carriageList:
            for p in c.passenger_list[:]:
                p.alight_train(train.stationNow)
                if p.status != "arrived":
                    train.stationNow.passenger_list.append(p)
                    train.stationNow.passengerNm = len(train.stationNow.passenger_list)
            c.passenger_list.clear()
            c.currentNum = 0
        originLine = train.line
        originLine.removeTrainFromLine(train)
        stime = goalLine.shuntTrainToLine(train, direction, station)
        self.trainTimer.register(stime, train, train.nextStatus)

    def updateAllTrain(self):
        updateTrain, updateStatus = self.trainTimer.update(dt=1)
        for i in range(len(updateTrain)):
            if updateStatus[i] == 1:  # 落客
                if updateTrain[i].status != 4:
                    sys.exit("前状态有误,1")
                if self.passenger_manager:
                    self.passenger_manager.process_passenger_alighting(updateTrain[i])
                dt = updateTrain[i].setAlighting(updateTrain[i].nextStationTarget)
                self.trainTimer.register(dt, updateTrain[i], updateTrain[i].nextStatus)
            elif updateStatus[i] == 2:  # 上客
                if updateTrain[i].waitShunting:
                    dt = updateTrain[i].setShunting(updateTrain[i].shuntingTargetLine)
                    self.trainTimer.register(dt, updateTrain[i], updateTrain[i].nextStatus)
                elif updateTrain[i].stationNow is None and updateTrain[i].shuntingTargetStation:
                    # shunting 完成后在新线路上线
                    target_station = updateTrain[i].shuntingTargetStation
                    target_line = updateTrain[i].line
                    dt = updateTrain[i].setBoarding(target_station)
                    target_line.addNewTrainToLine(updateTrain[i], target_station, True)
                    if self.passenger_manager:
                        self.passenger_manager.process_passenger_boarding(updateTrain[i])
                    updateTrain[i].shuntingTargetStation = None
                    self.trainTimer.register(dt, updateTrain[i], updateTrain[i].nextStatus)
                else:
                    if self.passenger_manager is None:
                        sys.exit("passengermanager is None")
                    else:
                        self.passenger_manager.process_passenger_boarding(updateTrain[i])
                    current_station = updateTrain[i].stationNow
                    dt = updateTrain[i].setBoarding(current_station)
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
