# create_simple_map.py — 创建简单的双线地图
#
# 用法:
#   cd /Users/raspberry/developProject/MINI_METRO
#   python create_simple_map.py

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from world.map_data import MapData
from core.station import (
    CATEGORY_RESIDENTIAL, CATEGORY_COMMERCIAL, CATEGORY_OFFICE,
    CATEGORY_SCHOOL,
)


def create_simple_two_line_map():
    """创建简单的双线地图

    地图结构:
      线路1: 居民区1 → 商业区 → 办公区1
      线路2: 居民区2 → 商业区 → 办公区2

      商业区是换乘站，两条线在此交汇
    """
    map_data = MapData()

    # 添加站点
    # 线路1的站点
    map_data.add_station(1, 100, 200, CATEGORY_RESIDENTIAL, spawn_weight=1.0)
    map_data.add_station(2, 200, 200, CATEGORY_COMMERCIAL, spawn_weight=1.5)  # 换乘站
    map_data.add_station(3, 300, 200, CATEGORY_OFFICE, spawn_weight=1.0)

    # 线路2的站点
    map_data.add_station(4, 200, 100, CATEGORY_RESIDENTIAL, spawn_weight=1.0)
    # 站点2已存在（商业区换乘站）
    map_data.add_station(5, 200, 300, CATEGORY_SCHOOL, spawn_weight=0.8)

    # 添加线路
    # 线路1: 居民区1 → 商业区 → 办公区1
    map_data.add_line(1, [1, 2, 3], segment_ticks=[5, 5])

    # 线路2: 居民区2 → 商业区 → 学校
    map_data.add_line(2, [4, 2, 5], segment_ticks=[5, 5])

    # 设置资源
    map_data.set_resources(trains=4, carriages=8)

    return map_data


def main():
    """创建并保存地图"""
    print("\n" + "="*60)
    print("创建简单的双线地图")
    print("="*60)

    # 创建地图
    map_data = create_simple_two_line_map()

    # 验证
    is_valid, errors = map_data.validate()
    if not is_valid:
        print("\n✗ 地图验证失败:")
        for err in errors:
            print(f"  - {err}")
        return

    print("\n✓ 地图验证通过")

    # 打印摘要
    map_data.print_summary()

    # 保存
    output_dir = os.path.join(PROJECT_ROOT, "maps")
    os.makedirs(output_dir, exist_ok=True)

    output_file = os.path.join(output_dir, "simple_two_line.json")
    map_data.save(output_file)

    print(f"\n✓ 地图已保存到: {output_file}")

    # 打印详细结构
    print("\n" + "="*60)
    print("地图详细结构")
    print("="*60)
    print("\n线路1: 居民区1(1) → 商业区(2) → 办公区1(3)")
    print("线路2: 居民区2(4) → 商业区(2) → 学校(5)")
    print("\n说明:")
    print("  - 商业区(站点2)是换乘站，两条线在此交汇")
    print("  - 每段行驶时间: 5 tick")
    print("  - 资源: 4辆列车, 8个车厢")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
