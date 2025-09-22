# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.


#
###------------------------------------------>><<-----------------------------------------------------
##引入库
import sys
import time
import random

import heapq
from queue import Queue
from collections import defaultdict

###------------------------------------------>><<-----------------------------------------------------
# 路径规划系统
class RoutePlanner:
    def __init__(self, metro_system):
        self.metro_system = metro_system
        self.transfer_penalty = 5  # 换乘惩罚时间
        self.route_cache = {}  # 路径缓存
    
    def find_route(self, origin_station, destination_station, passenger_preference="fastest"):
        """
        寻找从起点到终点的最优路径
        passenger_preference: "fastest" (最快), "least_transfer" (最少换乘), "balanced" (平衡)
        """
        cache_key = (origin_station, destination_station, passenger_preference)
        if cache_key in self.route_cache:
            return self.route_cache[cache_key]
        
        # 构建图结构
        graph = self._build_transit_graph()
        
        # 根据乘客偏好选择算法
        if passenger_preference == "fastest":
            route = self._dijkstra_fastest(graph, origin_station, destination_station)
        elif passenger_preference == "least_transfer":
            route = self._dijkstra_least_transfer(graph, origin_station, destination_station)
        else:  # balanced
            route = self._dijkstra_balanced(graph, origin_station, destination_station)
        
        self.route_cache[cache_key] = route
        return route
    
    def _build_transit_graph(self):
        """构建地铁网络图"""
        graph = defaultdict(list)
        
        # 添加同一条线路内的连接
        for line in self.metro_system.metroLine:
            stations = line.stationList
            for i in range(len(stations) - 1):
                # 正向连接
                graph[stations[i]].append({
                    'station': stations[i + 1],
                    'line': line,
                    'direction': True,
                    'time': self._calculate_travel_time(stations[i], stations[i + 1]),
                    'transfer': False
                })
                # 反向连接
                graph[stations[i + 1]].append({
                    'station': stations[i],
                    'line': line,
                    'direction': False,
                    'time': self._calculate_travel_time(stations[i + 1], stations[i]),
                    'transfer': False
                })
        
        # 添加换乘连接（同一站点的不同线路）
        for station in self.metro_system.stations:
            lines_at_station = self._get_lines_at_station(station)
            for i, line1 in enumerate(lines_at_station):
                for line2 in lines_at_station[i + 1:]:
                    # 双向换乘连接
                    graph[station].append({
                        'station': station,
                        'line': line2,
                        'direction': None,  # 换乘时方向待定
                        'time': self.transfer_penalty,
                        'transfer': True
                    })
        
        return graph
    
    def _get_lines_at_station(self, station):
        """获取经过指定站点的所有线路"""
        lines = []
        for line in self.metro_system.metroLine:
            if station in line.stationList:
                lines.append(line)
        return lines
    
    def _calculate_travel_time(self, station1, station2):
        """计算两站之间的行驶时间"""
        return countTrainRunningTime(station1, station2)
    
    def _dijkstra_fastest(self, graph, start, end):
        """Dijkstra算法 - 寻找最快路径"""
        return self._dijkstra(graph, start, end, weight_func=lambda edge: edge['time'])
    
    def _dijkstra_least_transfer(self, graph, start, end):
        """Dijkstra算法 - 寻找最少换乘路径"""
        return self._dijkstra(graph, start, end, weight_func=lambda edge: 1000 if edge['transfer'] else 1)
    
    def _dijkstra_balanced(self, graph, start, end):
        """Dijkstra算法 - 平衡时间和换乘次数"""
        return self._dijkstra(graph, start, end, weight_func=lambda edge: edge['time'] + (50 if edge['transfer'] else 0))
    
    def _dijkstra(self, graph, start, end, weight_func):
        """通用Dijkstra算法实现"""
        distances = {start: 0}
        previous = {}
        pq = [(0, start)]
        
        while pq:
            current_dist, current = heapq.heappop(pq)
            
            if current == end:
                break
            
            if current_dist > distances.get(current, float('inf')):
                continue
            
            for edge in graph[current]:
                neighbor = edge['station']
                weight = weight_func(edge)
                new_dist = current_dist + weight
                
                if new_dist < distances.get(neighbor, float('inf')):
                    distances[neighbor] = new_dist
                    previous[neighbor] = (current, edge)
                    heapq.heappush(pq, (new_dist, neighbor))
        
        # 重构路径
        if end not in previous:
            return None
        
        path = []
        current = end
        while current != start:
            prev_station, edge = previous[current]
            path.insert(0, {
                'station': current,
                'line': edge['line'],
                'direction': edge['direction'],
                'transfer': edge['transfer']
            })
            current = prev_station
        
        path.insert(0, {
            'station': start,
            'line': None,
            'direction': None,
            'transfer': False
        })
        
        return path

