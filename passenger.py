# passenger.py


class Passenger:
    def __init__(self, passenger_id, origin_station, destination_station, preference="fastest"):
        self.passenger_id = passenger_id
        self.origin_station = origin_station
        self.destination_station = destination_station
        self.current_station = origin_station
        self.waiting_time = 0
        self.status = "waiting"  # waiting, boarding, on_train, transferring, arrived
        self.preference = preference  # 路径偏好

        # 路径相关
        self.planned_route = None
        self.current_route_index = 0
        self.target_line = None
        self.target_direction = None
        self.transfer_waiting = False

    def __str__(self):
        return f"<PASSENGER/ID:{self.passenger_id}/{self.origin_station.id}->{self.destination_station.id}/{self.status}/>"

    def plan_route(self, route_planner):
        """规划路径"""
        self.planned_route = route_planner.find_route(
            self.origin_station,
            self.destination_station,
            self.preference
        )
        if self.planned_route:
            self._update_current_target()

    def _update_current_target(self):
        """更新当前目标线路和方向"""
        if not self.planned_route or self.current_route_index >= len(self.planned_route):
            return

        current_route_step = self.planned_route[self.current_route_index]
        # 起始站（index=0）的 line=None，需要看下一步才能知道要坐哪条线
        if current_route_step['line'] is None and self.current_route_index + 1 < len(self.planned_route):
            next_step = self.planned_route[self.current_route_index + 1]
            self.target_line = next_step['line']
            self.target_direction = next_step['direction']
        else:
            self.target_line = current_route_step['line']
            self.target_direction = current_route_step['direction']

    def should_board_train(self, train):
        """判断是否应该上这班车"""
        if not self.planned_route or self.status not in ("waiting", "transferring"):
            return False

        # 检查是否在正确的站点
        if train.stationNow != self.current_station:
            return False

        # 检查是否是目标线路
        if train.line != self.target_line:
            return False

        # 检查方向是否正确
        if train.line.trainDirection.get(train) != self.target_direction:
            return False

        return True

    def board_train(self, train):
        """上车"""
        if self.should_board_train(train):
            self.status = "on_train"
            self.current_station = None
            # 推进 route_index 到实际乘坐的线路步骤（跳过起点站）
            while (self.current_route_index < len(self.planned_route) - 1 and
                   self.planned_route[self.current_route_index]['line'] is None):
                self.current_route_index += 1
            return True
        return False

    def alight_train(self, station):
        """下车 — process_passenger_alighting 已将 current_route_index 推进到正确位置"""
        self.current_station = station

        if station is self.destination_station:
            self.status = "arrived"
        elif (self.planned_route and
              self.current_route_index + 1 < len(self.planned_route) and
              self.planned_route[self.current_route_index + 1]['line'] is not self.planned_route[self.current_route_index]['line']):
            # 下一步使用不同线路 → 换乘
            self.current_route_index += 1
            self.status = "transferring"
            self.transfer_waiting = True
            self._update_current_target()
        else:
            self.status = "waiting"
            self.transfer_waiting = False

    def update_waiting_time(self):
        """更新等待时间"""
        if self.status in ["waiting", "transferring"]:
            self.waiting_time += 1
