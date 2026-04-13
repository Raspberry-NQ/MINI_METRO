# carriage.py

class carriage:
    def __init__(self, number):
        self.number = number
        self.line = 0
        self.capacity = 6
        self.currentNum = 0
        self.passenger_list = []

    def moveCarriage(self, lineNo):
        self.line = lineNo
