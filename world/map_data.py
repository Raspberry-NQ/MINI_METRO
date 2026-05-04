# map_data.py — 地图数据结构
#
# 本文件定义了通用的地图数据结构，用于保存和加载训练/评估地图。


import json
from core.station import (
    CATEGORY_RESIDENTIAL, CATEGORY_COMMERCIAL, CATEGORY_OFFICE,
    CATEGORY_HOSPITAL, CATEGORY_SCENIC, CATEGORY_SCHOOL,
    CATEGORY_LABEL_CN,
)


class MapData:
    """地图数据类，封装站点、线路、资源等信息

    包含:
      - 站点列表: 每个站点的坐标、类别、乘客生成概率
      - 线路定义: 每条线路的站点序列、站间行驶tick
      - 资源配置: 列车和车厢数量
    """

    def __init__(self):
        """初始化空地图"""
        # 站点列表: list[dict]
        # 每个dict包含: id, x, y, category, spawn_weight
        self.stations = []

        # 线路列表: list[dict]
        # 每个dict包含: id, station_ids (list[int]), segment_ticks (list[int])
        self.lines = []

        # 资源配置: dict
        # 包含: trains (int), carriages (int)
        self.resources = {
            "trains": 0,
            "carriages": 0,
        }

    # ============================================================
    # 站点管理
    # ============================================================

    def add_station(self, station_id, x, y, category, spawn_weight=1.0):
        """添加站点

        参数:
            station_id: 站点ID
            x: x坐标
            y: y坐标
            category: 站点类别
            spawn_weight: 乘客生成权重，默认1.0
        """
        self.stations.append({
            "id": station_id,
            "x": x,
            "y": y,
            "category": category,
            "spawn_weight": spawn_weight,
        })

    def get_station_by_id(self, station_id):
        """根据ID获取站点信息

        参数:
            station_id: 站点ID

        返回:
            dict or None: 站点信息字典
        """
        for s in self.stations:
            if s["id"] == station_id:
                return s
        return None

    # ============================================================
    # 线路管理
    # ============================================================

    def add_line(self, line_id, station_ids, segment_ticks=None):
        """添加线路

        参数:
            line_id: 线路ID
            station_ids: 站点ID序列 list[int]
            segment_ticks: 站间行驶tick列表 list[int]，长度应为 len(station_ids)-1
                          如果为None，后续需要计算
        """
        if segment_ticks is None:
            segment_ticks = []

        self.lines.append({
            "id": line_id,
            "station_ids": station_ids,
            "segment_ticks": segment_ticks,
        })

    def get_line_by_id(self, line_id):
        """根据ID获取线路信息

        参数:
            line_id: 线路ID

        返回:
            dict or None: 线路信息字典
        """
        for line in self.lines:
            if line["id"] == line_id:
                return line
        return None

    # ============================================================
    # 资源管理
    # ============================================================

    def set_resources(self, trains, carriages):
        """设置资源数量

        参数:
            trains: 列车数量
            carriages: 车厢数量
        """
        self.resources["trains"] = trains
        self.resources["carriages"] = carriages

    # ============================================================
    # 序列化
    # ============================================================

    def to_dict(self):
        """转换为字典格式

        返回:
            dict: 地图数据的字典表示
        """
        return {
            "stations": self.stations,
            "lines": self.lines,
            "resources": self.resources,
        }

    def from_dict(self, data):
        """从字典加载地图数据

        参数:
            data: 地图数据字典
        """
        self.stations = data.get("stations", [])
        self.lines = data.get("lines", [])
        self.resources = data.get("resources", {"trains": 0, "carriages": 0})

    def save(self, filepath):
        """保存地图到JSON文件

        参数:
            filepath: 文件路径
        """
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    def load(self, filepath):
        """从JSON文件加载地图

        参数:
            filepath: 文件路径
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.from_dict(data)

    # ============================================================
    # 工具方法
    # ============================================================

    def get_summary(self):
        """获取地图摘要信息

        返回:
            str: 地图摘要字符串
        """
        # 统计各类别站点数
        category_count = {}
        for s in self.stations:
            cat = s["category"]
            category_count[cat] = category_count.get(cat, 0) + 1

        summary_lines = [
            f"站点总数: {len(self.stations)}",
            f"线路总数: {len(self.lines)}",
            f"资源: {self.resources['trains']}辆列车, {self.resources['carriages']}个车厢",
            "",
            "站点类别分布:",
        ]

        for cat, count in sorted(category_count.items()):
            label = CATEGORY_LABEL_CN.get(cat, cat)
            summary_lines.append(f"  {label}: {count}个")

        summary_lines.append("")
        summary_lines.append("线路详情:")
        for line in self.lines:
            line_id = line["id"]
            station_count = len(line["station_ids"])
            summary_lines.append(f"  线路{line_id}: {station_count}个站点")

        return "\n".join(summary_lines)

    def print_summary(self):
        """打印地图摘要信息"""
        print(f"\n{'='*60}")
        print("地图摘要")
        print(f"{'='*60}")
        print(self.get_summary())
        print(f"{'='*60}")

    # ============================================================
    # 验证
    # ============================================================

    def validate(self):
        """验证地图数据的有效性

        返回:
            tuple: (is_valid, error_messages)
                is_valid: bool, 是否有效
                error_messages: list[str], 错误信息列表
        """
        errors = []

        # 检查站点
        station_ids = set()
        for s in self.stations:
            if s["id"] in station_ids:
                errors.append(f"站点ID重复: {s['id']}")
            station_ids.add(s["id"])

            # 检查必要字段
            if "x" not in s or "y" not in s:
                errors.append(f"站点{s['id']}缺少坐标")
            if "category" not in s:
                errors.append(f"站点{s['id']}缺少类别")

        # 检查线路
        line_ids = set()
        for line in self.lines:
            if line["id"] in line_ids:
                errors.append(f"线路ID重复: {line['id']}")
            line_ids.add(line["id"])

            # 检查站点序列
            if len(line["station_ids"]) < 2:
                errors.append(f"线路{line['id']}站点数不足（至少需要2个）")

            # 检查站点是否存在
            for sid in line["station_ids"]:
                if sid not in station_ids:
                    errors.append(f"线路{line['id']}引用了不存在的站点{sid}")

            # 检查segment_ticks长度
            if line["segment_ticks"]:
                expected_len = len(line["station_ids"]) - 1
                actual_len = len(line["segment_ticks"])
                if actual_len != expected_len:
                    errors.append(
                        f"线路{line['id']}的segment_ticks长度不正确: "
                        f"期望{expected_len}, 实际{actual_len}"
                    )

        # 检查资源
        if self.resources["trains"] < 0:
            errors.append("列车数量不能为负")
        if self.resources["carriages"] < 0:
            errors.append("车厢数量不能为负")

        is_valid = len(errors) == 0
        return is_valid, errors
