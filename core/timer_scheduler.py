# timer_scheduler.py — 定时调度器模块
#
# 本文件实现基于最小堆的定时事件调度器，用于管理列车状态转换的定时事件。

import heapq


class TimerScheduler:
    """定时调度器类，管理定时事件的注册和触发"""

    def __init__(self, debug=False):
        """初始化定时调度器

        参数:
            debug: 是否输出调试信息
        """
        self.events = []  # 最小堆: (trigger_time, seq, train, action)
        self.current_time = 0  # 游戏时间(秒)
        self._seq = 0  # 序列号，打破时间相同时的比较
        self.debug = debug

    def register(self, delay, train, nextStatus):
        """注册定时事件

        参数:
            delay: 延迟时间(秒)
            train: 列车对象
            nextStatus: 触发后应进入的状态
        """
        trigger_time = self.current_time + delay
        self._seq += 1
        heapq.heappush(self.events, (trigger_time, self._seq, train, nextStatus))

    def update(self, dt):
        """更新所有定时事件

        参数:
            dt: 距离上次更新的时间增量(秒)

        返回:
            tuple: (updateTrain, updateStatus) 需要更新的列车列表和状态列表
        """
        updateTrain = []
        updateStatus = []
        self.current_time += dt
        while self.events and self.events[0][0] <= self.current_time:
            _, trainout, nextStatus = self.events[0][1:]  # 跳过 seq
            heapq.heappop(self.events)
            updateTrain.append(trainout)
            updateStatus.append(nextStatus)
        if self.debug:
            print("需要更新的火车有", len(updateTrain), "个")
            self.printSchedule()
        return updateTrain, updateStatus

    def printSchedule(self):
        """打印定时表信息"""
        if not self.debug:
            return
        print("定时表START")
        print("时间:", self.current_time)
        for i in self.events:
            print(i[2], i[0], i[3])  # train, trigger_time, nextStatus
        print("定时表END")
