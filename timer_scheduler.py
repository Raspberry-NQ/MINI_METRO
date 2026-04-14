# timer_scheduler.py

import heapq


class TimerScheduler:
    def __init__(self):
        self.events = []  # 最小堆: (trigger_time, seq, train, action)
        self.current_time = 0  # 游戏时间(秒)
        self._seq = 0  # 序列号，打破时间相同时的比较

    def register(self, delay, train, nextStatus):
        """注册定时事件
        delay: 延迟时间(秒)
        train: 列车对象
        nextStatus: 触发后应进入的状态
        """
        trigger_time = self.current_time + delay
        self._seq += 1
        heapq.heappush(self.events, (trigger_time, self._seq, train, nextStatus))

    def update(self, dt):
        """更新所有定时事件
        dt: 距离上次更新的时间增量(秒)
        """
        updateTrain = []
        updateStatus = []
        self.current_time += dt
        while self.events and self.events[0][0] <= self.current_time:
            _, trainout, nextStatus = self.events[0][1:]  # 跳过 seq
            heapq.heappop(self.events)
            updateTrain.append(trainout)
            updateStatus.append(nextStatus)
        print("需要更新的火车有", len(updateTrain), "个")
        self.printSchedule()
        return updateTrain, updateStatus

    def printSchedule(self):
        print("定时表START")
        print("时间:", self.current_time)
        for i in self.events:
            print(i[2], i[0], i[3])  # train, trigger_time, nextStatus
        print("定时表END")
