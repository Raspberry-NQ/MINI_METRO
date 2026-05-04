#!/usr/bin/env python
"""测试修复后的valid_mask"""

from world.ai_world import AIWorld
from world.game_config import GameConfig
from ai.src.action_space import ActionSpace
from ai.src.train_scheduler import rule_based_build_lines

cfg = GameConfig.for_ai_training()
world = AIWorld(cfg)
world.setup()
rule_based_build_lines(world)
world.lock_lines()

action_space = ActionSpace(max_lines=cfg.max_lines)
state_dict = world.getGameState()

print('线路信息:')
for line in state_dict['lines']:
    print(f'  线路{line["id"]}: {line["train_count"]}辆列车, max={line.get("max_trains", 999)}')

print(f'\n可用列车: {state_dict["available"]["trains"]}')
print(f'可用车厢: {state_dict["available"]["carriages"]}')

mask = action_space.get_valid_mask(state_dict)
print(f'\n有效动作掩码 (共{len(mask)}个动作):')
for i, valid in enumerate(mask):
    if i == 0:
        print(f'  动作0: 不操作 - {valid}')
    elif 1 <= i <= cfg.max_lines:
        print(f'  动作{i}: 分配列车到线路{i-1} - {valid}')
    else:
        print(f'  动作{i}: 给线路{i-1-cfg.max_lines}加车厢 - {valid}')