###------------------------------------------>><<-----------------------------------------------------
# 原子基础类
trainStatusList = {1: "passengerAlighting",  # 乘客落车
                   2: "passengerBoarding",  # 乘客上车
                   3: "idle",  # 空闲中
                   4: "running",  # 前往下一站中
                   5: "shunting"}  # 调车冷却中


#
# 注意列车状态是先下后上
class train:
    def __init__(self, number):
        self.number = number
        self.line = None  # 0代表未放置
        self.carriageList = []

        self.status = 3

        self.stationNow = None

        self.nextStatusTime = -1  # 空闲状态如果不做操作,应该是无限保持.因此为-1
        self.nextStatus = 3
        self.waitShunting=False# 接到调车指令后，running和alighting时，该状态为TRUE。在使用setshunting后为false
        self.shuntingTargetLine=None# 同上

    def __str__(self):
        if self.stationNow:
            self.stationNow.printStation()
            return f" TRAIN[No.{self.number}] /{trainStatusList[self.status]}/LINE[{self.line.number}]/station:({self.stationNow.x},{self.stationNow.y})/{len(self.carriageList)} carriage/time:{self.nextStatusTime} "
        else:
            return f" TRAIN[No.{self.number}] /{trainStatusList[self.status]}/LINE[{self.line.number}]/station:None/{len(self.carriageList)} carriage/time:{self.nextStatusTime} "

    def connectCarriage(self, carriage):
        self.carriageList.append(carriage)

    '''
    以下五个函数写明了操作火车进入新的状态,并且返回在新的状态持续的时间,注意不是从上个状态转移到新状态的时间
    也就是说,在调用这五个函数时,上个状态应当以及结束了
    '''

    def setAlighting(self, station):
        if self.status != 4:
            sys.exit("落客前状态不对,在SETALIGHTING")
        self.status = 1
        self.stationNow = station
        self.nextStatusTime = countTrainAlightingTime(self)
        self.nextStatus = 2  # 下一个状态一般是2
        return self.nextStatusTime

    def setBoarding(self, station):
        if self.status not in (1,3, 5):
            sys.exit("上客前状态不对,在setboarding")
        self.status = 2
        self.stationNow = station
        self.nextStatusTime = countTrainBoardingTime(station)
        self.nextStatus = 4  # 下一个状态是4（运行）
        return self.nextStatusTime

    def setIdle(self):
        print("TRAIN ", self.number, "移入车库待命")
        self.status = 3
        self.stationNow = None
        self.nextStatusTime = countTrainIdleTime()
        self.nextStatus = 3  # 下一个状态一般是3
        return self.nextStatusTime

    def setRunning(self, nextStation):
        if self.status != 2:
            sys.exit("出站前状态不对,在setrunning")
        self.status = 4
        # 不修改当前station,直到落客才修改
        self.nextStatusTime = countTrainRunningTime(self.stationNow, nextStation)
        self.nextStatus = 1  # 下一个状态一般是1
        return self.nextStatusTime

    def setShunting(self, nextLine):
        # 需要先进站落客再调车
        if self.waitShunting == False:
            sys.exit("invalid")
        self.waitShunting =False
        self.status = 5
        self.stationNow = None
        self.nextStatusTime = countTrainShuntingime(self.line, nextLine)
        self.nextStatus = 2  # 下一个状态一般是到站直接上客,无需等待落客
        return self.nextStatusTime

    def printTrain(self):
        print("车头编号:", self.number)
        print("车辆状态:", trainStatusList[self.status])
        if self.status in (4, 1, 2):
            print("所在线路:", self.line)
            print("挂载车厢:", self.carriageList)
        if self.status == 5:
            print("调车冷却中!")


