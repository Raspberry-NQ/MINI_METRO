# route_planner.py

import heapq
from collections import defaultdict
from external_functions import countTrainRunningTime


class RoutePlanner:
    def __init__(self, metro_system):
        self.metro_system = metro_system
        self.transfer_penalty = 5  # 换乘惩罚时间
        self.route_cache = {}  # 路径缓存

    def invalidate_cache(self):
        """线路变更后清除路径缓存"""
        self.route_cache = {}

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
