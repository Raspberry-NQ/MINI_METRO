# carriage.py


class carriage:
    def __init__(self, number):
        self.number = number
        self.line = 0
        self.capacity = 6  # 车厢容量,默认为6
        self.currentNum = 0  # 当前人数
        self.passenger_list = []  # 存储车厢内的乘客对象

    def moveCarriage(self, lineNo):
        # 注意此操作后,要到下一个站点才能正式操作
        # 先落客,然后判断去掉后是否为空车头,然后再修改
        self.line = lineNo