class Passenger:
    def __init__(self, passenger_id, origin_station, destination_station, preference="fastest"):
        self.passenger_id = passenger_id
        self.origin_station = origin_station
        self.destination_station = destination_station
        self.current_station = origin_station
        self.waiting_time = 0
        self.status = "waiting"  # waiting, boarding, on_train, transferring, arrived
        self.patience = 100
        self.preference = preference  # 路径偏好
        
        # 路径相关
        self.planned_route = None
        self.current_route_index = 0
        self.target_line = None
        self.target_direction = None
        self.transfer_waiting = False
        
    def plan_route(self, route_planner):
        """规划路径"""
        self.planned_route = route_planner.find_route(
            self.origin_station, 
            self.destination_station, 
            self.preference
        )
        if self.planned_route:
            self._update_current_target()
    
    def _update_current_target(self):
        """更新当前目标线路和方向"""
        if not self.planned_route or self.current_route_index >= len(self.planned_route):
            return
        
        current_route_step = self.planned_route[self.current_route_index]
        self.target_line = current_route_step['line']
        self.target_direction = current_route_step['direction']
    
    def should_board_train(self, train):
        """判断是否应该上这班车"""
        if not self.planned_route or self.status != "waiting":
            return False
        
        # 检查是否是目标线路
        if train.line != self.target_line:
            return False
        
        # 检查方向是否正确
        if train.line.trainDirection.get(train) != self.target_direction:
            return False
        
        # 检查是否在正确的站点
        if train.stationNow != self.current_station:
            return False
        
        return True
    
    def board_train(self, train):
        """上车"""
        if self.should_board_train(train):
            self.status = "on_train"
            self.current_station = None
            return True
        return False
    
    def alight_train(self, station):
        """下车"""
        self.current_station = station
        self.current_route_index += 1
        
        if station == self.destination_station:
            self.status = "arrived"
        else:
            # 检查是否需要换乘
            if (self.planned_route and 
                self.current_route_index < len(self.planned_route) and
                self.planned_route[self.current_route_index]['transfer']):
                self.status = "transferring"
                self.transfer_waiting = True
                self._update_current_target()
            else:
                self.status = "waiting"
                self.transfer_waiting = False
    
    def update_waiting_time(self):
        """更新等待时间"""
        if self.status in ["waiting", "transferring"]:
            self.waiting_time += 1
    
    def is_impatient(self):
        """检查是否失去耐心"""
        return self.waiting_time > self.patience

class carriage:
    def __init__(self, number):
        self.number = number
        self.line = 0
        self.capacity = 6  # 车厢容量,默认为6
        self.currentNum = 0  # 当前人数
        self.passenger_list = []  # 存储车厢内的乘客对象

    def moveCarriage(self, lineNo):  ###<<----------------
        # 注意此操作后,要到下一个站点才能正式操作
        # 先落客,然后判断去掉后是否为空车头,然后再修改
        self.line = lineNo


class station:
    def __init__(self, type, x, y):
        self.type = type  # 参考stationTypeList,目前只有1,2,3
        self.x = x
        self.y = y
        self.passengerNm = 0
        self.passenger_list = []  # 存储等待的乘客对象
        self.connections = []  # 存储连接的Station对象

    def __str__(self):
        return f"TYPE:{self.type} / x:{self.x} y:{self.y} / "

    def printStation(self):
        print("Type:", end="")
        print(self.type, end=" / ")
        print("x:", self.x, " y:", self.y, end=" /")


