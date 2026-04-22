# train_scheduler.py — 列车调度器训练脚本
#
# 用法:
#   cd /Users/raspberry/developProject/MINI_METRO
#   python -m AI.src.train_scheduler
#
# 或:
#   python AI/src/train_scheduler.py

import os
import sys
import time
import io
import contextlib
import numpy as np

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import torch

from ai_world import AIWorld
from game_config import GameConfig
from station import (
    CATEGORY_RESIDENTIAL, CATEGORY_COMMERCIAL, CATEGORY_OFFICE,
    CATEGORY_SCHOOL, CATEGORY_HOSPITAL, CATEGORY_SCENIC,
)

from AI.src.scheduler_encoder import SchedulerEncoder
from AI.src.action_space import ActionSpace
from AI.src.dqn_agent import DQNAgent
from AI.src.reward import RewardCalculator
from AI.src.action_executor import ActionExecutor


# ============================================================
# 规则建线 (训练调度器时, 先用简单规则生成线路)
# ============================================================

def rule_based_build_lines(world):
    """用规则建线, 给调度器训练用

    策略:
      1. 以居民区为枢纽, 每条线共享一个居民区站点作为换乘点
      2. 确保每个类别至少有一个站在线路上
      3. 线路之间通过共享站点连通, 保证换乘可达
    """
    stations = world.stations
    category_groups = {}
    for s in stations:
        category_groups.setdefault(s.category, []).append(s)

    residential = category_groups.get(CATEGORY_RESIDENTIAL, [])
    office = category_groups.get(CATEGORY_OFFICE, [])
    commercial = category_groups.get(CATEGORY_COMMERCIAL, [])
    school = category_groups.get(CATEGORY_SCHOOL, [])
    hospital = category_groups.get(CATEGORY_HOSPITAL, [])
    scenic = category_groups.get(CATEGORY_SCENIC, [])

    # 选一个居民区站作为所有线路的换乘枢纽
    hub = residential[0] if residential else None

    # 非居民区类别
    other_cats = [
        (CATEGORY_OFFICE, office),
        (CATEGORY_COMMERCIAL, commercial),
        (CATEGORY_SCHOOL, school),
        (CATEGORY_HOSPITAL, hospital),
        (CATEGORY_SCENIC, scenic),
    ]

    lines_built = []

    # 线路1: 主体线 — 贯穿多个居民区 + 办公区
    if len(residential) >= 2 and len(office) >= 1:
        line_stations = residential[:4] + office[:2]
        lines_built.append(line_stations)

    # 为每个非居民区类别建一条线, 通过枢纽连接
    # 枢纽站已在主干线上, 所以这些线的乘客可以通过枢纽换乘
    for cat, cat_stations in other_cats:
        if not cat_stations:
            continue
        # 线路: 该类别站点 + 枢纽站 (确保连通)
        # 优先用未覆盖的站点
        covered = set()
        for lb in lines_built:
            covered.update(s.id for s in lb)
        uncovered = [s for s in cat_stations if s.id not in covered]
        pool = uncovered if uncovered else cat_stations

        if hub:
            line_stations = [hub] + pool[:3]
        else:
            line_stations = pool[:4]

        if len(line_stations) >= 2:
            lines_built.append(line_stations)

    # 如果还有剩余居民区未覆盖, 加一条居民区-商业区线
    covered_ids = set()
    for lb in lines_built:
        covered_ids.update(s.id for s in lb)
    uncovered_res = [s for s in residential if s.id not in covered_ids]
    uncovered_comm = [s for s in commercial if s.id not in covered_ids]
    if len(uncovered_res) >= 2 and len(uncovered_comm) >= 1:
        line_stations = uncovered_res[:3] + uncovered_comm[:2]
        if len(line_stations) >= 2:
            lines_built.append(line_stations)

    for station_list in lines_built:
        if len(station_list) >= 2:
            world.playerNewLine(station_list)


def rule_based_place_trains(world):
    """给每条线路放初始列车, 每条线 1-2 辆"""
    placements = []
    for line in world.metroLine:
        if len(line.stationList) >= 2:
            first_station = line.stationList[0]
            placements.append({
                "line_id": line.number,
                "station_id": first_station.id,
                "direction": True,
            })
            # 长线路放第二辆
            if len(line.stationList) >= 4 and line.trainNm < 2:
                last_station = line.stationList[-1]
                placements.append({
                    "line_id": line.number,
                    "station_id": last_station.id,
                    "direction": False,
                })
    return placements


