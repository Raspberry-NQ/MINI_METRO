# visualize_ai_decision.py — AI决策可视化工具
#
# 用法:
#   python visualize_ai_decision.py --model ai/checkpoints/best_scheduler.pt
#
# 功能:
#   - 实时显示AI的每个决策动作
#   - 显示决策前后的状态对比
#   - 显示奖励变化和累计奖励
#   - 详细显示列车状态、乘客分布、站点拥堵
#   - 支持暂停、慢速播放、单步执行

import os
import sys
import time
import pygame
import math

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from world.ai_world import AIWorld
from world.game_config import GameConfig
from ai.src.scheduler_encoder import SchedulerEncoder
from ai.src.action_space import ActionSpace
from ai.src.dqn_agent import DQNAgent
from ai.src.action_executor import ActionExecutor
from ai.src.reward import RewardCalculator
from ai.src.train_scheduler import rule_based_build_lines, rule_based_place_trains
from game.visualizer import Visualizer, draw_shape


class AIDecisionVisualizer(Visualizer):
    """AI决策可视化器，继承基础可视化器并添加决策信息显示"""

    def __init__(self, world, agent, encoder, action_space, executor, reward_calc, config=None):
        """初始化AI决策可视化器

        参数:
            world: 游戏世界对象
            agent: DQN智能体
            encoder: 状态编码器
            action_space: 动作空间
            executor: 动作执行器
            reward_calc: 奖励计算器
            config: 游戏配置
        """
        super().__init__(world, config)
        self.agent = agent
        self.encoder = encoder
        self.action_space = action_space
        self.executor = executor
        self.reward_calc = reward_calc

        # AI决策相关状态
        self.last_action = 0  # 上一次动作
        self.last_action_name = "无操作"
        self.last_reward = 0.0
        self.total_reward = 0.0
        self.decision_count = 0
        self.last_state_dict = None
        self.action_history = []  # 动作历史记录

        # 决策间隔计数
        self.tick_since_last_decision = 0

        # 单步模式
        self.step_mode = False  # 单步执行模式
        self.waiting_for_step = False  # 等待用户按键继续

        # 动作名称映射
        self.action_names = {
            0: "无操作",
            1: "线路1+列车",
            2: "线路2+列车",
            3: "线路3+列车",
            4: "线路4+列车",
            5: "线路1+车厢",
            6: "线路2+车厢",
            7: "线路3+车厢",
            8: "线路4+车厢",
        }

        # 决策详情面板
        self.show_detail_panel = True

    def draw(self):
        """主绘制函数，添加AI决策信息"""
        super().draw()  # 绘制基础元素
        self._draw_ai_decision_info()
        self._draw_detail_panel()
        pygame.display.flip()

    def _draw_ai_decision_info(self):
        """绘制AI决策信息"""
        cfg = self.config

        # 左侧决策信息面板
        y = 100
        x = 10

        # 决策次数
        self._hud_text(f"AI决策: {self.decision_count}次", x, y, color=(60, 60, 180))
        y += 22

        # 最近动作
        action_color = (60, 180, 60) if self.last_action != 0 else (150, 150, 150)
        self._hud_text(f"动作: {self.last_action_name}", x, y, color=action_color)
        y += 22

        # 最近奖励
        reward_color = (60, 180, 60) if self.last_reward > 0 else (180, 60, 60) if self.last_reward < 0 else (150, 150, 150)
        self._hud_text(f"奖励: {self.last_reward:+.2f}", x, y, color=reward_color)
        y += 22

        # 累计奖励
        total_color = (60, 180, 60) if self.total_reward > 0 else (180, 60, 60)
        self._hud_text(f"累计奖励: {self.total_reward:.2f}", x, y, color=total_color)
        y += 22

        # 距下次决策
        next_decision = cfg.decision_interval - self.tick_since_last_decision
        self._hud_text(f"下次决策: {next_decision} tick", x, y, color=(120, 120, 120))
        y += 22

        # 单步模式提示
        if self.step_mode:
            self._hud_text("[单步模式] 按S继续", x, y, color=(255, 200, 0))
            y += 22

    def _draw_detail_panel(self):
        """绘制详细状态面板"""
        if not self.show_detail_panel:
            return

        cfg = self.config
        state = self.last_state_dict or self.world.getGameState()

        # 右侧详细面板
        panel_x = cfg.window_width - 300
        panel_y = 80
        panel_width = 290
        panel_height = 500

        # 半透明背景
        panel_surface = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        panel_surface.fill((245, 245, 235, 230))
        self.screen.blit(panel_surface, (panel_x, panel_y))

        # 边框
        pygame.draw.rect(self.screen, (100, 100, 100),
                        (panel_x, panel_y, panel_width, panel_height), 2)

        y = panel_y + 10
        x = panel_x + 10

        # 标题
        title = self.font_large.render("详细状态", True, (60, 60, 60))
        self.screen.blit(title, (x, y))
        y += 30

        # 全局指标
        metrics = state.get("metrics", {})
        self._detail_text(f"总等待: {metrics.get('total_waiting', 0)}", x, y)
        y += 20
        self._detail_text(f"风险站点: {metrics.get('at_risk_stations', 0)}", x, y)
        y += 20
        self._detail_text(f"到达乘客: {metrics.get('total_arrived', 0)}", x, y)
        y += 20
        self._detail_text(f"最大站候车: {metrics.get('max_station_passengers', 0)}", x, y)
        y += 20
        self._detail_text(f"未连通站点: {metrics.get('unconnected_stations', 0)}", x, y)
        y += 30

        # 线路详情
        self._detail_text("=== 线路状态 ===", x, y, color=(80, 80, 80))
        y += 20

        lines = state.get("lines", [])
        for i, line in enumerate(lines[:cfg.max_lines]):
            line_color = self.get_line_color(line["id"])
            station_count = len(line.get("station_ids", []))
            self._detail_text(
                f"线路{line['id']}: {line['train_count']}车 {station_count}站",
                x, y, color=line_color
            )
            y += 18
            # 显示站点乘客
            if station_count > 0:
                # 计算该线路站点的平均候车人数
                station_ids = line.get("station_ids", [])
                stations_data = state.get("stations", [])
                line_stations = [s for s in stations_data if s["id"] in station_ids]
                if line_stations:
                    avg_pax = sum(s["passenger_count"] for s in line_stations) / len(line_stations)
                    self._detail_text(f"  平均候车: {avg_pax:.1f}", x + 10, y, font=self.font_small)
                    y += 16

        y += 10

        # 列车详情
        self._detail_text("=== 列车状态 ===", x, y, color=(80, 80, 80))
        y += 20

        trains = state.get("trains", [])
        for i, train in enumerate(trains[:8]):  # 最多显示8辆
            status_map = {
                0: "空闲", 1: "下车", 2: "上车",
                3: "停用", 4: "运行", 5: "调车", 6: "等待"
            }
            status_name = status_map.get(train["status"], "?")

            # 状态颜色
            status_color = {
                0: (150, 150, 150),  # 空闲-灰
                1: (60, 180, 60),    # 下车-绿
                2: (60, 180, 60),    # 上车-绿
                3: (180, 60, 60),    # 停用-红
                4: (60, 120, 220),   # 运行-蓝
                5: (180, 120, 60),   # 调车-橙
                6: (180, 180, 60),   # 等待-黄
            }.get(train["status"], (150, 150, 150))

            line_id = train.get("line_id", -1)
            line_color = self.get_line_color(line_id) if line_id >= 0 else (150, 150, 150)

            self._detail_text(
                f"车{train['id']}: 线{line_id if line_id >= 0 else '-'} {status_name}",
                x, y, color=line_color
            )
            y += 18

            # 详细信息
            pax = train.get("passenger_count", 0)
            cap = train.get("capacity", 0)
            cars = train.get("carriage_count", 1)
            self._detail_text(
                f"  {pax}/{cap}人 {cars}厢",
                x + 10, y, font=self.font_small, color=status_color
            )
            y += 16

            if y > panel_y + panel_height - 30:
                break

        # 可用资源
        y += 10
        avail = state.get("available", {})
        self._detail_text("=== 可用资源 ===", x, y, color=(80, 80, 80))
        y += 20
        self._detail_text(f"空闲列车: {avail.get('trains', 0)}", x, y)
        y += 18
        self._detail_text(f"空闲车厢: {avail.get('carriages', 0)}", x, y)
        y += 18
        self._detail_text(f"剩余线路: {avail.get('lines_remaining', 0)}", x, y)

    def _detail_text(self, text, x, y, font=None, color=None):
        """绘制详细面板文本

        参数:
            text: 文本内容
            x: x坐标
            y: y坐标
            font: 字体对象
            color: 颜色
        """
        font = font or self.font
        color = color or (60, 60, 60)
        surf = font.render(text, True, color)
        self.screen.blit(surf, (x, y))

    def handle_events(self):
        """处理pygame事件，添加AI可视化相关控制"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                elif event.key == pygame.K_SPACE:
                    self.paused = not self.paused
                elif event.key == pygame.K_s:
                    # 单步模式：按S继续下一步
                    if self.step_mode and self.waiting_for_step:
                        self.waiting_for_step = False
                elif event.key == pygame.K_m:
                    # 切换单步模式
                    self.step_mode = not self.step_mode
                    self.waiting_for_step = False
                    print(f"单步模式: {'开启' if self.step_mode else '关闭'}")
                elif event.key == pygame.K_d:
                    # 切换详细面板
                    self.show_detail_panel = not self.show_detail_panel
                elif event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                    self.sim_speed = min(20, self.sim_speed + 1)
                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    self.sim_speed = max(1, self.sim_speed - 1)
                elif event.key == pygame.K_r:
                    # 重置视角
                    self.offset_x = self.config.window_width // 2
                    self.offset_y = self.config.window_height // 2
                    self.zoom = 1.0

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # 左键拖拽
                    self.dragging = True
                    self.drag_start = event.pos
                    self.offset_start = (self.offset_x, self.offset_y)
                elif event.button == 4:  # 滚轮上
                    self._zoom_at(event.pos, 1.15)
                elif event.button == 5:  # 滚轮下
                    self._zoom_at(event.pos, 1 / 1.15)

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    self.dragging = False

            elif event.type == pygame.MOUSEMOTION:
                if self.dragging:
                    dx = event.pos[0] - self.drag_start[0]
                    dy = event.pos[1] - self.drag_start[1]
                    self.offset_x = self.offset_start[0] + dx
                    self.offset_y = self.offset_start[1] + dy

        return True

    def run_with_ai(self, max_decisions=100):
        """带AI决策的可视化运行

        参数:
            max_decisions: 最大决策次数
        """
        running = True
        tick_count = 0

        print("\n" + "="*60)
        print("AI决策可视化模式")
        print("="*60)
        print("控制键:")
        print("  [Space] 暂停/继续")
        print("  [S] 单步执行（在单步模式下）")
        print("  [M] 切换单步模式")
        print("  [D] 切换详细面板")
        print("  [+/-] 调整速度")
        print("  [Scroll] 缩放")
        print("  [Drag] 平移")
        print("  [Esc] 退出")
        print("="*60 + "\n")

        while running and not self.world.game_over and self.decision_count < max_decisions:
            # 处理事件
            running = self.handle_events()

            # 单步模式下等待用户按键
            if self.step_mode and self.waiting_for_step:
                self.draw()
                self.clock.tick(self.config.fps)
                continue

            # 模拟更新（暂停时不更新）
            if not self.paused:
                # 抑制输出
                import io
                _original_stdout = sys.stdout
                sys.stdout = io.StringIO()

                try:
                    # 更新一个tick
                    self.world.updateOneTick()
                    tick_count += 1
                    self.tick_since_last_decision += 1
                finally:
                    sys.stdout = _original_stdout

                # 检查是否需要AI决策
                if tick_count > 0 and tick_count % self.config.decision_interval == 0:
                    self._make_ai_decision()

                    # 单步模式下等待下一步
                    if self.step_mode:
                        self.waiting_for_step = True

            # 绘制
            self.draw()
            self.clock.tick(self.config.fps)

        # 结束统计
        print("\n" + "="*60)
        print("可视化结束")
        print("="*60)
        print(f"总tick: {tick_count}")
        print(f"决策次数: {self.decision_count}")
        print(f"累计奖励: {self.total_reward:.2f}")
        print(f"到达乘客: {self.world.pm.arrivedNum}")

        if self.world.game_over:
            print("游戏结束原因: 站点拥堵")
        else:
            print(f"达到决策上限: {max_decisions}")

        # 动作统计
        print("\n动作分布:")
        action_counts = {}
        for action in self.action_history:
            action_counts[action] = action_counts.get(action, 0) + 1
        for action, count in sorted(action_counts.items()):
            name = self.action_names.get(action, f"动作{action}")
            print(f"  {name}: {count}次")

        print("="*60)

        pygame.quit()

    def _make_ai_decision(self):
        """执行一次AI决策"""
        import io
        _original_stdout = sys.stdout
        sys.stdout = io.StringIO()

        try:
            # 获取当前状态
            state_dict = self.world.getGameState()
            state_tensor = self.encoder.encode(state_dict)

            # 计算奖励
            reward = self.reward_calc.compute(state_dict)
            self.last_reward = reward
            self.total_reward += reward

            # 选择动作
            valid_mask = self.action_space.get_valid_mask(state_dict)
            action = self.agent.select_action(state_tensor.unsqueeze(0), valid_mask)

            # 执行动作
            self.executor.execute(action, self.world, state_dict)

            # 记录
            self.last_action = action
            self.last_action_name = self.action_names.get(action, f"动作{action}")
            self.last_state_dict = state_dict
            self.decision_count += 1
            self.tick_since_last_decision = 0
            self.action_history.append(action)

        finally:
            sys.stdout = _original_stdout

        # 打印决策信息（恢复stdout后）
        print(f"\n[决策 {self.decision_count}] tick={self.world.tick}")
        print(f"  动作: {self.last_action_name}")
        print(f"  奖励: {reward:+.2f} (累计: {self.total_reward:.2f})")

        # 打印状态变化
        metrics = state_dict.get("metrics", {})
        print(f"  等待乘客: {metrics.get('total_waiting', 0)}")
        print(f"  风险站点: {metrics.get('at_risk_stations', 0)}")
        print(f"  到达乘客: {metrics.get('total_arrived', 0)}")


def main():
    """主函数"""
    import argparse
    parser = argparse.ArgumentParser(description="AI决策可视化")
    parser.add_argument("--model", type=str, default="ai/checkpoints/best_scheduler.pt",
                       help="模型文件路径")
    parser.add_argument("--max-decisions", type=int, default=100,
                       help="最大决策次数")
    args = parser.parse_args()

    # 检查模型文件
    if not os.path.exists(args.model):
        print(f"错误: 模型文件不存在: {args.model}")
        print("请先训练模型: python ai/src/train_scheduler.py")
        return

    # 初始化配置
    cfg = GameConfig.for_ai_training()
    encoder = SchedulerEncoder(cfg)
    action_space = ActionSpace(max_lines=cfg.max_lines)
    executor = ActionExecutor(max_lines=cfg.max_lines)
    reward_calc = RewardCalculator(overcrowd_limit=cfg.overcrowd_limit)

    # 计算状态维度
    state_dim = 11 + cfg.max_lines * 7 + cfg.max_trains * 6 + 6

    # 创建agent并加载模型
    agent = DQNAgent(state_dim=state_dim, n_actions=action_space.n_actions)
    agent.load(args.model)
    agent.epsilon = 0.0  # 关闭探索，使用训练好的策略

    print(f"\n加载模型: {args.model}")
    print(f"运行模式: 最多 {args.max_decisions} 次决策")

    # 初始化世界
    import io
    _original_stdout = sys.stdout
    sys.stdout = io.StringIO()

    try:
        world = AIWorld(cfg)
        world.setup()
        rule_based_build_lines(world)
        world.place_initial_trains(rule_based_place_trains(world))
        world.lock_lines()
    finally:
        sys.stdout = _original_stdout

    print("世界初始化完成")

    # 创建可视化器并运行
    viz = AIDecisionVisualizer(
        world, agent, encoder, action_space, executor, reward_calc, cfg
    )
    viz.run_with_ai(max_decisions=args.max_decisions)


if __name__ == "__main__":
    main()