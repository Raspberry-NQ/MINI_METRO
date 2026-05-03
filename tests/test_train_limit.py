#!/usr/bin/env python
# test_train_limit.py — 测试线路列车数量限制

import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from world.game_config import GameConfig
from world.run import MetroWorld
from core.station import CATEGORY_RESIDENTIAL

# 测试配置
cfg = GameConfig.for_ai_training()
print(f"配置: max_trains_per_line = {cfg.max_trains_per_line}")

# 创建世界
world = MetroWorld(cfg)
world.setup()

# 创建线路
stations = [s for s in world.stations if s.category == CATEGORY_RESIDENTIAL][:3]
if len(stations) < 2:
    print("站点不足，无法测试")
    sys.exit(1)

line = world.playerNewLine(stations)
print(f"线路 {line.number} 创建成功, max_trains = {line.max_trains}")

# 尝试添加多辆列车（测试是否有实际限制）
print("\n尝试添加 5 辆列车:")
for i in range(5):
    try:
        train = world.playerEmployTrain(line, stations[0], True)
        if train:
            print(f"  ✓ 成功添加列车 {i+1}, 当前线路列车数: {line.trainNm}")
    except Exception as e:
        print(f"  ✗ 添加列车 {i+1} 失败: {e}")

print(f"\n最终线路列车数: {line.trainNm} / {line.max_trains}")
print(f"测试结果: {'✓ 无限制' if line.trainNm == 5 else '✗ 有限制'}")