# ============================================================
# 训练循环
# ============================================================

class _SuppressPrint:
    """上下文管理器: 临时抑制 stdout 的 print 输出"""
    def __enter__(self):
        self._original_stdout = sys.stdout
        sys.stdout = io.StringIO()
        return self
    def __exit__(self, *args):
        sys.stdout = self._original_stdout


def train_scheduler(num_episodes=5000):
    """训练列车调度器

    每个 episode = 一天 (1200 tick), 每 60 tick 决策一次, 共 20 步
    """
    # --- 初始化 ---
    cfg = GameConfig.for_ai_training()
    encoder = SchedulerEncoder(cfg)
    action_space = ActionSpace(max_lines=cfg.max_lines)
    agent = DQNAgent(
        state_dim=186,
        n_actions=action_space.n_actions,
    )
    executor = ActionExecutor(max_lines=cfg.max_lines)
    reward_calc = RewardCalculator(overcrowd_limit=cfg.overcrowd_limit)

    # checkpoint 目录
    ckpt_dir = os.path.join(PROJECT_ROOT, "AI", "checkpoints")
    os.makedirs(ckpt_dir, exist_ok=True)

    # 训练日志
    episode_rewards = []
    episode_survived = []
    episode_arrived = []
    best_avg_reward = -float('inf')

    print(f"{'='*60}")
    print(f"列车调度器训练开始")
    print(f"  episodes: {num_episodes}")
    print(f"  device: {agent.device}")
    print(f"  state_dim: 186")
    print(f"  n_actions: {action_space.n_actions}")
    print(f"  day_length: {cfg.day_length} tick")
    print(f"  max_lines: {cfg.max_lines}")
    print(f"  max_trains: {cfg.max_trains}")
    print(f"{'='*60}\n")

    start_time = time.time()

    for episode in range(num_episodes):
        # --- 1. 重置环境 ---
        with _SuppressPrint():
            world = AIWorld(cfg)
            world.setup()
            rule_based_build_lines(world)
            initial_placements = rule_based_place_trains(world)
            world.place_initial_trains(initial_placements)
            world.lock_lines()

        # --- 2. 运行一天 ---
        # 记录天开始时的到达人数, 用于结算报告
        start_arrived = world._count_arrived()

        reward_calc.reset()
        state_dict = world.getGameState()
        state_tensor = encoder.encode(state_dict)
        episode_reward = 0.0
        decision_step = 0
        last_action = 0  # 初始为不操作

        # 手动 tick 循环 (而非用 run_one_day), 以便在每个决策步采集经验
        # 抑制游戏引擎的调试输出
        with _SuppressPrint():
            for tick_in_day in range(cfg.day_length):
                if world.game_over:
                    break

                world.updateOneTick()

                # 每 60 tick 决策一次
                if tick_in_day > 0 and tick_in_day % 60 == 0:
                    next_state_dict = world.getGameState()
                    next_state_tensor = encoder.encode(next_state_dict)

                    # 计算奖励
                    reward = reward_calc.compute(next_state_dict)
                    done = world.game_over

                    # 存经验
                    agent.buffer.push(
                        state_tensor,
                        last_action,
                        reward,
                        next_state_tensor,
                        float(done)
                    )

                    # 选择新动作
                    valid_mask = action_space.get_valid_mask(next_state_dict)
                    action = agent.select_action(next_state_tensor.unsqueeze(0), valid_mask)
                    executor.execute(action, world, next_state_dict)

                    # 更新网络
                    agent.update()

                    # 记录
                    episode_reward += reward
                    state_tensor = next_state_tensor
                    state_dict = next_state_dict
                    last_action = action
                    decision_step += 1

        # --- 3. Episode 结束 ---
        # 读取结算报告
        with _SuppressPrint():
            report = world._day_summary(start_arrived, 0)
        survived = report.get("survived", not world.game_over)
        arrived = report.get("passengers_arrived_today", 0)

        episode_rewards.append(episode_reward)
        episode_survived.append(1 if survived else 0)
        episode_arrived.append(arrived)

        # 打印进度 (前 20 个 episode 每个都打印, 之后每 10 个打印)
        print_interval = 1 if num_episodes <= 20 else 10
        if (episode + 1) % print_interval == 0:
            elapsed = time.time() - start_time
            window = min(10, len(episode_rewards))
            avg_reward = np.mean(episode_rewards[-window:])
            avg_survival = np.mean(episode_survived[-window:]) * 100
            avg_arrived = np.mean(episode_arrived[-window:])
            print(f"Episode {episode+1:5d}/{num_episodes} | "
                  f"Avg Reward: {avg_reward:7.2f} | "
                  f"Survival: {avg_survival:5.1f}% | "
                  f"Avg Arrived: {avg_arrived:6.1f} | "
                  f"Epsilon: {agent.epsilon:.3f} | "
                  f"Steps: {agent.step_count} | "
                  f"Time: {elapsed:.0f}s")

        # 保存最佳模型
        if (episode + 1) % 50 == 0 and len(episode_rewards) >= 10:
            avg_reward = np.mean(episode_rewards[-50:])
            if avg_reward > best_avg_reward:
                best_avg_reward = avg_reward
                ckpt_path = os.path.join(ckpt_dir, "best_scheduler.pt")
                agent.save(ckpt_path)
                print(f"  → 新最佳模型! avg_reward={avg_reward:.2f}, 保存到 {ckpt_path}")

        # 定期保存 checkpoint
        if (episode + 1) % 500 == 0:
            ckpt_path = os.path.join(ckpt_dir, f"scheduler_ep{episode+1}.pt")
            agent.save(ckpt_path)
            print(f"  → Checkpoint 保存: {ckpt_path}")

    # 训练结束
    total_time = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"训练完成! 总用时: {total_time:.0f}s")
    print(f"  最佳平均奖励: {best_avg_reward:.2f}")
    print(f"  最终 epsilon: {agent.epsilon:.4f}")
    print(f"  总训练步数: {agent.step_count}")
    print(f"{'='*60}")

    # 保存最终模型
    final_path = os.path.join(ckpt_dir, "scheduler_final.pt")
    agent.save(final_path)
    print(f"最终模型保存到: {final_path}")

    return agent


