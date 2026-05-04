# action_space.py — 调度器动作空间定义

from world.game_config import GameConfig


class ActionSpace:
    """
    简化动作空间:
      0           : 不操作
      1 ~ L       : 分配列车到线路 0 ~ L-1  (playerEmployTrain)
      L+1 ~ L+L   : 给线索引 0~L-1 上的列车加车厢 (playerConnectCarriage)

    总共 1 + L + L = 1 + 2*L 个动作 (默认 L=7 → 15 个动作)

    调车动作 (playerTrainShunt) 暂时不包含在动作空间中,
    由规则触发 (当某线压力过小时自动调出)。
    后续可以扩展为完整动作空间。
    """

    def __init__(self, max_lines=7):
        self.max_lines = max_lines
        self.n_actions = 1 + max_lines * 2

    def get_action_meaning(self, action_id):
        """返回动作的可读描述"""
        if action_id == 0:
            return "noop"
        elif 1 <= action_id <= self.max_lines:
            return f"employ_train_to_line_{action_id - 1}"
        else:
            line_idx = action_id - 1 - self.max_lines
            return f"add_carriage_to_line_{line_idx}"

    def get_valid_mask(self, state_dict):
        """返回 boolean 数组, 标记哪些动作当前合法

        条件:
          - 分配列车: 有空闲列车 + 目标线存在 + 目标线未满
          - 加车厢: 有空闲车厢 + 目标线上有列车 + 列车未达最大车厢数
        """
        mask = [True]  # 不操作始终合法

        available_trains = state_dict["available"]["trains"]
        available_carriages = state_dict["available"]["carriages"]

        # 收集线路信息（按索引顺序）
        lines_sorted = sorted(state_dict["lines"], key=lambda l: l["id"])
        line_train_count = []
        line_max_trains = []
        line_has_train = []
        line_can_add_carriage = []

        # 默认最大车厢数
        max_carriages_per_train = 4  # 与 game_config 保持一致

        for line_info in lines_sorted:
            line_id = line_info["id"]
            line_train_count.append(line_info["train_count"])
            line_max_trains.append(line_info.get("max_trains", 999))
            line_has_train.append(line_info["train_count"] > 0)

            # 检查线路上是否有列车还能加车厢
            can_add = False
            if available_carriages > 0:
                for train_info in state_dict.get("trains", []):
                    if train_info["line_id"] == line_id:
                        carriage_count = train_info.get("carriage_count", 1)
                        if carriage_count < max_carriages_per_train:
                            can_add = True
                            break
            line_can_add_carriage.append(can_add)

        # 分配列车到线路
        for line_idx in range(self.max_lines):
            if line_idx < len(lines_sorted):
                can_employ = (available_trains > 0 and
                             line_train_count[line_idx] < line_max_trains[line_idx])
            else:
                can_employ = False
            mask.append(can_employ)

        # 给线路上的列车加车厢
        for line_idx in range(self.max_lines):
            if line_idx < len(lines_sorted):
                can_add = (available_carriages > 0 and
                          line_can_add_carriage[line_idx])
            else:
                can_add = False
            mask.append(can_add)

        # 补齐到 n_actions (理论上不需要, 但防御性编程)
        while len(mask) < self.n_actions:
            mask.append(False)

        return mask
