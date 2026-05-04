# train_scheduler.py — 列车调度器训练脚本
#
# 用法:
#   cd /Users/raspberry/developProject/MINI_METRO
#   python -m ai.src.train_scheduler
#
# 或:
#   python ai/src/train_scheduler.py

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

from world.ai_world import AIWorld
from world.game_config import GameConfig
from world.map_data import MapData
from core.station import (
    CATEGORY_RESIDENTIAL, CATEGORY_COMMERCIAL, CATEGORY_OFFICE,
    CATEGORY_SCHOOL, CATEGORY_HOSPITAL, CATEGORY_SCENIC,
)

# 使用相对导入（当作为模块运行时）
try:
    from .scheduler_encoder import SchedulerEncoder
    from .action_space import ActionSpace
    from .dqn_agent import DQNAgent
    from .reward import RewardCalculator
    from .action_executor import ActionExecutor
except ImportError:
    # 如果相对导入失败，使用绝对导入
    from ai.src.scheduler_encoder import SchedulerEncoder
    from ai.src.action_space import ActionSpace
    from ai.src.dqn_agent import DQNAgent
    from ai.src.reward import RewardCalculator
    from ai.src.action_executor import ActionExecutor


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

# 全局的null文件，用于抑制输出
_DEVNULL = open(os.devnull, 'w')

class _SuppressPrint:
    """上下文管理器: 临时抑制 stdout 的 print 输出"""
    def __enter__(self):
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        sys.stdout = _DEVNULL
        sys.stderr = _DEVNULL
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self._original_stdout
        sys.stderr = self._original_stderr
        # 强制flush
        sys.stdout.flush()
        sys.stderr.flush()
        # 不抑制异常，让它们正常传播
        return False


def train_scheduler(num_episodes=5000, config=None, map_paths=None):
    """训练列车调度器

    参数:
        num_episodes: 训练的 episode 数量，默认为 5000
        config: 游戏配置对象，如果为 None 则使用默认 AI 训练配置
        map_paths: 地图文件路径列表，如果为 None 则随机生成地图
                   如果提供多个地图，每个episode随机选择一个

    每个 episode = 一天 (1200 tick), 每 60 tick 决策一次, 共 20 步
    """
    # --- 初始化 ---
    cfg = config if config is not None else GameConfig.for_ai_training()
    encoder = SchedulerEncoder(cfg)
    action_space = ActionSpace(max_lines=cfg.max_lines)

    # 计算状态维度: 11 + max_lines×7 + max_trains×6 + 6
    state_dim = 11 + cfg.max_lines * 7 + cfg.max_trains * 6 + 6

    agent = DQNAgent(
        state_dim=state_dim,
        n_actions=action_space.n_actions,
    )
    executor = ActionExecutor(max_lines=cfg.max_lines)
    reward_calc = RewardCalculator(overcrowd_limit=cfg.overcrowd_limit)

    # 加载地图（如果提供）
    maps = []
    if map_paths:
        for path in map_paths:
            map_data = MapData()
            map_data.load(path)
            is_valid, errors = map_data.validate()
            if not is_valid:
                print(f"[ERROR] 地图 {path} 验证失败:")
                for err in errors:
                    print(f"  - {err}")
                continue
            maps.append(map_data)
            print(f"✓ 加载地图: {path}")

        if not maps:
            print("[WARN] 没有有效的地图，将使用随机生成")
    else:
        print("[INFO] 未提供地图，将使用随机生成")

    # checkpoint 目录
    ckpt_dir = os.path.join(PROJECT_ROOT, "ai", "checkpoints")
    os.makedirs(ckpt_dir, exist_ok=True)

    # 训练日志
    log_file = os.path.join(PROJECT_ROOT, "training_log.txt")
    log_f = open(log_file, 'w')
    log_f.write("Episode,Avg_Reward,Survival_Rate,Avg_Arrived,Epsilon,Steps\n")

    episode_rewards = []
    episode_survived = []
    episode_arrived = []
    best_avg_reward = -float('inf')

    print(f"\n{'='*60}")
    print(f"列车调度器训练开始")
    print(f"  episodes: {num_episodes}")
    print(f"  device: {agent.device}")
    print(f"  state_dim: {state_dim}")
    print(f"  n_actions: {action_space.n_actions}")
    print(f"  day_length: {cfg.day_length} tick")
    print(f"  max_lines: {cfg.max_lines}")
    print(f"  max_trains: {cfg.max_trains}")
    print(f"  max_ticks: {cfg.max_ticks_per_episode} tick (上限)")
    print(f"  decision_interval: {cfg.decision_interval} tick")
    if maps:
        print(f"  地图数量: {len(maps)}")
        print(f"  地图模式: 从地图文件加载")
    else:
        print(f"  地图模式: 随机生成")
    print(f"{'='*60}\n")

    start_time = time.time()

    for episode in range(num_episodes):
        # --- 1. 重置环境 ---
        print(f"\nEpisode {episode+1}/{num_episodes} 初始化中...", end=" ", flush=True)

        with _SuppressPrint():
            world = AIWorld(cfg)

            # 根据是否提供地图选择初始化方式
            if maps:
                # 从地图列表中随机选择一个
                import random
                selected_map = random.choice(maps)
                world.setup_from_map(selected_map)
            else:
                # 使用原有的随机生成方式
                world.setup()
                rule_based_build_lines(world)
                world.lock_lines()

        print("✓", flush=True)

        # --- 2. 持续运行直到游戏结束或达到上限 ---
        reward_calc.reset()
        state_dict = world.getGameState()
        state_tensor = encoder.encode(state_dict)
        episode_reward = 0.0
        decision_step = 0
        last_action = 0  # 初始为不操作
        episode_start_time = time.time()

        # 持续运行，不再限制为一天
        tick_count = 0
        last_print_tick = 0

        while not world.game_over and tick_count < cfg.max_ticks_per_episode:
            # 抑制tick更新的输出
            with _SuppressPrint():
                world.updateOneTick()
            tick_count += 1

            # 每 1000 tick 打印一次进度（此时stdout已恢复）
            if tick_count - last_print_tick >= 1000:
                elapsed = time.time() - episode_start_time
                print(f"  Tick {tick_count}/{cfg.max_ticks_per_episode} "
                      f"({tick_count/cfg.max_ticks_per_episode*100:.1f}%) "
                      f"奖励: {episode_reward:.2f} "
                      f"速度: {tick_count/max(elapsed,1):.1f} ticks/s", flush=True)
                last_print_tick = tick_count

                # 按配置的决策间隔进行决策
            if tick_count > 0 and tick_count % cfg.decision_interval == 0:
                # 决策时也抑制输出
                with _SuppressPrint():
                    next_state_dict = world.getGameState()
                    next_state_tensor = encoder.encode(next_state_dict)

                    # 计算奖励
                    reward = reward_calc.compute(next_state_dict)
                    done = world.game_over or tick_count >= cfg.max_ticks_per_episode

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
        # 统计数据
        final_state = world.getGameState()
        metrics = final_state.get("metrics", {})
        arrived = metrics.get("total_arrived", 0)
        survived = not world.game_over

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

            # 写入日志
            log_f.write(f"{episode+1},{avg_reward:.2f},{avg_survival:.1f},{avg_arrived:.1f},{agent.epsilon:.4f},{agent.step_count}\n")
            log_f.flush()

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

    # 关闭日志文件
    log_f.close()
    print(f"训练日志已保存到: {log_file}")

    # 保存最终模型
    final_path = os.path.join(ckpt_dir, "scheduler_final.pt")
    agent.save(final_path)
    print(f"最终模型保存到: {final_path}")

    return agent