# ============================================================
# 评估
# ============================================================

def evaluate_scheduler(agent_path=None, num_episodes=10):
    """测试训练好的调度器"""
    cfg = GameConfig.for_ai_training()
    encoder = SchedulerEncoder(cfg)
    action_space = ActionSpace(max_lines=cfg.max_lines)
    executor = ActionExecutor(max_lines=cfg.max_lines)

    agent = DQNAgent(state_dim=186, n_actions=action_space.n_actions)
    if agent_path:
        agent.load(agent_path)
    agent.epsilon = 0.0  # 关闭探索

    print(f"\n{'='*60}")
    print(f"评估调度器 ({num_episodes} episodes)")
    print(f"{'='*60}")

    for ep in range(num_episodes):
        with _SuppressPrint():
            world = AIWorld(cfg)
            world.setup()
            rule_based_build_lines(world)
            world.place_initial_trains(rule_based_place_trains(world))
            world.lock_lines()

            def scheduler_callback(w, _encoder=encoder, _agent=agent,
                                    _action_space=action_space, _executor=executor):
                state_dict = w.getGameState()
                state_tensor = _encoder.encode(state_dict).unsqueeze(0)
                valid_mask = _action_space.get_valid_mask(state_dict)
                action = _agent.select_action(state_tensor, valid_mask)
                _executor.execute(action, w, state_dict)

            report = world.run_one_day(ai_callback=scheduler_callback)

        print(f"\n--- Episode {ep+1} ---")
        world.print_day_report(report)

    print(f"\n{'='*60}")


# ============================================================
# 入口
# ============================================================

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="列车调度器训练/评估")
    parser.add_argument("--eval", action="store_true", help="评估模式")
    parser.add_argument("--model", type=str, default=None, help="模型路径 (评估时用)")
    parser.add_argument("--episodes", type=int, default=5000, help="训练 episode 数")
    args = parser.parse_args()

    if args.eval:
        evaluate_scheduler(agent_path=args.model, num_episodes=10)
    else:
        train_scheduler(num_episodes=args.episodes)
