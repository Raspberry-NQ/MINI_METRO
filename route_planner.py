# route_planner.py — 路线规划器

class RoutePlanner:
    def __init__(self, metro_system):
        self.metro_system = metro_system

    def find_route(self, origin_station, destination_station, preference="fastest"):
        """寻找从 origin 到 destination 的路线。
        返回路线步骤列表: [{'line': MetroLine, 'direction': bool, 'transfer': bool, 'station': station}]
        如果不可达返回 None。
        """
        if not hasattr(self.metro_system, 'metroLine'):
            return None

        # 直达
        for line in self.metro_system.metroLine:
            if origin_station in line.stationList and destination_station in line.stationList:
                origin_idx = line.stationList.index(origin_station)
                dest_idx = line.stationList.index(destination_station)
                direction = dest_idx > origin_idx
                return [{'line': line, 'direction': direction, 'transfer': False, 'station': destination_station}]

        # 一次换乘: 找经过起点和换乘站的线路A, 和经过换乘站和终点的线路B
        lines_with_origin = [l for l in self.metro_system.metroLine if origin_station in l.stationList]
        lines_with_dest = [l for l in self.metro_system.metroLine if destination_station in l.stationList]
        for line_a in lines_with_origin:
            for line_b in lines_with_dest:
                if line_a == line_b:
                    continue
                # 找换乘站
                transfers = [s for s in line_a.stationList if s in line_b.stationList]
                if transfers:
                    transfer_station = transfers[0]
                    oidx = line_a.stationList.index(origin_station)
                    tidx_a = line_a.stationList.index(transfer_station)
                    tidx_b = line_b.stationList.index(transfer_station)
                    didx = line_b.stationList.index(destination_station)
                    return [
                        {'line': line_a, 'direction': tidx_a > oidx, 'transfer': False, 'station': transfer_station},
                        {'line': line_b, 'direction': didx > tidx_b, 'transfer': True, 'station': destination_station},
                    ]

        return None
