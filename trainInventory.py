# trainInventory.py

from train import train, TrainError, trainStatusList
from carriage import carriage
from timer_scheduler import TimerScheduler


class ResourceError(Exception):
    """资源不足错误"""
    pass


class TrainInventory:
    """记录所有火车和车厢信息。train代表动力不载人车头,carriage代表无动力载人车厢"""

    def __init__(self, passenger_manager=None, config=None):
        self.trainNm = 0
        self.carriageNm = 0

        self.trainBusyList = []
        self.carriageBusyList = []
        self.trainAbleList = []
        self.carriageAbleList = []

        self.trainTimer = TimerScheduler()
        self.passenger_manager = passenger_manager
        self.config = config

    def addTrain(self):
        self.trainNm += 1
        newTrain = train(self.trainNm, self.config)
        self.trainAbleList.append(newTrain)

    def addCarriage(self):
        self.carriageNm += 1
        cap = self.config.carriage_capacity if self.config else 6
        newCarr = carriage(self.carriageNm, cap)
        self.carriageAbleList.append(newCarr)

    def getFreeTrain(self):
        if len(self.trainAbleList) == 0:
            raise ResourceError("火车余额不足!(在getFreeTrain)")
        newtrain = self.trainAbleList[0]
        self.trainAbleList.remove(newtrain)
        self.trainBusyList.append(newtrain)
        return newtrain

    def getFreeCarriage(self):
        if len(self.carriageAbleList) == 0:
            raise ResourceError("车厢余额不足!(在getFreeCarriage)")
        newcarriage = self.carriageAbleList[0]
        self.carriageAbleList.remove(newcarriage)
        self.carriageBusyList.append(newcarriage)
        return newcarriage

    def employTrain(self, line, station, direction=True):
        """移动列车到线路,进入上客状态"""
        train_obj = self.getFreeTrain()
        nca = self.getFreeCarriage()
        train_obj.connectCarriage(nca)

        if line is None or line == train_obj.line:
            raise TrainError(f"无效线路,在employTrain()")

        dt = train_obj.setBoarding(station)
        line.addNewTrainToLine(train_obj, station, direction)
        self.trainTimer.register(dt, train_obj, train_obj.nextStatus)

    def shuntTrain(self, train_obj, goalLine, direction, station):
        """将列车从当前线路调到目标线路（立即调车，列车已停在站上）"""
        # 强制乘客下车
        if self.passenger_manager:
            self.passenger_manager.force_alight_all(train_obj, station)

        originLine = train_obj.line

        # 设置 waitShunting 标志，使 setShunting 可以调用
        train_obj.waitShunting = True
        train_obj.shuntingTargetLine = goalLine
        train_obj.shuntingTargetStation = station
        train_obj.shuntingTargetDirection = direction

        # setShunting 内部会用 self.line 计算调车时间，所以必须在 removeTrainFromLine 之前
        dt = train_obj.setShunting(goalLine, arrival_station=station)

        # 从原线路移除（setShunting 之后，此时 self.line 仍指向原线路）
        originLine.removeTrainFromLine(train_obj)

        # 加入新线路
        goalLine.addNewTrainToLine(train_obj, station, direction)
        self.trainTimer.register(dt, train_obj, train_obj.nextStatus)

    def updateAllTrain(self):
        updateTrain, updateStatus = self.trainTimer.update(dt=1)
        if len(updateTrain) != 0:
            print('''           -------------
                    ！！！有更新！！！
                    ---------------''')
        for i in range(0, len(updateTrain)):
            print(updateTrain[i])
            print(updateStatus[i])

            if updateStatus[i] == 1:  # 落客
                if updateTrain[i].status != 4:
                    raise TrainError(f"前状态有误,期望running(4),实际为{updateTrain[i].status}")
                # 列车到站，先调用 nextStation 获取目标站（可能自动掉头）
                arrival_station = updateTrain[i].line.nextStation(updateTrain[i])
                # 检查该站是否被同线路其他列车占用
                if self._is_station_occupied_by_same_line(updateTrain[i], arrival_station):
                    # 被占用，不能进站。将列车置于站外等待状态
                    updateTrain[i].stationNow = arrival_station  # 列车已到达该站外
                    updateTrain[i].status = 2  # 临时设为 boarding，以便 setWaiting 可以调用
                    dt = updateTrain[i].setWaiting(arrival_station, self.config, before_departure=False)
                    self.trainTimer.register(dt, updateTrain[i], updateTrain[i].nextStatus)
                    continue
                # 处理乘客下车
                if self.passenger_manager:
                    self.passenger_manager.process_passenger_alighting(updateTrain[i])
                dt = updateTrain[i].setAlighting(arrival_station)
                self.trainTimer.register(dt, updateTrain[i], updateTrain[i].nextStatus)
                continue

            elif updateStatus[i] == 2:  # 上客
                # 如果是从 shunting 转来，先恢复 stationNow
                if updateTrain[i].status == 5 and updateTrain[i]._shunting_arrival_station:
                    updateTrain[i].stationNow = updateTrain[i]._shunting_arrival_station
                    updateTrain[i]._shunting_arrival_station = None

                # 如果是从 waiting 转来，说明前方站之前被占用，重新检查
                if updateTrain[i].status == 6:
                    # waiting 结束，重新检查是否可以进入下一站
                    updateTrain[i].status = 2  # 临时恢复为 boarding 状态
                    waiting_target = updateTrain[i]._waiting_for_station
                    before_departure = updateTrain[i]._waiting_before_departure
                    updateTrain[i]._waiting_for_station = None

                    if before_departure:
                        # 出发前等待：检查前方站是否仍被占用
                        if updateTrain[i].line and updateTrain[i].line.isNextStationBlocked(updateTrain[i]):
                            dt = updateTrain[i].setWaiting(waiting_target, self.config, before_departure=True)
                            self.trainTimer.register(dt, updateTrain[i], updateTrain[i].nextStatus)
                            continue
                        # 前方站已空闲，可以出发
                        dt = updateTrain[i].setRunning(waiting_target)
                        self.trainTimer.register(dt, updateTrain[i], updateTrain[i].nextStatus)
                        continue
                    else:
                        # 到达站外等待：检查目标站是否仍被占用
                        if self._is_station_occupied_by_same_line(updateTrain[i], waiting_target):
                            dt = updateTrain[i].setWaiting(waiting_target, self.config, before_departure=False)
                            self.trainTimer.register(dt, updateTrain[i], updateTrain[i].nextStatus)
                            continue
                        # 前方站已空闲，处理落客并进站
                        if self.passenger_manager:
                            self.passenger_manager.process_passenger_alighting(updateTrain[i])
                        dt = updateTrain[i].setAlighting(waiting_target)
                        self.trainTimer.register(dt, updateTrain[i], updateTrain[i].nextStatus)
                        continue

                # 处理乘客上车
                if self.passenger_manager is None:
                    raise TrainError("passengermanager is None")
                else:
                    self.passenger_manager.process_passenger_boarding(updateTrain[i])

                if updateTrain[i].waitShunting:
                    # 收到调车指令
                    originLine = updateTrain[i].line
                    target_line = updateTrain[i].shuntingTargetLine
                    target_station = updateTrain[i].shuntingTargetStation
                    target_direction = updateTrain[i].shuntingTargetDirection
                    # 强制乘客下车
                    if self.passenger_manager:
                        self.passenger_manager.force_alight_all(updateTrain[i], target_station or updateTrain[i].stationNow)
                    # setShunting 在 removeTrainFromLine 之前调，因为需要 self.line 计算调车时间
                    dt = updateTrain[i].setShunting(target_line, arrival_station=target_station)
                    originLine.removeTrainFromLine(updateTrain[i])
                    target_line.addNewTrainToLine(updateTrain[i], target_station, target_direction)
                    self.trainTimer.register(dt, updateTrain[i], updateTrain[i].nextStatus)
                    continue
                else:
                    # 开始上客
                    next_station = updateTrain[i].stationNow
                    dt = updateTrain[i].setBoarding(next_station)
                    self.trainTimer.register(dt, updateTrain[i], updateTrain[i].nextStatus)
                    continue

            elif updateStatus[i] == 3:  # 等待/idle
                # idle 状态结束后，检查列车是否有线路和站点
                tr = updateTrain[i]
                if tr.line and tr.stationNow:
                    # 有线路且有站点，尝试重新上客
                    next_station = tr.line.nextStation(tr)
                    dt = tr.setBoarding(next_station)
                    self.trainTimer.register(dt, tr, tr.nextStatus)
                else:
                    # 没有线路或没有站点，继续空闲
                    dt = tr.setIdle()
                    self.trainTimer.register(dt, tr, tr.nextStatus)
                continue

            elif updateStatus[i] == 4:  # running
                if updateTrain[i].waitShunting:
                    # 列车正在运行但收到调车指令，等到达下一站后再调车
                    # 正常落客，在落客完成后（状态2）检查waitShunting
                    pass
                next_station = updateTrain[i].line.nextStation(updateTrain[i])
                # 检查前方站是否被占用
                if updateTrain[i].line.isNextStationBlocked(updateTrain[i]):
                    dt = updateTrain[i].setWaiting(next_station, self.config)
                    self.trainTimer.register(dt, updateTrain[i], updateTrain[i].nextStatus)
                    continue
                dt = updateTrain[i].setRunning(next_station)
                self.trainTimer.register(dt, updateTrain[i], updateTrain[i].nextStatus)
                continue

            else:
                raise TrainError(f"未知的nextStatus: {updateStatus[i]}")

    def printInformation(self):
        print("车库信息->")
        print("车头数量", self.trainNm)
        for i in range(0, len(self.trainBusyList)):
            print(self.trainBusyList[i])

        # 打印乘客信息
        if self.passenger_manager:
            print("乘客信息->")
            print("总乘客数量:", len(self.passenger_manager.passenger_list))
            for passenger in self.passenger_manager.passenger_list:
                print(f"乘客{passenger.passenger_id}: {passenger.status} 在站点{passenger.current_station} 等待时间:{passenger.waiting_time}")
        print("<-车库信息")

    def _is_station_occupied_by_same_line(self, train, station):
        """检查同一线路的其他列车是否已占据该站（非终点站时对向列车也算占用）

        用于 running→alighting 转换时的检查。
        running 状态的列车 stationNow 还是出发站，不算占用出发站。
        """
        line = train.line
        if line is None or station is None:
            return False

        # 终点站允许对向列车同时存在
        is_terminal = (station is line.stationList[0] or
                       station is line.stationList[-1])
        my_direction = line.trainDirection.get(train)

        for other_train, other_direction in line.trainDirection.items():
            if other_train is train:
                continue

            # running 状态的列车不算占用其出发站
            if other_train.status == 4:
                continue

            # 同方向：另一列车在该站就算占用
            if other_direction == my_direction:
                if other_train.stationNow is station:
                    return True

            # 非终点站：对向列车也占用
            if not is_terminal and other_direction != my_direction:
                if other_train.stationNow is station:
                    return True

        return False