# ============================================================
# 评估
# ============================================================

def evaluate_scheduler(agent_path=None, num_episodes=10, max_decisions=50, config=None, map_path=None):
    """测试训练好的调度器

    参数:
        agent_path: 模型文件路径
        num_episodes: 评估的 episode 数量
        max_decisions: 每个episode的最大决策次数（默认50次）
        config: 游戏配置对象，如果为 None 则使用默认 AI 训练配置
        map_path: 地图文件路径，如果为 None 则随机生成地图

    说明:
        每个 episode 运行最多 max_decisions 次决策，然后统计结果。
        如果游戏提前结束（某站点乘客超过限制），也会停止。
    """
    cfg = config if config is not None else GameConfig.for_ai_training()
    encoder = SchedulerEncoder(cfg)
    action_space = ActionSpace(max_lines=cfg.max_lines)
    executor = ActionExecutor(max_lines=cfg.max_lines)

    # 计算状态维度
    state_dim = 11 + cfg.max_lines * 7 + cfg.max_trains * 6 + 6

    agent = DQNAgent(state_dim=state_dim, n_actions=action_space.n_actions)
    if agent_path:
        agent.load(agent_path)
    agent.epsilon = 0.0  # 关闭探索，完全使用训练好的策略

    # 加载地图（如果提供）
    map_data = None
    if map_path:
        map_data = MapData()
        map_data.load(map_path)
        is_valid, errors = map_data.validate()
        if not is_valid:
            print(f"[ERROR] 地图 {map_path} 验证失败:")
            for err in errors:
                print(f"  - {err}")
            return []
        print(f"✓ 加载地图: {map_path}")
    else:
        print("[INFO] 未提供地图，将使用随机生成")

    print(f"\n{'='*60}")
    print(f"评估调度器 ({num_episodes} episodes)")
    print(f"运行模式: 每个episode最多{max_decisions}次决策")
    if map_data:
        print(f"地图: {map_path}")
    else:
        print(f"地图: 随机生成")
    print(f"{'='*60}")

    episode_results = []

    for ep in range(num_episodes):
        # 初始化世界
        with _SuppressPrint():
            world = AIWorld(cfg)

            if map_data:
                # 使用指定地图
                world.setup_from_map(map_data)
            else:
                # 随机生成
                world.setup()
                rule_based_build_lines(world)
                world.lock_lines()

        # 持续运行直到游戏结束或达到决策上限
        tick_count = 0
        decision_step = 0

        while not world.game_over and decision_step < max_decisions:
            # 更新一个tick
            with _SuppressPrint():
                world.updateOneTick()
            tick_count += 1

            # 按决策间隔进行AI调度
            if tick_count > 0 and tick_count % cfg.decision_interval == 0:
                with _SuppressPrint():
                    state_dict = world.getGameState()
                    state_tensor = encoder.encode(state_dict).unsqueeze(0)
                    valid_mask = action_space.get_valid_mask(state_dict)
                    action = agent.select_action(state_tensor, valid_mask)
                    executor.execute(action, world, state_dict)
                    decision_step += 1

        # Episode结束，统计结果
        # 获取最终统计
        final_state = world.getGameState()
        metrics = final_state.get("metrics", {})
        arrived = metrics.get("total_arrived", 0)
        total_waiting = metrics.get("total_waiting", 0)

        # 找出最拥堵的站点
        max_station = None
        max_wait = 0
        for s in world.stations:
            if s.passengerNm > max_wait:
                max_wait = s.passengerNm
                max_station = s

        result = {
            "episode": ep + 1,
            "ticks": tick_count,
            "days": tick_count / cfg.day_length,
            "arrived": arrived,
            "decisions": decision_step,
            "total_waiting": total_waiting,
            "max_station_wait": max_wait,
            "game_over": world.game_over,
        }
        episode_results.append(result)

        # 简洁输出
        status = "游戏结束" if world.game_over else f"达到决策上限({max_decisions}次)"
        print(f"Episode {ep+1:2d}: {status} | "
              f"决策{decision_step:2d}次 | "
              f"tick {tick_count:4d} ({tick_count/cfg.day_length:.1f}天) | "
              f"到达{arrived:3d}人 | "
              f"等待{total_waiting:3d}人 | "
              f"最大站{max_wait:2d}人")

    # 打印汇总统计
    print(f"\n{'='*60}")
    print(f"评估汇总 ({num_episodes} episodes)")
    print(f"{'='*60}")

    avg_ticks = sum(r["ticks"] for r in episode_results) / len(episode_results)
    avg_days = sum(r["days"] for r in episode_results) / len(episode_results)
    avg_arrived = sum(r["arrived"] for r in episode_results) / len(episode_results)
    avg_decisions = sum(r["decisions"] for r in episode_results) / len(episode_results)
    avg_waiting = sum(r["total_waiting"] for r in episode_results) / len(episode_results)
    avg_max_wait = sum(r["max_station_wait"] for r in episode_results) / len(episode_results)
    game_over_count = sum(1 for r in episode_results if r["game_over"])

    print(f"\n平均统计:")
    print(f"  存活时间: {avg_ticks:.0f} tick ({avg_days:.1f} 天)")
    print(f"  决策次数: {avg_decisions:.1f}")
    print(f"  到达乘客: {avg_arrived:.1f}")
    print(f"  等待乘客: {avg_waiting:.1f}")
    print(f"  最大站候车: {avg_max_wait:.1f}")
    print(f"  游戏结束: {game_over_count}/{num_episodes} 次")

    print(f"\n各Episode详情:")
    print(f"  Episode | 决策 | Tick  | 天数  | 到达 | 等待 | 最大站 | 状态")
    print(f"  --------|------|-------|-------|------|------|--------|------")
    for r in episode_results:
        status = "结束" if r["game_over"] else "运行中"
        print(f"  {r['episode']:7d} | {r['decisions']:4d} | {r['ticks']:5d} | {r['days']:5.1f} | {r['arrived']:4d} | {r['total_waiting']:4d} | {r['max_station_wait']:6d} | {status}")

    print(f"\n{'='*60}")

    return episode_results


# ============================================================
# 入口
# ============================================================

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="列车调度器训练/评估")
    parser.add_argument("--eval", action="store_true", help="评估模式")
    parser.add_argument("--model", type=str, default=None, help="模型路径 (评估时用)")
    parser.add_argument("--episodes", type=int, default=5000, help="训练/评估 episode 数")
    parser.add_argument("--max-decisions", type=int, default=50, help="评估时每个episode的最大决策次数 (默认50)")
    parser.add_argument("--maps", type=str, nargs='+', default=None,
                        help="地图文件路径列表 (训练时可指定多个地图，评估时指定单个地图)")
    args = parser.parse_args()

    if args.eval:
        # 评估模式：如果提供了多个地图，只使用第一个
        map_path = args.maps[0] if args.maps else None
        evaluate_scheduler(
            agent_path=args.model,
            num_episodes=args.episodes,
            max_decisions=args.max_decisions,
            map_path=map_path
        )
    else:
        # 训练模式：可以使用多个地图
        train_scheduler(
            num_episodes=args.episodes,
            map_paths=args.maps
        )
