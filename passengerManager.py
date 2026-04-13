# passenger_manager.py
from passenger import Passenger
from route_planner import RoutePlanner

class PassengerManager:
    def __init__(self, metro_system):
        self.passenger_list = []
        self.passenger_id_counter = 0
        self.route_planner = RoutePlanner(metro_system)
        self.metro_system = metro_system

    def generate_passenger(self, origin, destination, preference="fastest"):
        self.passenger_id_counter += 1
        passenger = Passenger(self.passenger_id_counter, origin, destination, preference)
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
        station = train.stationNow
        passengers_to_board = []
        for passenger in station.passenger_list[:]:
            if not passenger.should_board_train(train):
                continue
            # 检查车厢容量，无车厢或满员则跳过
            if not train.carriageList:
                continue
            carriage = train.carriageList[0]
            if len(carriage.passenger_list) >= carriage.capacity:
                continue
            if passenger.board_train(train):
                passengers_to_board.append(passenger)
                station.passenger_list.remove(passenger)
                station.passengerNm = len(station.passenger_list)
                for c in train.carriageList:
                    if len(c.passenger_list) < c.capacity:
                        c.passenger_list.append(passenger)
                        c.currentNum = len(c.passenger_list)
                        break
        return passengers_to_board

    def process_passenger_alighting(self, train):
        passengers_to_alight = []
        for carriage in train.carriageList:
            for passenger in carriage.passenger_list[:]:
                should_alight = False
                # 到达目的地
                if train.stationNow == passenger.destination_station:
                    should_alight = True
                # 到达路线中指定的换乘/下车站
                elif passenger.planned_route:
                    step = passenger.planned_route[passenger.current_route_index]
                    if step.get('station') == train.stationNow:
                        should_alight = True
                if should_alight:
                    passenger.alight_train(train.stationNow)
                    passengers_to_alight.append(passenger)
                    carriage.passenger_list.remove(passenger)
                    carriage.currentNum = len(carriage.passenger_list)
        for passenger in passengers_to_alight:
            if passenger.status != "arrived":
                train.stationNow.passenger_list.append(passenger)
                train.stationNow.passengerNm = len(train.stationNow.passenger_list)
        return passengers_to_alight

    def _should_transfer(self, passenger, current_station):
        if not passenger.planned_route or passenger.current_route_index >= len(passenger.planned_route):
            return False
        next_step = passenger.planned_route[passenger.current_route_index + 1]
        return next_step['transfer'] and next_step['station'] == current_station

    def update_all_passengers(self):
        for passenger in self.passenger_list[:]:
            passenger.update_waiting_time()

    def remove_passenger(self, passenger):
        if passenger in self.passenger_list:
            self.passenger_list.remove(passenger)
        if passenger.current_station and passenger in passenger.current_station.passenger_list:
            passenger.current_station.passenger_list.remove(passenger)
            passenger.current_station.passengerNm = len(passenger.current_station.passenger_list)
