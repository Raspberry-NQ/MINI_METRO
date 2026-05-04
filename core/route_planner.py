# route_planner.py — 路径规划模块
#
# 本文件实现了地铁网络的路径规划功能，使用Dijkstra算法寻找最优路径。

import heapq
from collections import defaultdict
from core.external_functions import countTrainRunningTime


class RoutePlanner:
    """路径规划器类，负责规划乘客的最优路径"""

    def __init__(self, metro_system, config=None):
        """初始化路径规划器

        参数:
            metro_system: 地铁系统对象
            config: 游戏配置对象，默认为None
        """
        self.metro_system = metro_system
        self.config = config
        self.transfer_penalty = config.passenger_transfer_penalty if config else 5  # 换乘惩罚时间
        self.route_cache = {}  # 路径缓存

    def invalidate_cache(self):
        """线路变更后清除路径缓存"""
        self.route_cache = {}

    def find_route(self, origin_station, destination_station, passenger_preference="fastest"):
        """寻找从起点到终点的最优路径

        参数:
            origin_station: 起始站点对象
            destination_station: 目的地站点对象
            passenger_preference: 路径偏好，可选值："fastest"(最快), "least_transfer"(最少换乘), "balanced"(平衡)

        返回:
            list: 路径步骤列表，每步包含station、line、direction、transfer信息；或None（无法到达）
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
        """构建地铁网络图

        返回:
            dict: 图结构字典，{station: [edge_dict, ...]}
        """
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
        # 换乘边：从当前站（当前线路）到同一站（新线路），只计算换乘惩罚
        for station in self.metro_system.stations:
            lines_at_station = self._get_lines_at_station(station)
            for i, line1 in enumerate(lines_at_station):
                for line2 in lines_at_station[i + 1:]:
                    # 换乘边：line1 -> line2（在同一站）
                    graph[station].append({
                        'station': station,  # 仍在同一站
                        'line': line2,       # 切换到line2
                        'direction': None,   # 方向待定（乘客需要选择）
                        'time': self.transfer_penalty,  # 只有换乘惩罚
                        'transfer': True,
                        'from_line': line1    # 记录从哪条线换乘
                    })
                    # 换乘边：line2 -> line1（在同一站）
                    graph[station].append({
                        'station': station,
                        'line': line1,
                        'direction': None,
                        'time': self.transfer_penalty,
                        'transfer': True,
                        'from_line': line2
                    })

        return graph

    def _get_lines_at_station(self, station):
        """获取经过指定站点的所有线路

        参数:
            station: 站点对象

        返回:
            list: 线路对象列表
        """
        lines = []
        for line in self.metro_system.metroLine:
            if station in line.stationList:
                lines.append(line)
        return lines

    def _calculate_travel_time(self, station1, station2):
        """计算两站之间的行驶时间

        参数:
            station1: 起始站点对象
            station2: 目标站点对象

        返回:
            int: 行驶时间（tick数）
        """
        return countTrainRunningTime(station1, station2, self.config)

    def _dijkstra_fastest(self, graph, start, end):
        """Dijkstra算法 - 寻找最快路径

        参数:
            graph: 图结构
            start: 起始站点
            end: 目标站点

        返回:
            list: 路径步骤列表
        """
        return self._dijkstra(graph, start, end, weight_func=lambda edge: edge['time'])

    def _dijkstra_least_transfer(self, graph, start, end):
        """Dijkstra算法 - 寻找最少换乘路径

        参数:
            graph: 图结构
            start: 起始站点
            end: 目标站点

        返回:
            list: 路径步骤列表
        """
        return self._dijkstra(graph, start, end, weight_func=lambda edge: 1000 if edge['transfer'] else 1)

    def _dijkstra_balanced(self, graph, start, end):
        """Dijkstra算法 - 平衡时间和换乘次数

        参数:
            graph: 图结构
            start: 起始站点
            end: 目标站点

        返回:
            list: 路径步骤列表
        """
        return self._dijkstra(graph, start, end, weight_func=lambda edge: edge['time'] + (50 if edge['transfer'] else 0))

    def _dijkstra(self, graph, start, end, weight_func):
        """通用Dijkstra算法实现

        参数:
            graph: 图结构
            start: 起始站点
            end: 目标站点
            weight_func: 权重计算函数

        返回:
            list: 路径步骤列表，或None（无法到达）
        """
        distances = {start: 0}
        previous = {}
        pq = [(0, 0, start)]  # (dist, seq, station) — seq 打破平局
        _seq = 0

        while pq:
            current_dist, _, current = heapq.heappop(pq)

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
                    _seq += 1
                    heapq.heappush(pq, (new_dist, _seq, neighbor))

        # 重构路径
        if end not in previous:
            return None

        path = []
        current = end
        while current != start:
            prev_station, edge = previous[current]

            # 如果是换乘边，需要插入换乘步
            if edge['transfer']:
                # 换乘步：在同一站，从 from_line 切换到 edge['line']
                path.insert(0, {
                    'station': current,
                    'line': edge['line'],
                    'direction': None,  # 方向待乘客选择
                    'transfer': True
                })
                # 当前站（换乘前）的步骤
                path.insert(0, {
                    'station': current,
                    'line': edge['from_line'],
                    'direction': None,  # 方向信息在换乘前不重要
                    'transfer': False
                })
            else:
                # 普通步骤
                path.insert(0, {
                    'station': current,
                    'line': edge['line'],
                    'direction': edge['direction'],
                    'transfer': False
                })

            current = prev_station

        # 添加起点站
        path.insert(0, {
            'station': start,
            'line': None,
            'direction': None,
            'transfer': False
        })

        # 后处理：为换乘步填充方向信息
        # 换乘后的方向应该与后续步骤的方向一致
        for i in range(len(path) - 1):
            if path[i]['transfer'] and path[i + 1]['line'] is path[i]['line']:
                path[i]['direction'] = path[i + 1]['direction']

        return path
