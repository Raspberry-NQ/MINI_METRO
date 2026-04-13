# passenger.py

class Passenger:
    def __init__(self, passenger_id, origin_station, destination_station, preference="fastest"):
        self.passenger_id = passenger_id
        self.origin_station = origin_station
        self.destination_station = destination_station
        self.current_station = origin_station
        self.waiting_time = 0
        self.status = "waiting"
        self.patience = 100
        self.preference = preference
        self.planned_route = None
        self.current_route_index = 0
        self.target_line = None
        self.target_direction = None
        self.transfer_waiting = False

    def __str__(self):
        return f"<PASSENGER/ID:{self.passenger_id}/{self.origin_station.id}->{self.destination_station.id}/{self.status}/>"

    def plan_route(self, route_planner):
        self.planned_route = route_planner.find_route(
            self.origin_station,
            self.destination_station,
            self.preference
        )
        if self.planned_route:
            self._update_current_target()

    def _update_current_target(self):
        if not self.planned_route or self.current_route_index >= len(self.planned_route):
            return
        current_route_step = self.planned_route[self.current_route_index]
        self.target_line = current_route_step['line']
        self.target_direction = current_route_step['direction']

    def should_board_train(self, train):
        if not self.planned_route or self.status != "waiting":
            return False
        if train.line != self.target_line:
            return False
        if train.line.trainDirection.get(train) != self.target_direction:
            return False
        if train.stationNow != self.current_station:
            return False
        return True

    def board_train(self, train):
        if self.should_board_train(train):
            self.status = "on_train"
            self.current_station = None
            return True
        return False

    def alight_train(self, station):
        self.current_station = station
        # 完成当前路段, 推进到下一段
        self.current_route_index += 1
        if self.current_station == self.destination_station:
            self.status = "arrived"
        elif not self.planned_route or self.current_route_index >= len(self.planned_route):
            self.status = "arrived"
        else:
            self.status = "waiting"
            self._update_current_target()

    def update_waiting_time(self):
        self.waiting_time += 1

    def is_impatient(self):
        return self.waiting_time >= self.patience
