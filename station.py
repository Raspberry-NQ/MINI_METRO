# station.py

class station:
    def __init__(self, id, type, x, y):
        self.id = id
        self.type = type
        self.x = x
        self.y = y
        self.passengerNm = 0
        self.passenger_list = []
        self.connections = []

    def __str__(self):
        return f"<STATION/ID:{self.id}/TYPE:{self.type} / x:{self.x} y:{self.y} /> "

    def printStation(self):
        print("Type:", end="")
        print(self.type, end=" / ")
        print("x:", self.x, " y:", self.y, end=" /")
