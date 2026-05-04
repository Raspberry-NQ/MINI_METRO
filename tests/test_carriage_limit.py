#!/usr/bin/env python
"""测试车厢限制和valid_mask修复"""

from world.ai_world import AIWorld
from world.game_config import GameConfig
from ai.src.action_space import ActionSpace
from ai.src.action_executor import ActionExecutor
from ai.src.train_scheduler import rule_based_build_lines

cfg = GameConfig.for_ai_training()
world = AIWorld(cfg)
world.setup()
rule_based_build_lines(world)
world.lock_lines()

action_space = ActionSpace(max_lines=cfg.max_lines)
executor = ActionExecutor(max_lines=cfg.max_lines)

print("="*60)
print("测试车厢限制")
print("="*60)

# 分配列车到线路1
state = world.getGameState()
print("\n1. 初始状态")
print(f"   可用列车: {state['available']['trains']}")
print(f"   可用车厢: {state['available']['carriages']}")

# 分配列车
executor.execute(1, world, state)
state = world.getGameState()
print("\n2. 分配列车到线路1后")
print(f"   可用列车: {state['available']['trains']}")
print(f"   可用车厢: {state['available']['carriages']}")
train = state['trains'][0]
print(f"   列车{train['id']}: {train.get('carriage_count', '?')}节车厢, 容量{train.get('capacity', '?')}")

mask = action_space.get_valid_mask(state)
print(f"   动作5（加车厢）有效: {mask[5]}")

# 连续加车厢直到达到上限
for i in range(5):
    if mask[5]:
        executor.execute(5, world, state)
        state = world.getGameState()
        train = state['trains'][0]
        print(f"\n3.{i+1}. 加第{train.get('carriage_count', '?')}节车厢后")
        print(f"   可用车厢: {state['available']['carriages']}")
        print(f"   列车{train['id']}: {train.get('carriage_count', '?')}节车厢, 容量{train.get('capacity', '?')}")

        mask = action_space.get_valid_mask(state)
        print(f"   动作5（加车厢）有效: {mask[5]}")
    else:
        print(f"\n   无法继续加车厢（已达上限或无资源）")
        break

print("\n" + "="*60)
print("测试完成")
print("="*60)
