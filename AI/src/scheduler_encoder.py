# scheduler_encoder.py — 把 getGameState() 的输出编码成 PyTorch 张量

import torch
import numpy as np
from game_config import GameConfig


class SchedulerEncoder:
    """把 getGameState() 返回的字典编码成固定维度的张量

    编码方案:
      全局特征 (11 维)
        + 每条线路特征 (7 条线 × 7 维 = 49 维)
        + 每辆列车特征 (20 辆车 × 6 维 = 120 维)
        + 站点拥堵概要 (6 维: 每类别的最大候车数)
      = 186 维
    """

    PERIODS = ["night", "morning_rush", "morning", "midday",
               "evening_rush", "evening", "late_night"]
    CATEGORIES = ["residential", "commercial", "office", "hospital", "scenic", "school"]

    def __init__(self, config):
        self.cfg = config
        self.max_lines = config.max_lines           # 7
        self.max_trains = config.max_trains          # 20
        self.max_carriages = config.max_carriages    # 40
        self.max_trains_per_line = getattr(config, 'max_trains_per_line', 2)
        self.overcrowd_limit = config.overcrowd_limit

    def encode(self, state):
        """输入: getGameState() 返回的字典, 输出: 一维张量 (186,)"""
        features = []

        # --- 1. 全局特征 (11 维) ---
        tick_ratio = state["tick_in_day"] / max(state["time_of_day"]["day_length"], 1)
        features.append(tick_ratio)

        # 时段 one-hot (7 维)
        current_period = state["time_of_day"]["period"]
        period_onehot = [1.0 if p == current_period else 0.0 for p in self.PERIODS]
        features.extend(period_onehot)

        # 可用资源占比 (3 维)
        features.append(state["available"]["trains"] / max(self.max_trains, 1))
        features.append(state["available"]["carriages"] / max(self.max_carriages, 1))
        features.append(state["available"]["lines_remaining"] / max(self.max_lines, 1))

        # --- 2. 每条线路的特征 (7 条线 × 7 维 = 49 维) ---
        line_features = {}
        for line_info in state["lines"]:
            lf = [
                len(line_info["station_ids"]) / 20.0,
                line_info["train_count"] / max(self.max_trains_per_line, 1),
                0.0,  # 该线路上总候客人数 (从站点汇总)
                0.0,  # 该线路上列车平均载客率
                1.0,  # 该线存在
                0.0,  # 该线路上列车是否都在运行
                0.0,  # 该线路是否还有车位可加车
            ]
            line_features[line_info["id"]] = lf

        # 统计每条线路的候客人数
        station_line_waiting = {}
        for station in state["stations"]:
            for lid in station["connecting_lines"]:
                station_line_waiting.setdefault(lid, 0)
                station_line_waiting[lid] += station["passenger_count"]

        for line_info in state["lines"]:
            lid = line_info["id"]
            lf = line_features[lid]
            lf[2] = station_line_waiting.get(lid, 0) / max(self.overcrowd_limit, 1)

            # 统计该线列车载客率
            line_trains = [t for t in state["trains"] if t["line_id"] == lid]
            if line_trains:
                loads = [t["passenger_count"] / max(t["capacity"], 1) for t in line_trains]
                lf[3] = float(np.mean(loads))
                all_running = all(t["status"] == 4 for t in line_trains)
                lf[5] = 1.0 if all_running else 0.0

            max_t = line_info.get("max_trains", self.max_trains_per_line)
            has_slot = line_info["train_count"] < max_t
            lf[6] = 1.0 if has_slot else 0.0

        # 按线路 ID 排序, 不存在的线路填零
        for lid in range(self.max_lines):
            if lid in line_features:
                features.extend(line_features[lid])
            else:
                features.extend([0.0] * 7)

        # --- 3. 每辆列车特征 (20 辆车 × 6 维 = 120 维) ---
        train_feature_list = []
        for train in state["trains"]:
            tf = [
                train["line_id"] / max(self.max_lines, 1) if train["line_id"] is not None else -1.0,
                train["status"] / 6.0,
                train["direction"] if train["direction"] is not None else 0.0,
                train["passenger_count"] / max(train["capacity"], 1),
                train["carriage_count"] / 4.0,
                1.0 if train["status"] == 3 else 0.0,  # 是否空闲(可调)
            ]
            train_feature_list.append(tf)

        # 补零到 max_trains
        while len(train_feature_list) < self.max_trains:
            train_feature_list.append([0.0] * 6)
        # 只取前 max_trains
        for tf in train_feature_list[:self.max_trains]:
            features.extend(tf)

        # --- 4. 站点拥堵概要 (6 维) ---
        for cat in self.CATEGORIES:
            cat_stations = [s for s in state["stations"] if s["category"] == cat]
            max_wait = max((s["passenger_count"] for s in cat_stations), default=0)
            features.append(max_wait / max(self.overcrowd_limit, 1))

        return torch.tensor(features, dtype=torch.float32)
