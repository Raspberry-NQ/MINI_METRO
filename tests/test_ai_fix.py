#!/usr/bin/env python
"""快速测试修复后的AI是否能正常训练"""

import os
import sys

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from world.ai_world import AIWorld
from world.game_config import GameConfig
from ai.src.scheduler_encoder import SchedulerEncoder
from ai.src.action_space import ActionSpace
from ai.src.dqn_agent import DQNAgent
from ai.src.action_executor import ActionExecutor
from ai.src.reward import RewardCalculator
from ai.src.train_scheduler import rule_based_build_lines

# 初始化
cfg = GameConfig.for_ai_training()
encoder = SchedulerEncoder(cfg)
action_space = ActionSpace(max_lines=cfg.max_lines)
state_dim = 11 + cfg.max_lines * 7 + cfg.max_trains * 6 + 6
agent = DQNAgent(state_dim=state_dim, n_actions=action_space.n_actions)
executor = ActionExecutor(max_lines=cfg.max_lines)
reward_calc = RewardCalculator(overcrowd_limit=cfg.overcrowd_limit)

# 创建世界
world = AIWorld(cfg)
world.setup()
rule_based_build_lines(world)
world.lock_lines()

# 测试valid_mask
state_dict = world.getGameState()
mask = action_space.get_valid_mask(state_dict)

print("="*60)
print("Valid Mask测试")
print("="*60)
print(f"可用列车: {state_dict['available']['trains']}")
print(f"可用车厢: {state_dict['available']['carriages']}")
print(f"\n有效动作:")
valid_count = 0
for i, valid in enumerate(mask):
    if valid:
        valid_count += 1
        if i == 0:
            print(f"  动作0: 不操作")
        elif 1 <= i <= cfg.max_lines:
            line_idx = i - 1
            lines_sorted = sorted(state_dict["lines"], key=lambda l: l["id"])
            if line_idx < len(lines_sorted):
                line_id = lines_sorted[line_idx]["id"]
                print(f"  动作{i}: 分配列车到线路{line_id} (索引{line_idx})")
        else:
            line_idx = i - 1 - cfg.max_lines
            lines_sorted = sorted(state_dict["lines"], key=lambda l: l["id"])
            if line_idx < len(lines_sorted):
                line_id = lines_sorted[line_idx]["id"]
                print(f"  动作{i}: 给线路{line_id}加车厢 (索引{line_idx})")

print(f"\n总共有 {valid_count} 个有效动作（包括不操作）")

# 测试执行动作
print("\n" + "="*60)
print("动作执行测试")
print("="*60)

# 尝试分配列车到第一条线路
if valid_count > 1:  # 有除了"不操作"之外的动作
    for i in range(1, len(mask)):
        if mask[i]:
            print(f"\n执行动作{i}...")
            result = executor.execute(i, world, state_dict)
            print(f"  结果: {'成功' if result else '失败'}")

            # 检查状态变化
            new_state = world.getGameState()
            print(f"  可用列车: {state_dict['available']['trains']} → {new_state['available']['trains']}")
            print(f"  线路列车数:")
            for line in new_state['lines']:
                print(f"    线路{line['id']}: {line['train_count']}辆")
            break

print("\n" + "="*60)
print("测试完成!")
print("="*60)
