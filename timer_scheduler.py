# timer_scheduler.py — 计时调度器

class TimerScheduler:
    def __init__(self):
        self.events = []  # [(remaining_time, train, next_status)]

    def register(self, dt, train, next_status):
        self.events.append([dt, train, next_status])
        train.nextStatusTime = dt

    def update(self, dt=1):
        """推进时间 dt, 返回 (updated_trains, updated_statuses)"""
        updated_trains = []
        updated_statuses = []
        remaining = []
        for event in self.events:
            event[0] -= dt
            if event[0] <= 0:
                updated_trains.append(event[1])
                updated_statuses.append(event[2])
            else:
                remaining.append(event)
        self.events = remaining
        return updated_trains, updated_statuses
