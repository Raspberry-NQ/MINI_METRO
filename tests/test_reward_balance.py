#!/usr/bin/env python
"""测试新的奖励函数对线路平衡的激励效果"""

from world.ai_world import AIWorld
from world.game_config import GameConfig
from ai.src.reward import RewardCalculator
from ai.src.action_executor import ActionExecutor
from ai.src.train_scheduler import rule_based_build_lines

cfg = GameConfig.for_ai_training()
world = AIWorld(cfg)
world.setup()
rule_based_build_lines(world)
world.lock_lines()

reward_calc = RewardCalculator(overcrowd_limit=cfg.overcrowd_limit)
executor = ActionExecutor(max_lines=cfg.max_lines)

print("="*60)
print("奖励函数测试：线路平衡激励")
print("="*60)

# 初始状态
state0 = world.getGameState()
reward0 = reward_calc.compute(state0)
print(f"\n初始状态:")
print(f"  奖励: {reward0:.2f}")
print(f"  线路列车分布: {[l['train_count'] for l in state0['lines']]}")

# 场景1: 只在一条线路放置列车
print("\n" + "-"*60)
print("场景1: 只在线路1放置列车")
print("-"*60)

executor.execute(1, world, state0)  # 分配列车到线路1
state1 = world.getGameState()
reward1 = reward_calc.compute(state1)

print(f"  奖励: {reward1:.2f}")
print(f"  线路列车分布: {[l['train_count'] for l in state1['lines']]}")
print(f"  线路覆盖率: {sum(1 for l in state1['lines'] if l['train_count'] > 0)}/{len(state1['lines'])}")

# 场景2: 在两条线路放置列车
print("\n" + "-"*60)
print("场景2: 在线路1和线路2放置列车")
print("-"*60)

executor.execute(2, world, state1)  # 分配列车到线路2
state2 = world.getGameState()
reward2 = reward_calc.compute(state2)

print(f"  奖励: {reward2:.2f}")
print(f"  线路列车分布: {[l['train_count'] for l in state2['lines']]}")
print(f"  线路覆盖率: {sum(1 for l in state2['lines'] if l['train_count'] > 0)}/{len(state2['lines'])}")
print(f"  向空线路分配奖励: {reward2 - reward1:.2f}")

# 场景3: 在四条线路都放置列车（完全平衡）
print("\n" + "-"*60)
print("场景3: 在所有4条线路放置列车（完全平衡）")
print("-"*60)

executor.execute(3, world, state2)  # 分配列车到线路3
state3 = world.getGameState()
reward3 = reward_calc.compute(state3)

executor.execute(4, world, state3)  # 分配列车到线路4
state4 = world.getGameState()
reward4 = reward_calc.compute(state4)

print(f"  奖励: {reward4:.2f}")
print(f"  线路列车分布: {[l['train_count'] for l in state4['lines']]}")
print(f"  线路覆盖率: {sum(1 for l in state4['lines'] if l['train_count'] > 0)}/{len(state4['lines'])}")
print(f"  完全覆盖奖励: {reward4 - reward2:.2f}")

# 场景4: 不平衡分布（线路1有4辆，其他线路0辆）
print("\n" + "-"*60)
print("场景4: 不平衡分布（线路1有4辆，其他线路0辆）")
print("-"*60)

# 重置世界
world2 = AIWorld(cfg)
world2.setup()
rule_based_build_lines(world2)
world2.lock_lines()
reward_calc2 = RewardCalculator(overcrowd_limit=cfg.overcrowd_limit)
executor2 = ActionExecutor(max_lines=cfg.max_lines)

state_a = world2.getGameState()
reward_calc2.compute(state_a)

# 给线路1连续分配4辆列车
for i in range(4):
    executor2.execute(1, world2, state_a)
    state_a = world2.getGameState()

reward_unbalanced = reward_calc2.compute(state_a)
print(f"  奖励: {reward_unbalanced:.2f}")
print(f"  线路列车分布: {[l['train_count'] for l in state_a['lines']]}")
print(f"  标准差惩罚: （列车分布不均）")

# 场景5: 平衡分布（每条线路1辆）
print("\n" + "-"*60)
print("场景5: 平衡分布（每条线路1辆）")
print("-"*60)

world3 = AIWorld(cfg)
world3.setup()
rule_based_build_lines(world3)
world3.lock_lines()
reward_calc3 = RewardCalculator(overcrowd_limit=cfg.overcrowd_limit)
executor3 = ActionExecutor(max_lines=cfg.max_lines)

state_b = world3.getGameState()
reward_calc3.compute(state_b)

# 给每条线路分配1辆列车
for i in range(1, 5):
    executor3.execute(i, world3, state_b)
    state_b = world3.getGameState()

reward_balanced = reward_calc3.compute(state_b)
print(f"  奖励: {reward_balanced:.2f}")
print(f"  线路列车分布: {[l['train_count'] for l in state_b['lines']]}")
print(f"  标准差=0（完全均衡）")

print("\n" + "="*60)
print("对比总结")
print("="*60)
print(f"不平衡分布（4,0,0,0）奖励: {reward_unbalanced:.2f}")
print(f"平衡分布（1,1,1,1）奖励: {reward_balanced:.2f}")
print(f"平衡优势: {reward_balanced - reward_unbalanced:.2f} 分")
print("="*60)