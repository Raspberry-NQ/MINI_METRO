# trainInventory.py — 列车库存管理模块
#
# 本文件负责管理所有列车和车厢的库存信息，包括空闲和忙碌状态的列车、
# 列车调度、定时更新等功能。

from core.train import train, TrainError, trainStatusList
from core.carriage import carriage
from core.timer_scheduler import TimerScheduler


class ResourceError(Exception):
    """资源不足错误"""
    pass


class TrainInventory:
    """记录所有火车和车厢信息。train代表动力不载人车头,carriage代表无动力载人车厢"""

    def __init__(self, passenger_manager=None, config=None, debug=False):
        """初始化列车库存

        参数:
            passenger_manager: 乘客管理器对象，默认为None
            config: 游戏配置对象，默认为None
            debug: 是否输出调试信息
        """
        self.trainNm = 0
        self.carriageNm = 0

        self.trainBusyList = []
        self.carriageBusyList = []
        self.trainAbleList = []
        self.carriageAbleList = []

        self.trainTimer = TimerScheduler(debug=debug)
        self.passenger_manager = passenger_manager
        self.config = config
        self.debug = debug

    def addTrain(self):
        """添加新列车到空闲列表"""
        self.trainNm += 1
        newTrain = train(self.trainNm, self.config)
        self.trainAbleList.append(newTrain)

    def addCarriage(self):
        """添加新车厢到空闲列表"""
        self.carriageNm += 1
        cap = self.config.carriage_capacity if self.config else 6
        newCarr = carriage(self.carriageNm, cap)
        self.carriageAbleList.append(newCarr)

    def getFreeTrain(self):
        """从空闲列表获取列车

        返回:
            train: 空闲列车对象

        异常:
            ResourceError: 火车余额不足
        """
        if len(self.trainAbleList) == 0:
            raise ResourceError("火车余额不足!(在getFreeTrain)")
        newtrain = self.trainAbleList[0]
        self.trainAbleList.remove(newtrain)
        self.trainBusyList.append(newtrain)
        return newtrain

    def getFreeCarriage(self):
        """从空闲列表获取车厢

        返回:
            carriage: 空闲车厢对象

        异常:
            ResourceError: 车厢余额不足
        """
        if len(self.carriageAbleList) == 0:
            raise ResourceError("车厢余额不足!(在getFreeCarriage)")
        newcarriage = self.carriageAbleList[0]
        self.carriageAbleList.remove(newcarriage)
        self.carriageBusyList.append(newcarriage)
        return newcarriage

    def employTrain(self, line, station, direction=True):
        """移动列车到线路,进入上客状态

        参数:
            line: 目标线路对象
            station: 上车站点对象
            direction: 运行方向，True=正向, False=反向，默认为True
        """
        train_obj = self.getFreeTrain()
        nca = self.getFreeCarriage()
        train_obj.connectCarriage(nca)

        if line is None or line == train_obj.line:
            raise TrainError(f"无效线路,在employTrain()")

        dt = train_obj.setBoarding(station)
        line.addNewTrainToLine(train_obj, station, direction)
        self.trainTimer.register(dt, train_obj, train_obj.nextStatus)

    def shuntTrain(self, train_obj, goalLine, direction, station):
        """将列车从当前线路调到目标线路（立即调车，列车已停在站上）

        参数:
            train_obj: 要调车的列车对象
            goalLine: 目标线路对象
            direction: 目标线路上的运行方向
            station: 调车到达的站点对象
        """
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
        """更新所有列车状态

        根据定时器触发的事件，更新列车状态。
        """
        updateTrain, updateStatus = self.trainTimer.update(dt=1)
        if self.debug and len(updateTrain) != 0:
            print('''           -------------
                    ！！！有更新！！！
                    ---------------''')
        for i in range(0, len(updateTrain)):
            if self.debug:
                print(updateTrain[i])
                print(updateStatus[i])

            try:
                self._update_single_train(updateTrain[i], updateStatus[i])
            except Exception as e:
                if self.debug:
                    print(f"[ERROR] 列车 {updateTrain[i].number} 更新出错(状态{updateStatus[i]}): {e}")
                # 尝试将出错列车置为 idle，避免后续卡死
                try:
                    updateTrain[i].status = 3
                    updateTrain[i].nextStatusTime = -1
                    updateTrain[i].nextStatus = 3
                except Exception:
                    pass

    def _update_single_train(self, train_obj, status_code):
        """处理单辆列车的状态转移，出错时不影响其他列车

        参数:
            train_obj: 列车对象
            status_code: 目标状态码
        """
        if status_code == 1:  # 落客
            if train_obj.status != 4:
                raise TrainError(f"前状态有误,期望running(4),实际为{train_obj.status}")
            # 列车到站，先调用 nextStation 获取目标站
            arrival_station = train_obj.line.nextStation(train_obj)

            # 如果没有下一站，说明到达终点，需要掉头
            if arrival_station is None:
                # 掉头
                if train_obj.line.turnAround(train_obj):
                    # 重新获取下一站
                    arrival_station = train_obj.line.nextStation(train_obj)
                    if arrival_station is None:
                        # 掉头后还是没有下一站，说明线路只有一个站或出错了
                        print(f"⚠️  列车{train_obj.number}掉头后仍无下一站，线路可能只有一个站点")
                        # 设置为空闲状态
                        dt = train_obj.setIdle()
                        self.trainTimer.register(dt, train_obj, train_obj.nextStatus)
                        return

            # 处理乘客下车
            if self.passenger_manager:
                self.passenger_manager.process_passenger_alighting(train_obj)
            dt = train_obj.setAlighting(arrival_station)
            self.trainTimer.register(dt, train_obj, train_obj.nextStatus)
            return

        elif status_code == 2:  # 上客
            # 如果是从 shunting 转来，先恢复 stationNow
            if train_obj.status == 5 and train_obj._shunting_arrival_station:
                train_obj.stationNow = train_obj._shunting_arrival_station
                train_obj._shunting_arrival_station = None

            # 处理乘客上车
            if self.passenger_manager is None:
                raise TrainError("passengermanager is None")
            else:
                self.passenger_manager.process_passenger_boarding(train_obj)

            if train_obj.waitShunting:
                # 收到调车指令
                originLine = train_obj.line
                target_line = train_obj.shuntingTargetLine
                target_station = train_obj.shuntingTargetStation
                target_direction = train_obj.shuntingTargetDirection
                # 强制乘客下车
                if self.passenger_manager:
                    self.passenger_manager.force_alight_all(train_obj, target_station or train_obj.stationNow)
                # setShunting 在 removeTrainFromLine 之前调，因为需要 self.line 计算调车时间
                dt = train_obj.setShunting(target_line, arrival_station=target_station)
                originLine.removeTrainFromLine(train_obj)
                target_line.addNewTrainToLine(train_obj, target_station, target_direction)
                self.trainTimer.register(dt, train_obj, train_obj.nextStatus)
                return
            else:
                # 开始上客
                next_station = train_obj.stationNow
                dt = train_obj.setBoarding(next_station)
                self.trainTimer.register(dt, train_obj, train_obj.nextStatus)
                return

        elif status_code == 3:  # 等待/idle
            # idle 状态结束后，检查列车是否有线路和站点
            if train_obj.line and train_obj.stationNow:
                # 有线路且有站点，尝试重新上客
                next_station = train_obj.line.nextStation(train_obj)
                dt = train_obj.setBoarding(next_station)
                self.trainTimer.register(dt, train_obj, train_obj.nextStatus)
            else:
                # 没有线路或没有站点，继续空闲
                dt = train_obj.setIdle()
                self.trainTimer.register(dt, train_obj, train_obj.nextStatus)
            return

        elif status_code == 4:  # running
            if train_obj.waitShunting:
                # 列车正在运行但收到调车指令，等到达下一站后再调车
                # 正常落客，在落客完成后（状态2）检查waitShunting
                pass

            next_station = train_obj.line.nextStation(train_obj)

            # 如果没有下一站，说明到达终点，需要掉头
            if next_station is None:
                # 掉头
                if train_obj.line.turnAround(train_obj):
                    next_station = train_obj.line.nextStation(train_obj)
                    if next_station is None:
                        # 掉头后还是没有下一站，线路可能只有一个站点
                        print(f"⚠️  列车{train_obj.number}无法找到下一站，设置为空闲")
                        dt = train_obj.setIdle()
                        self.trainTimer.register(dt, train_obj, train_obj.nextStatus)
                        return
                else:
                    # 无法掉头（不在终点站？）
                    print(f"⚠️  列车{train_obj.number}无法掉头，设置为空闲")
                    dt = train_obj.setIdle()
                    self.trainTimer.register(dt, train_obj, train_obj.nextStatus)
                    return

            # 正常运行
            dt = train_obj.setRunning(next_station)
            self.trainTimer.register(dt, train_obj, train_obj.nextStatus)
            return

        else:
            raise TrainError(f"未知的nextStatus: {status_code}")

    def printInformation(self):
        """打印库存信息

        输出列车信息和乘客信息。
        """
        if not self.debug:
            return
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

        参数:
            train: 列车对象
            station: 站点对象

        返回:
            bool: True表示被占用, False表示未被占用

        说明:
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
