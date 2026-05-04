# test_map_training.py — 测试基于地图的训练和评估
#
# 用法:
#   cd /Users/raspberry/developProject/MINI_METRO
#   python test_map_training.py

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from world.map_data import MapData
from world.ai_world import AIWorld
from world.game_config import GameConfig
from core.station import (
    CATEGORY_RESIDENTIAL, CATEGORY_COMMERCIAL, CATEGORY_OFFICE,
    CATEGORY_SCHOOL,
)


def test_load_map_to_world():
    """测试从MapData加载到AIWorld"""
    print("\n" + "="*60)
    print("测试: 从MapData加载到AIWorld")
    print("="*60)

    # 加载地图
    map_path = os.path.join(PROJECT_ROOT, "maps", "simple_two_line.json")
    if not os.path.exists(map_path):
        print(f"\n✗ 地图文件不存在: {map_path}")
        print("请先运行: python create_simple_map.py")
        return False

    map_data = MapData()
    map_data.load(map_path)
    print(f"\n✓ 加载地图: {map_path}")

    # 创建AIWorld并加载地图
    cfg = GameConfig.for_ai_training()
    world = AIWorld(cfg)

    # 抑制输出
    import io
    import contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        world.setup_from_map(map_data)

    # 验证
    print(f"\n✓ AIWorld初始化成功")
    print(f"  站点数: {len(world.stations)}")
    print(f"  线路数: {len(world.metroLine)}")
    print(f"  列车数: {len(world.ti.trainAbleList)} (空闲)")
    print(f"  车厢数: {len(world.ti.carriageAbleList)} (空闲)")

    # 检查线路是否锁定
    if world._lines_locked:
        print(f"  线路状态: 已锁定 ✓")
    else:
        print(f"  线路状态: 未锁定 ✗")
        return False

    # 检查站点
    expected_stations = 5
    if len(world.stations) == expected_stations:
        print(f"\n✓ 站点数正确: {expected_stations}")
    else:
        print(f"\n✗ 站点数不正确: 期望{expected_stations}, 实际{len(world.stations)}")
        return False

    # 检查线路
    expected_lines = 2
    if len(world.metroLine) == expected_lines:
        print(f"✓ 线路数正确: {expected_lines}")
    else:
        print(f"✗ 线路数不正确: 期望{expected_lines}, 实际{len(world.metroLine)}")
        return False

    # 检查资源
    expected_trains = 4
    expected_carriages = 8
    if len(world.ti.trainAbleList) == expected_trains:
        print(f"✓ 列车数正确: {expected_trains}")
    else:
        print(f"✗ 列车数不正确: 期望{expected_trains}, 实际{len(world.ti.trainAbleList)}")
        return False

    if len(world.ti.carriageAbleList) == expected_carriages:
        print(f"✓ 车厢数正确: {expected_carriages}")
    else:
        print(f"✗ 车厢数不正确: 期望{expected_carriages}, 实际{len(world.ti.carriageAbleList)}")
        return False

    print("\n✓ 所有检查通过")
    return True


def test_training_with_map():
    """测试使用地图训练（简短测试）"""
    print("\n" + "="*60)
    print("测试: 使用地图训练 (2个episode)")
    print("="*60)

    from ai.src.train_scheduler import train_scheduler

    map_path = os.path.join(PROJECT_ROOT, "maps", "simple_two_line.json")
    if not os.path.exists(map_path):
        print(f"\n✗ 地图文件不存在: {map_path}")
        print("请先运行: python create_simple_map.py")
        return False

    # 训练2个episode作为测试
    try:
        agent = train_scheduler(num_episodes=2, map_paths=[map_path])
        print("\n✓ 训练测试成功")
        return True
    except Exception as e:
        print(f"\n✗ 训练测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_evaluate_with_map():
    """测试使用地图评估（简短测试）"""
    print("\n" + "="*60)
    print("测试: 使用地图评估 (2个episode)")
    print("="*60)

    from ai.src.train_scheduler import evaluate_scheduler

    map_path = os.path.join(PROJECT_ROOT, "maps", "simple_two_line.json")
    if not os.path.exists(map_path):
        print(f"\n✗ 地图文件不存在: {map_path}")
        print("请先运行: python create_simple_map.py")
        return False

    # 评估2个episode作为测试（不加载模型）
    try:
        results = evaluate_scheduler(
            agent_path=None,
            num_episodes=2,
            max_decisions=10,
            map_path=map_path
        )
        print(f"\n✓ 评估测试成功，返回{len(results)}个结果")
        return True
    except Exception as e:
        print(f"\n✗ 评估测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("基于地图的训练和评估测试")
    print("="*60)

    # 测试1: 加载地图到AIWorld
    if not test_load_map_to_world():
        print("\n✗ 测试失败: 加载地图到AIWorld")
        return

    # 测试2: 使用地图训练
    if not test_training_with_map():
        print("\n✗ 测试失败: 使用地图训练")
        return

    # 测试3: 使用地图评估
    if not test_evaluate_with_map():
        print("\n✗ 测试失败: 使用地图评估")
        return

    print("\n" + "="*60)
    print("所有测试通过！")
    print("="*60)

    # 打印使用示例
    print("\n" + "="*60)
    print("使用示例")
    print("="*60)
    print("\n训练（使用地图）:")
    print("  python -m ai.src.train_scheduler --episodes 100 --maps maps/simple_two_line.json")
    print("\n训练（使用多个地图）:")
    print("  python -m ai.src.train_scheduler --episodes 100 --maps map1.json map2.json map3.json")
    print("\n评估（使用地图）:")
    print("  python -m ai.src.train_scheduler --eval --model ai/checkpoints/best_scheduler.pt --maps maps/simple_two_line.json --episodes 10")
    print("\n训练（随机生成地图）:")
    print("  python -m ai.src.train_scheduler --episodes 100")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
