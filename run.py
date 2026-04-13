# run.py — 运行迷你地铁世界
import random
from station import station
from line import MetroLine
from trainInventory import TrainInventory
from passengerManager import PassengerManager
from passenger import Passenger

OVERCROWD_LIMIT = 15  # 站点人数超过此值则游戏结束

# ============================================================
# 构建世界
# ============================================================
class MetroWorld:
    def __init__(self):
        self.stations = []
        self.metroLine = []
        self.pm = PassengerManager(self)
        self.ti = TrainInventory(self.pm)
        self.tick = 0

    def setup(self):
        """两条线路, 共享换乘站"""
        # 线路1 站点: A(0) - B(1) - C(换乘) - D(3)
        sA = station(1, "circle",   0,   0)
        sB = station(2, "triangle", 100, 0)
        sC = station(3, "square",   200, 0)   # 换乘站
        sD = station(4, "diamond",  300, 0)

        # 线路2 站点: E(0) - C(换乘) - F(2)
        sE = station(5, "star",     200, -150)
        sF = station(6, "pentagon", 200, -300)

        self.stations = [sA, sB, sC, sD, sE, sF]

        line1 = MetroLine(1, [sA, sB, sC, sD])
        line2 = MetroLine(2, [sE, sC, sF])
        self.metroLine = [line1, line2]

        # 每条线2个车头, 每车头2节车厢
        for _ in range(4):
            self.ti.addTrain()
        for _ in range(8):
            self.ti.addCarriage()

        # 线路1: 列车1从起点正向, 列车2从终点反向
        self.ti.employTrain(line1, sA)
        self.ti.addCarriage()
        self.ti.trainBusyList[-1].connectCarriage(self.ti.getFreeCarriage())

        self.ti.employTrain(line1, sD)
        self.ti.addCarriage()
        self.ti.trainBusyList[-1].connectCarriage(self.ti.getFreeCarriage())
        # 修正方向: 从终点出发应该反向
        line1.trainDirection[self.ti.trainBusyList[-1]] = False

        # 线路2: 列车3从起点正向, 列车4从终点反向
        self.ti.employTrain(line2, sE)
        self.ti.addCarriage()
        self.ti.trainBusyList[-1].connectCarriage(self.ti.getFreeCarriage())

        self.ti.employTrain(line2, sF)
        self.ti.addCarriage()
        self.ti.trainBusyList[-1].connectCarriage(self.ti.getFreeCarriage())
        # 修正方向: 从终点出发应该反向
        line2.trainDirection[self.ti.trainBusyList[-1]] = False

        print("=" * 60)
        print("世界初始化完成")
        print(f"站点数: {len(self.stations)}")
        print(f"线路数: {len(self.metroLine)}")
        print(f"列车数: {len(self.ti.trainBusyList)}")
        for line in self.metroLine:
            line.printLine()
        print("=" * 60)

    def generate_random_passenger(self):
        if len(self.stations) < 2:
            return
        origin = random.choice(self.stations)
        destinations = [s for s in self.stations if s != origin]
        if not destinations:
            return
        dest = random.choice(destinations)
        self.pm.generate_passenger(origin, dest)

    def check_overcrowd(self):
        for s in self.stations:
            if s.passengerNm >= OVERCROWD_LIMIT:
                return s
        return None

    def print_status(self):
        print(f"\n--- Tick {self.tick} ---")
        print("站点候车:")
        for s in self.stations:
            marker = " !!!" if s.passengerNm >= OVERCROWD_LIMIT - 2 else ""
            print(f"  {s} 等候{ s.passengerNm}人{marker}")
        print("列车状态:")
        for tr in self.ti.trainBusyList:
            carriage_info = ""
            for c in tr.carriageList:
                carriage_info += f" [{c.currentNum}/{c.capacity}]"
            print(f"  {tr}{carriage_info}")

    def run(self, max_ticks=500):
        self.setup()
        while self.tick < max_ticks:
            self.tick += 1

            # 更新列车
            self.ti.updateAllTrain()

            # 更新乘客等待时间
            self.pm.update_all_passengers()

            # 随机生成乘客 (越来越频繁)
            spawn_chance = min(0.4, 0.08 + self.tick * 0.002)
            if random.random() < spawn_chance:
                self.generate_random_passenger()
            if self.tick > 50 and random.random() < spawn_chance * 0.5:
                self.generate_random_passenger()

            # 每 10 tick 打印一次
            if self.tick % 10 == 0:
                self.print_status()

            # 检查拥堵
            crowded = self.check_overcrowd()
            if crowded:
                print(f"\n{'!' * 60}")
                print(f"游戏结束! 站点 {crowded} 过度拥堵! (等候{crowded.passengerNm}人)")
                print(f"共经过 {self.tick} 个 tick")
                print(f"{'!' * 60}")
                self.print_status()

                # 打印最终统计
                arrived = sum(1 for p in self.pm.passenger_list if p.status == "arrived")
                on_train = sum(1 for p in self.pm.passenger_list if p.status == "on_train")
                waiting = sum(1 for p in self.pm.passenger_list if p.status == "waiting")
                print(f"\n统计: 到达={arrived}, 在车上={on_train}, 等候中={waiting}")
                return

        print(f"\n达到最大tick数 {max_ticks}, 游戏未结束")
        self.print_status()


if __name__ == "__main__":
    world = MetroWorld()
    world.run()