###------------------------------------------>><<-----------------------------------------------------
# 乘客管理系统
class PassengerManager:
    def __init__(self, metro_system):
        self.passenger_list = []
        self.passenger_id_counter = 0
        self.route_planner = RoutePlanner(metro_system)
        self.metro_system = metro_system
    
    def generate_passenger(self, origin, destination, preference="fastest"):
        """生成新乘客并规划路径"""
        self.passenger_id_counter += 1
        passenger = Passenger(self.passenger_id_counter, origin, destination, preference)
        passenger.plan_route(self.route_planner)
        
        if passenger.planned_route:
            self.passenger_list.append(passenger)
            origin.passenger_list.append(passenger)
            origin.passengerNm = len(origin.passenger_list)  # 更新乘客数量
            return passenger
        else:
            print(f"乘客 {passenger.passenger_id} 无法找到路径")
            return None
    
    def process_passenger_boarding(self, train):
        """处理乘客上车"""
        station = train.stationNow
        passengers_to_board = []
        
        for passenger in station.passenger_list[:]:  # 使用切片避免修改列表时的问题
            if passenger.should_board_train(train):
                if passenger.board_train(train):
                    passengers_to_board.append(passenger)
                    station.passenger_list.remove(passenger)
                    station.passengerNm = len(station.passenger_list)  # 更新乘客数量
                    
                    # 将乘客添加到车厢
                    if train.carriageList:
                        carriage = train.carriageList[0]  # 简化：使用第一个车厢
                        if len(carriage.passenger_list) < carriage.capacity:
                            carriage.passenger_list.append(passenger)
                            carriage.currentNum = len(carriage.passenger_list)
        
        return passengers_to_board
    
    def process_passenger_alighting(self, train):
        """处理乘客下车"""
        passengers_to_alight = []
        
        for carriage in train.carriageList:
            for passenger in carriage.passenger_list[:]:
                if passenger.current_route_index >= len(passenger.planned_route) - 1:
                    # 到达目的地
                    passenger.alight_train(train.stationNow)
                    passengers_to_alight.append(passenger)
                    carriage.passenger_list.remove(passenger)
                    carriage.currentNum = len(carriage.passenger_list)
                elif self._should_transfer(passenger, train.stationNow):
                    # 需要换乘
                    passenger.alight_train(train.stationNow)
                    passengers_to_alight.append(passenger)
                    carriage.passenger_list.remove(passenger)
                    carriage.currentNum = len(carriage.passenger_list)
        
        # 将下车的乘客添加到站点
        for passenger in passengers_to_alight:
            if passenger.status != "arrived":
                train.stationNow.passenger_list.append(passenger)
                train.stationNow.passengerNm = len(train.stationNow.passenger_list)
        
        return passengers_to_alight
    
    def _should_transfer(self, passenger, current_station):
        """判断乘客是否需要在当前站换乘"""
        if not passenger.planned_route or passenger.current_route_index >= len(passenger.planned_route):
            return False
        
        next_step = passenger.planned_route[passenger.current_route_index + 1]
        return next_step['transfer'] and next_step['station'] == current_station
    
    def update_all_passengers(self):
        """更新所有乘客状态"""
        for passenger in self.passenger_list[:]:
            passenger.update_waiting_time()
            
            if passenger.is_impatient() and passenger.status in ["waiting", "transferring"]:
                print(f"乘客 {passenger.passenger_id} 失去耐心离开了")
                self.remove_passenger(passenger)
    
    def remove_passenger(self, passenger):
        """移除乘客"""
        if passenger in self.passenger_list:
            self.passenger_list.remove(passenger)
        if passenger.current_station and passenger in passenger.current_station.passenger_list:
            passenger.current_station.passenger_list.remove(passenger)
            passenger.current_station.passengerNm = len(passenger.current_station.passenger_list)

