# passengerManager.py

from passenger import Passenger
from route_planner import RoutePlanner


class PassengerManager:
    def __init__(self, metro_system, config=None):
        self.passenger_list = []
        self.passenger_id_counter = 0
        self.route_planner = RoutePlanner(metro_system, config)
        self.metro_system = metro_system
        self.config = config

    def generate_passenger(self, origin, destination, preference="fastest"):
        """生成新乘客并规划路径"""
        self.passenger_id_counter += 1
        patience = self.config.passenger_default_patience if self.config else 100
        passenger = Passenger(self.passenger_id_counter, origin, destination, preference, patience)
        passenger.plan_route(self.route_planner)

        if passenger.planned_route:
            self.passenger_list.append(passenger)
            origin.passenger_list.append(passenger)
            origin.passengerNm = len(origin.passenger_list)
            return passenger
        else:
            print(f"乘客 {passenger.passenger_id} 无法找到路径")
            return None

    def process_passenger_boarding(self, train):
        """处理乘客上车"""
        station = train.stationNow
        passengers_to_board = []

        for passenger in station.passenger_list[:]:  # 使用切片避免修改列表时的问题
            if passenger.should_board_train(train):
                # 先检查是否有空车厢
                has_capacity = any(
                    len(c.passenger_list) < c.capacity for c in train.carriageList
                ) if train.carriageList else False

                if not has_capacity:
                    continue  # 没有空位，乘客继续等

                if passenger.board_train(train):
                    passengers_to_board.append(passenger)
                    station.passenger_list.remove(passenger)
                    station.passengerNm = len(station.passenger_list)

                    # 将乘客添加到车厢
                    for carriage in train.carriageList:
                        if len(carriage.passenger_list) < carriage.capacity:
                            carriage.passenger_list.append(passenger)
                            carriage.currentNum = len(carriage.passenger_list)
                            break

        return passengers_to_board

    def process_passenger_alighting(self, train):
        """处理乘客下车"""
        passengers_to_alight = []

        for carriage in train.carriageList:
            for passenger in carriage.passenger_list[:]:
                if passenger.current_route_index >= len(passenger.planned_route) - 1:
                    # 到达目的地
                    passenger.alight_train(train.stationNow)
                    passengers_to_alight.append(passenger)
                    carriage.passenger_list.remove(passenger)
                    carriage.currentNum = len(carriage.passenger_list)
                elif self._should_transfer(passenger, train.stationNow):
                    # 需要换乘
                    passenger.alight_train(train.stationNow)
                    passengers_to_alight.append(passenger)
                    carriage.passenger_list.remove(passenger)
                    carriage.currentNum = len(carriage.passenger_list)

        # 将下车的乘客添加到站点
        for passenger in passengers_to_alight:
            if passenger.status != "arrived":
                train.stationNow.passenger_list.append(passenger)
                train.stationNow.passengerNm = len(train.stationNow.passenger_list)

        return passengers_to_alight

    def force_alight_all(self, train, station):
        """调车时强制所有乘客下车"""
        passengers_to_alight = []

        for carriage in train.carriageList:
            for passenger in carriage.passenger_list[:]:
                passenger.alight_train(station)
                if passenger.status != "arrived":
                    # 乘客未到达目的地，需要重新规划路径
                    passenger.status = "waiting"
                    passenger.transfer_waiting = False
                passengers_to_alight.append(passenger)
            carriage.passenger_list.clear()
            carriage.currentNum = 0

        # 将下车的乘客添加到站点
        for passenger in passengers_to_alight:
            if passenger.status != "arrived":
                station.passenger_list.append(passenger)
                station.passengerNm = len(station.passenger_list)

        return passengers_to_alight

    def _should_transfer(self, passenger, current_station):
        """判断乘客是否需要在当前站换乘"""
        if not passenger.planned_route or passenger.current_route_index >= len(passenger.planned_route):
            return False

        next_step = passenger.planned_route[passenger.current_route_index + 1]
        return next_step['transfer'] and next_step['station'] == current_station

    def update_all_passengers(self):
        """更新所有乘客状态"""
        for passenger in self.passenger_list[:]:
            passenger.update_waiting_time()

            if passenger.is_impatient() and passenger.status in ["waiting", "transferring"]:
                print(f"乘客 {passenger.passenger_id} 失去耐心离开了")
                self.remove_passenger(passenger)

    def remove_passenger(self, passenger):
        """移除乘客"""
        if passenger in self.passenger_list:
            self.passenger_list.remove(passenger)
        if passenger.current_station and passenger in passenger.current_station.passenger_list:
            passenger.current_station.passenger_list.remove(passenger)
            passenger.current_station.passengerNm = len(passenger.current_station.passenger_list)
