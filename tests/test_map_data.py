# test_map_data.py — 测试地图数据类
#
# 用法:
#   cd /Users/raspberry/developProject/MINI_METRO
#   python test_map_data.py

import os
import sys

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from world.map_data import MapData
from core.station import (
    CATEGORY_RESIDENTIAL, CATEGORY_COMMERCIAL, CATEGORY_OFFICE,
    CATEGORY_HOSPITAL, CATEGORY_SCENIC, CATEGORY_SCHOOL,
)


def test_basic_operations():
    """测试基本操作"""
    print("\n" + "="*60)
    print("测试1: 基本操作")
    print("="*60)

    # 创建地图
    map_data = MapData()

    # 添加站点
    map_data.add_station(1, 100, 200, CATEGORY_RESIDENTIAL, spawn_weight=1.0)
    map_data.add_station(2, 150, 250, CATEGORY_COMMERCIAL, spawn_weight=1.2)
    map_data.add_station(3, 200, 180, CATEGORY_OFFICE, spawn_weight=0.8)
    map_data.add_station(4, 120, 300, CATEGORY_RESIDENTIAL, spawn_weight=1.0)

    # 添加线路
    map_data.add_line(1, [1, 2, 3], segment_ticks=[5, 6])
    map_data.add_line(2, [1, 4], segment_ticks=[4])

    # 设置资源
    map_data.set_resources(trains=4, carriages=8)

    # 打印摘要
    map_data.print_summary()

    # 验证
    is_valid, errors = map_data.validate()
    if is_valid:
        print("\n✓ 地图数据验证通过")
    else:
        print("\n✗ 地图数据验证失败:")
        for err in errors:
            print(f"  - {err}")


def test_save_load():
    """测试保存和加载"""
    print("\n" + "="*60)
    print("测试2: 保存和加载")
    print("="*60)

    # 创建地图
    map_data = MapData()
    map_data.add_station(1, 0, 0, CATEGORY_RESIDENTIAL)
    map_data.add_station(2, 100, 0, CATEGORY_COMMERCIAL)
    map_data.add_station(3, 200, 0, CATEGORY_OFFICE)
    map_data.add_line(1, [1, 2, 3], segment_ticks=[3, 3])
    map_data.set_resources(trains=2, carriages=4)

    # 保存
    test_file = "test_map.json"
    map_data.save(test_file)
    print(f"\n✓ 地图已保存到 {test_file}")

    # 加载
    loaded_map = MapData()
    loaded_map.load(test_file)
    print(f"✓ 地图已从 {test_file} 加载")

    # 验证加载的数据
    assert len(loaded_map.stations) == 3, "站点数不匹配"
    assert len(loaded_map.lines) == 1, "线路数不匹配"
    assert loaded_map.resources["trains"] == 2, "列车数不匹配"
    assert loaded_map.resources["carriages"] == 4, "车厢数不匹配"

    print("✓ 数据一致性验证通过")

    # 打印加载的地图
    loaded_map.print_summary()

    # 清理测试文件
    if os.path.exists(test_file):
        os.remove(test_file)
        print(f"\n✓ 已清理测试文件 {test_file}")


def test_validation():
    """测试验证功能"""
    print("\n" + "="*60)
    print("测试3: 验证功能")
    print("="*60)

    # 测试1: 重复的站点ID
    print("\n测试3.1: 重复的站点ID")
    map_data = MapData()
    map_data.add_station(1, 0, 0, CATEGORY_RESIDENTIAL)
    map_data.add_station(1, 100, 100, CATEGORY_COMMERCIAL)  # 重复ID
    is_valid, errors = map_data.validate()
    assert not is_valid, "应该检测到重复ID"
    print(f"✓ 正确检测到错误: {errors[0]}")

    # 测试2: 线路引用不存在的站点
    print("\n测试3.2: 线路引用不存在的站点")
    map_data = MapData()
    map_data.add_station(1, 0, 0, CATEGORY_RESIDENTIAL)
    map_data.add_line(1, [1, 999], segment_ticks=[5])  # 999不存在
    is_valid, errors = map_data.validate()
    assert not is_valid, "应该检测到不存在的站点"
    print(f"✓ 正确检测到错误: {errors[0]}")

    # 测试3: segment_ticks长度不正确
    print("\n测试3.3: segment_ticks长度不正确")
    map_data = MapData()
    map_data.add_station(1, 0, 0, CATEGORY_RESIDENTIAL)
    map_data.add_station(2, 100, 0, CATEGORY_COMMERCIAL)
    map_data.add_station(3, 200, 0, CATEGORY_OFFICE)
    map_data.add_line(1, [1, 2, 3], segment_ticks=[5])  # 应该是2个元素
    is_valid, errors = map_data.validate()
    assert not is_valid, "应该检测到segment_ticks长度错误"
    print(f"✓ 正确检测到错误: {errors[0]}")

    # 测试4: 线路站点数不足
    print("\n测试3.4: 线路站点数不足")
    map_data = MapData()
    map_data.add_station(1, 0, 0, CATEGORY_RESIDENTIAL)
    map_data.add_line(1, [1])  # 只有1个站点
    is_valid, errors = map_data.validate()
    assert not is_valid, "应该检测到站点数不足"
    print(f"✓ 正确检测到错误: {errors[0]}")

    print("\n✓ 所有验证测试通过")


def test_query_operations():
    """测试查询操作"""
    print("\n" + "="*60)
    print("测试4: 查询操作")
    print("="*60)

    map_data = MapData()
    map_data.add_station(1, 0, 0, CATEGORY_RESIDENTIAL)
    map_data.add_station(2, 100, 0, CATEGORY_COMMERCIAL)
    map_data.add_line(1, [1, 2], segment_ticks=[5])

    # 测试查询站点
    station = map_data.get_station_by_id(1)
    assert station is not None, "应该找到站点1"
    assert station["category"] == CATEGORY_RESIDENTIAL, "站点类别不匹配"
    print("✓ 查询站点成功")

    # 测试查询不存在的站点
    station = map_data.get_station_by_id(999)
    assert station is None, "不应该找到站点999"
    print("✓ 查询不存在的站点返回None")

    # 测试查询线路
    line = map_data.get_line_by_id(1)
    assert line is not None, "应该找到线路1"
    assert line["station_ids"] == [1, 2], "线路站点序列不匹配"
    print("✓ 查询线路成功")

    print("\n✓ 所有查询测试通过")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("MapData 类测试")
    print("="*60)

    test_basic_operations()
    test_save_load()
    test_validation()
    test_query_operations()

    print("\n" + "="*60)
    print("所有测试通过！")
    print("="*60 + "\n")
