# action_executor.py — 把动作编号翻译成对 AIWorld 的调用


class ActionExecutor:
    """把动作编号变成游戏操作

    动作编号:
      0         : 不操作
      1 ~ L     : 分配列车到线路 0 ~ L-1
      L+1 ~ 2L  : 给线索引 0~L-1 上的列车加车厢
    """

    def __init__(self, max_lines=7):
        self.max_lines = max_lines

    def execute(self, action_id, world, state_dict):
        """执行动作

        Args:
            action_id: 动作编号
            world: AIWorld 实例
            state_dict: 当前游戏状态

        Returns:
            bool: 是否成功执行
        """
        if action_id == 0:
            return True  # 不操作

        # 分配列车到线路
        if 1 <= action_id <= self.max_lines:
            line_idx = action_id - 1
            return self._employ_train(world, state_dict, line_idx)

        # 给线路上的列车加车厢
        if self.max_lines + 1 <= action_id <= self.max_lines * 2:
            line_idx = action_id - 1 - self.max_lines
            return self._add_carriage(world, state_dict, line_idx)

        return False

    def _employ_train(self, world, state_dict, line_idx):
        """从车库分配列车到指定线路"""
        line_info = self._find_line_by_idx(state_dict, line_idx)
        if line_info is None:
            return False

        line = world.findLineById(line_info["id"])
        if line is None:
            return False

        # 选该线路的第一个站点作为上车站
        if not line_info["station_ids"]:
            return False
        station = world.findStationById(line_info["station_ids"][0])
        if station is None:
            return False

        try:
            train = world.playerEmployTrain(line, station, direction=True)
            return train is not None
        except Exception:
            return False

    def _add_carriage(self, world, state_dict, line_idx):
        """给指定线路上的一辆列车加车厢"""
        line_info = self._find_line_by_idx(state_dict, line_idx)
        if line_info is None:
            return False

        # 找该线路上的一辆车
        line_id = line_info["id"]
        for train_info in state_dict["trains"]:
            if train_info["line_id"] == line_id:
                train_obj = world.findTrainById(train_info["id"])
                if train_obj is not None:
                    try:
                        result = world.playerConnectCarriage(train_obj)
                        return result is not None
                    except Exception:
                        return False
        return False

    def _find_line_by_idx(self, state_dict, line_idx):
        """按索引找线路信息 (线路按 ID 排序后取第 line_idx 个)"""
        lines = sorted(state_dict["lines"], key=lambda l: l["id"])
        if 0 <= line_idx < len(lines):
            return lines[line_idx]
        return None