###------------------------------------------>><<-----------------------------------------------------
# 集合类
class TrainInventory:  # 记录所有火车和车厢信息.以及注意:train代表动力不载人车头,carriage代表无动力载人车厢
    def __init__(self, passenger_manager=None):
        self.trainNm = 0
        self.carriageNm = 0

        self.trainBusyList = []
        self.carriageBusyList = []
        self.trainAbleList = []
        self.carriageAbleList = []

        self.trainTimer = TimerScheduler()
        self.passenger_manager = passenger_manager

    def addTrain(self):
        self.trainNm += 1
        newTrain = train(self.trainNm)
        self.trainAbleList.append(newTrain)

    def addCarriage(self):
        self.carriageNm += 1
        newCarr = carriage(self.carriageNm)
        self.carriageAbleList.append(newCarr)

    def getFreeTrain(self):
        if len(self.trainAbleList) == 0:
            sys.exit("火车余额不足!(在addTrainToLine)")
        newtrain = self.trainAbleList[0]
        self.trainAbleList.remove(newtrain)
        self.trainBusyList.append(newtrain)
        return newtrain

    def getFreeCarriage(self):
        if len(self.carriageAbleList) == 0:
            sys.exit("车厢余额不足!(在addTrainToLine)")
        newcarriage = self.carriageAbleList[0]
        self.carriageAbleList.remove(newcarriage)
        self.carriageBusyList.append(newcarriage)
        return newcarriage

    def employTrain(self, line, station):  # 移动列车到线路,进入状态1
        train=self.getFreeTrain()
        nca=self.getFreeCarriage()
        train.connectCarriage(nca)
        if line == 0 or line == train.line:
            print("FALSE LINE")
            sys.exit("FALSE LINE,in \"employTrain()\"")

        dt=train.setBoarding(station)
        line.addNewTrainToLine(train,station,True)
        self.trainTimer.register(dt, train,train.nextStatus)

    def shuntTrain(self, train, goalLine, direction, station):
        originLine = train.line
        originLine.removeTrainFromLine(train)
        stime = goalLine.shuntTrainToLine(train, direction, station)
        self.trainTimer.register(stime, train, train.nextStatus)

    def updateAllTrain(self):

        updateTrain, updateStatus = self.trainTimer.update(dt=1)
        if len(updateTrain) !=0:
            print('''           -------------
                    ！！！有更新！！！
                    ---------------''')
        for i in range(0, len(updateTrain)):
            print(updateTrain[i])
            print(updateStatus[i])

            if updateStatus[i] == 1:  # 落客
                if updateTrain[i].status != 4:
                    sys.exit("前状态有误,1")
                # 处理乘客下车
                if self.passenger_manager:
                    self.passenger_manager.process_passenger_alighting(updateTrain[i])
                dt=updateTrain[i].setAlighting(updateTrain[i].line.nextStation(updateTrain[i]))  # 如果到终点站则会在此处掉头
                self.trainTimer.register(dt,updateTrain[i],updateTrain[i].nextStatus)
                continue

            elif updateStatus[i] == 2:  # 上客
                # 处理乘客上车
                if self.passenger_manager:
                    self.passenger_manager.process_passenger_boarding(updateTrain[i])

                if updateTrain[i].waitShunting == True:
                    updateTrain[i].waitShunting = False
                    dt=updateTrain[i].setShunting(updateTrain[i].shuntingTargetLine)
                    self.trainTimer.register(dt, updateTrain[i], updateTrain[i].nextStatus)
                    continue
                else:
                    #开始上客
                    next_station = updateTrain[i].stationNow
                    dt=updateTrain[i].setBoarding(next_station)
                    self.trainTimer.register(dt, updateTrain[i], updateTrain[i].nextStatus)
                    continue

            elif updateStatus[i] == 3: #等待
                # 空闲状态结束后，尝试重新上客
                if updateTrain[i].line and updateTrain[i].line.nextStation(updateTrain[i]):
                    dt=updateTrain[i].setBoarding(updateTrain[i].line.nextStation(updateTrain[i]))
                    self.trainTimer.register(dt, updateTrain[i], updateTrain[i].nextStatus)
                else:
                    # 如果没有线路或无法找到下一站，继续空闲
                    dt=updateTrain[i].setIdle()
                    self.trainTimer.register(dt, updateTrain[i], updateTrain[i].nextStatus)
                continue

            elif updateStatus[i] == 4: #running
                dt=updateTrain[i].setRunning(updateTrain[i].line.nextStation(updateTrain[i]))
                self.trainTimer.register(dt, updateTrain[i], updateTrain[i].nextStatus)
                continue

            else:
                sys.exit("error nextstatus")

    def printInformation(self):
        print("车库信息->")
        print("车头数量",self.trainNm)
        for i in range(0,len(self.trainBusyList)):
            print(self.trainBusyList[i])
        
        # 打印乘客信息
        if self.passenger_manager:
            print("乘客信息->")
            print("总乘客数量:", len(self.passenger_manager.passenger_list))
            for passenger in self.passenger_manager.passenger_list:
                print(f"乘客{passenger.passenger_id}: {passenger.status} 在站点{passenger.current_station} 等待时间:{passenger.waiting_time}")
        print("<-车库信息")


