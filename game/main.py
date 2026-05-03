# main.py — 游戏入口
#
# 本文件是游戏的启动入口，创建并初始化游戏世界。

import os
import sys

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from world.run import MetroWorld
from world.game_config import GameConfig

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Mini Metro")
    parser.add_argument("--visual", action="store_true", help="启用 pygame 可视化模式")
    parser.add_argument("--max-ticks", type=int, default=500, help="最大 tick 数 (默认 500)")
    args = parser.parse_args()

    # 使用 GameConfig 创建世界
    config = GameConfig()
    world = MetroWorld(config)

    if args.visual:
        from game.visualizer import Visualizer
        viz = Visualizer(world)
        viz.run(max_ticks=args.max_ticks)
    else:
        world.run(max_ticks=args.max_ticks)
