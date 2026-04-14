# line.py

from external_functions import countTrainRunningTime


class MetroLine:
    def __init__(self, number, stList):
        self.number = number
        self.stationList = list(stList)

        self.trainNm = 0
        self.trainDirection = {}  # True为正向,False为反向

        # 初始化 station.connections
        self._rebuild_connections()

    # ---- 线路修改 ----

    def addStation(self, station):
        """在线路末端延伸一个站点"""
        self.stationList.append(station)
        # 更新连接关系：新站与前一站互为邻居
        if len(self.stationList) >= 2:
            prev = self.stationList[-2]
            self._add_connection(prev, station)
        self._invalidate_route_cache()

    def insertStation(self, index, station):
        """在指定位置插入一个站点"""
        index = max(0, min(index, len(self.stationList)))
        self.stationList.insert(index, station)

        # 重修连接关系
        self._rebuild_connections()
        self._invalidate_route_cache()

    def removeStation(self, station):
        """移除一个站点，线路上正在运营的列车如果有此站点需要注意"""
        if station not in self.stationList:
            return False

        self.stationList.remove(station)
        self._rebuild_connections()
        self._invalidate_route_cache()
        return True

    # ---- 连接关系维护 ----

    def _add_connection(self, stA, stB):
        """双向添加站点连接"""
        if stB not in stA.connections:
            stA.connections.append(stB)
        if stA not in stB.connections:
            stB.connections.append(stA)

    def _remove_connection(self, stA, stB):
        """双向移除站点连接（仅当两站不再被同一线路相邻连接时才移除）"""
        # 检查是否还有其他线路让这两站相邻
        # 这里简单处理：直接移除，由 _rebuild_connections 重建
        if stB in stA.connections:
            stA.connections.remove(stB)
        if stA in stB.connections:
            stB.connections.remove(stA)

    def _rebuild_connections(self):
        """根据当前 stationList 重建相邻站点的连接关系"""
        # 先清掉由本线路维护的连接
        # 由于无法区分哪些连接是本线路添加的，采用全部重建策略
        # 清除所有站点的 connections，再由所有线路重建
        # 注意：此方法只负责本线路的连接，全局重建由 World 调用
        for i in range(len(self.stationList)):
            st = self.stationList[i]
            # 不在此处清空，只添加
            if i > 0:
                self._add_connection(self.stationList[i - 1], st)

    def _invalidate_route_cache(self):
        """线路变更后需要使路径缓存失效，由 World 负责调用 route_planner.invalidate_cache()"""
        pass

    # ---- 列车管理 ----

    def distance(self):  # 单位为刻
        dis = 0
        for i in range(0, len(self.stationList) - 1):
            dis = dis + countTrainRunningTime(self.stationList[i], self.stationList[i + 1])
        return dis

    def addNewTrainToLine(self, train, station, direction):
        """添加新车到线路"""
        train.line = self
        self.trainDirection[train] = direction
        self.trainNm += 1

    def removeTrainFromLine(self, train):
        """从线路移除列车（调车时使用），会清空 train.line"""
        if train in self.trainDirection:
            self.trainNm -= 1
            self.trainDirection.pop(train)
        train.line = None

    def shuntTrainToLine(self, train, direction, station):
        """调车到本线路，设置 train.line"""
        self.trainNm += 1
        self.trainDirection[train] = direction
        train.line = self
        lt = train.setBoarding(station)
        return lt

    def nextStation(self, train):
        """返回列车在当前方向上的下一站，到达终点站时自动掉头"""
        if not self.stationList or train not in self.trainDirection:
            return None

        dire = self.trainDirection[train]
        if dire == True:
            p = self.stationList.index(train.stationNow)
            if p == len(self.stationList) - 1:
                self.trainDirection[train] = False
                if p - 1 < 0:
                    return None
                return self.stationList[p - 1]
            else:
                return self.stationList[p + 1]
        else:
            p = self.stationList.index(train.stationNow)
            if p == 0:
                self.trainDirection[train] = True
                if p + 1 >= len(self.stationList):
                    return None
                return self.stationList[p + 1]
            else:
                return self.stationList[p - 1]

    def isAtDestination(self, train):
        dire = self.trainDirection[train]
        if dire == True:
            p = self.stationList.index(train.stationNow)
            return p == len(self.stationList) - 1
        else:
            p = self.stationList.index(train.stationNow)
            return p == 0

    def printLine(self):
        print("正向起点", end="")
        for i, station in enumerate(self.stationList):
            if i > 0:
                print(" -> ", end="")
            print(f" ( [{i}]{station} ) ", end="")
        print(" -> 正向终点")