class MetroLine:
    def __init__(self, number, stList):
        self.number = number
        self.stationList = stList

        self.trainNm = 0
        self.trainDirection = {}  # True为正向,False为反向

    def distance(self):  # 单位为刻
        dis = 0
        for i in range(0, len(self.stationList) - 1):
            dis = dis + countTrainRunningTime(self.stationList[i], self.stationList[i + 1])
        return dis

    def addNewTrainToLine(self, train, station,direction):  # 返回是否成功,和加入火车的编号

        train.line=self
        self.trainDirection[train] = direction
        self.trainNm += 1

    def removeTrainFromLine(self, train):  # 只有在调车时才会用到
        if train in self.trainDirection:
            self.trainNm -= 1
            self.trainDirection.pop(train)

    def shuntTrainToLine(self, train, direction, station):
        self.trainNm += 1
        self.trainDirection[train] = direction
        lt = train.setBoarding(station)
        return lt

    def nextStation(self, train):
        dire = self.trainDirection[train]
        if dire == True:
            p = self.stationList.index(train.stationNow)
            if p == len(self.stationList) - 1:
                print("终点站")
                self.trainDirection[train] = False
                return self.stationList[p - 1]
            else:
                return self.stationList[p + 1]
        else:
            p = self.stationList.index(train.stationNow)
            if p == 0:
                print("终点站")
                self.trainDirection[train] = True
                return self.stationList[p + 1]
            else:
                return self.stationList[p - 1]

    def isAtDestination(self, train):
        dire = self.trainDirection[train]
        if dire == True:
            p = self.stationList.index(train.stationNow)
            if p == len(self.stationList) - 1:
                return True
            else:
                return False
        else:
            p = self.stationList.index(train.stationNow)
            if p == 0:
                return True
            else:
                return False

    def printLine(self):
        print("正向起点", end="")
        for i, station in enumerate(self.stationList):
            if i > 0:
                print(" -> ", end="")
            print(f" ( [{i}]{station} ) ", end="")
        print(" -> 正向终点")


###------------------------------------------>><<-----------------------------------------------------

class TimerScheduler:
    def __init__(self):
        self.events = []  # 最小堆: (trigger_time, train_id, action)
        self.current_time = 0  # 游戏时间(秒)

    def register(self, delay, train, nextStatus):
        """注册定时事件
        delay: 延迟时间(秒)
        train_id: 列车标识
        """
        trigger_time = self.current_time + delay
        heapq.heappush(self.events, (trigger_time, train, nextStatus))

    def update(self, dt):
        """更新所有定时事件
        dt: 距离上次更新的时间增量(秒)
        """
        updateTrain = []
        updateStatus = []
        self.current_time += dt
        while self.events and self.events[0][0] <= self.current_time:
            _, trainout, nextStatus = heapq.heappop(self.events)
            updateTrain.append(trainout)
            updateStatus.append(nextStatus)
        print("定时器更新一次")
        print(self.events)
        print("需要更新的火车有", len(updateTrain), "个")
        self.printSchedule()
        return updateTrain, updateStatus

    def printSchedule(self):
        print("定时表STRAT")
        if self.current_time ==19:
            print("19!")
        print("时间:",self.current_time)
        for i in self.events:
            print(i[1],i[0],i[2])
        print("定时表END")

