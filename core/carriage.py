# carriage.py — 车厢模块
#
# 本文件定义了车厢类，表示无动力载人车厢。


class carriage:
    """车厢类，表示无动力载人车厢"""

    def __init__(self, number, capacity=6):
        """初始化车厢

        参数:
            number: 车厢编号
            capacity: 车厢容量，默认为6
        """
        self.number = number
        self.line = 0
        self.capacity = capacity  # 车厢容量,默认为6
        self.currentNum = 0  # 当前人数
        self.passenger_list = []  # 存储车厢内的乘客对象

    def moveCarriage(self, lineNo):
        """移动车厢到指定线路

        参数:
            lineNo: 目标线路编号

        说明:
            注意此操作后,要到下一个站点才能正式操作
            先落客,然后判断去掉后是否为空车头,然后再修改
        """
        self.line = lineNo