# 世界状态管理
class GameWorld:
    def __init__(self):
        self.stations = []  # 所有Station

        self.metroLine = []  # 所有线路

        self.passenger_manager = PassengerManager(self)
        self.trainInventory = TrainInventory(self.passenger_manager)

    def worldInit(self, trainNm=1, carriageNm=1, stationNm=2):
        print("世界初始化,车头", trainNm, "车厢", carriageNm, "站点", stationNm)
        # 初始化资源
        for i in range(0, trainNm):
            self.trainInventory.addTrain()
        for i in range(0, carriageNm):
            self.trainInventory.addCarriage()
        nsta = station(1, 0, 0)
        nstb = station(2, 0, 10)
        self.stations.append(nsta)
        self.stations.append(nstb)

        linea = MetroLine(1, self.stations)
        self.metroLine.append(linea)

        self.trainInventory.employTrain(linea,nsta)

        for i in range(0, len(self.metroLine)):
            print("线路", i)
            self.metroLine[i].printLine()

    def printInformation(self):
        count = 0
        for i in self.stations:
            print("station", count, end=">>")
            i.printStation()
            print("")
            count = count + 1
        self.trainInventory.printInformation()

    def playerTrainShunt(self):

        pass

    def playerLineExtension(self):
        pass

    def playerLineInsert(self):
        pass

    def playerPassTick(self):
        pass

    def generate_random_passenger(self):
        """生成随机乘客"""
        if len(self.stations) >= 2:
            origin = random.choice(self.stations)
            destination = random.choice([s for s in self.stations if s != origin])
            preference = random.choice(["fastest", "least_transfer", "balanced"])
            return self.passenger_manager.generate_passenger(origin, destination, preference)
        return None

    def updateOneTick(self):


        #playerCommand = input()
        '''
        q退出游戏,p直接过一个tick,shunt调动列车,n放置空闲列车,nc连接新车厢,cl修改线路
        '''
        '''
        while playerCommand != "q":

            if playerCommand == "p":
                print("跳过;")
            elif playerCommand == "shunt":
                print("输入要调动的车头")
            elif playerCommand == "n":
                print("输入新增车辆的线路")
            elif playerCommand == "nc":
                print("输入要连接到的车头")
            elif playerCommand == "cl":
                print("输入要修改的线路")
            else:
                print("输入有误")

            playerCommand = input()
        '''
        self.trainInventory.updateAllTrain()
        
        # 更新乘客状态
        self.passenger_manager.update_all_passengers()
        
        # 随机生成新乘客（每10个tick生成一个）
        if random.randint(1, 10) == 1:
            self.generate_random_passenger()
        
        print("---------------------------------------")
        self.trainInventory.printInformation()
        pass

    def updateWorld(self):
        pass


###------------------------------------------>><<-----------------------------------------------------
# 外部独立函数
def countTrainRunningTime(sta, stb):
    x1 = sta.x
    x2 = stb.x
    y1 = sta.y
    y2 = stb.y
    d = round(((x1 - x2) ** 2 + (y1 - y2) ** 2) ** (1 / 2))
    return d


def countTrainBoardingTime(station):
    ticks = 5
    ticks += station.passengerNm * 5
    return ticks


def countTrainAlightingTime(train):
    ticks = 5
    l = len(train.carriageList)
    for i in range(0, l):
        ticks += train.carriageList[i].currentNum * 5
    return ticks


def countTrainIdleTime():
    return 5  # 空闲状态持续5个tick，然后重新尝试上客


def countTrainShuntingime(lineA, lineB):
    if lineA == lineB:
        return 10
    return 20


###------------------------------------------>><<-----------------------------------------------------
# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    stationTypeList = {1: "square", 2: "triangel", 3: "circle"}
    print(stationTypeList)

    world = GameWorld()
    world.worldInit(trainNm=1, carriageNm=1, stationNm=2)
    for i in range(1,500):
        world.updateOneTick()







# See PyCharm help at https://www.jetbrains.com/help/pycharm/
