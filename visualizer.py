# visualizer.py — 基于 pygame 的迷你地铁可视化

import pygame
import sys
import math
import io
from external_functions import countTrainRunningTime
from station import CATEGORY_LABEL_CN

# 站点形状 → 绘制函数 映射
SHAPE_DRAWERS = {}


def _register_shape(name):
    def decorator(fn):
        SHAPE_DRAWERS[name] = fn
        return fn
    return decorator


# ---- 形状绘制 ----

@_register_shape("circle")
def _draw_circle(surface, cx, cy, r, color, width=0):
    pygame.draw.circle(surface, color, (cx, cy), r, width)


@_register_shape("triangle")
def _draw_triangle(surface, cx, cy, r, color, width=0):
    pts = [
        (cx, cy - r),
        (cx - r * math.sin(math.pi / 3), cy + r * 0.5),
        (cx + r * math.sin(math.pi / 3), cy + r * 0.5),
    ]
    pygame.draw.polygon(surface, color, pts, width)


@_register_shape("square")
def _draw_square(surface, cx, cy, r, color, width=0):
    half = r * 0.75
    rect = pygame.Rect(cx - half, cy - half, half * 2, half * 2)
    pygame.draw.rect(surface, color, rect, width)


@_register_shape("diamond")
def _draw_diamond(surface, cx, cy, r, color, width=0):
    pts = [(cx, cy - r), (cx + r * 0.7, cy), (cx, cy + r), (cx - r * 0.7, cy)]
    pygame.draw.polygon(surface, color, pts, width)


@_register_shape("star")
def _draw_star(surface, cx, cy, r, color, width=0):
    pts = []
    for i in range(10):
        angle = math.pi / 2 + i * math.pi / 5
        radius = r if i % 2 == 0 else r * 0.45
        pts.append((cx + radius * math.cos(angle), cy - radius * math.sin(angle)))
    pygame.draw.polygon(surface, color, pts, width)


@_register_shape("pentagon")
def _draw_pentagon(surface, cx, cy, r, color, width=0):
    pts = []
    for i in range(5):
        angle = math.pi / 2 + i * 2 * math.pi / 5
        pts.append((cx + r * math.cos(angle), cy - r * math.sin(angle)))
    pygame.draw.polygon(surface, color, pts, width)


def draw_shape(surface, shape_type, cx, cy, r, color, width=0):
    drawer = SHAPE_DRAWERS.get(shape_type)
    if drawer:
        drawer(surface, cx, cy, r, color, width)
    else:
        pygame.draw.circle(surface, color, (cx, cy), r, width)


# ---- 乘客小形状绘制 (缩小版) ----

def draw_passenger_shape(surface, shape_type, cx, cy, r, color):
    draw_shape(surface, shape_type, int(cx), int(cy), int(r), color)


class Visualizer:
    """迷你地铁的可视化渲染器"""

    def __init__(self, world, config=None):
        self.world = world
        self.config = config or world.config

        # pygame 初始化
        pygame.init()
        self.screen = pygame.display.set_mode(
            (self.config.window_width, self.config.window_height)
        )
        pygame.display.set_caption("Mini Metro")
        self.clock = pygame.time.Clock()

        # 字体
        self.font = pygame.font.SysFont("Arial", self.config.hud_font_size)
        self.font_large = pygame.font.SysFont("Arial", self.config.hud_font_size + 8, bold=True)
        self.font_small = pygame.font.SysFont("Arial", self.config.hud_font_size - 4)

        # 视口平移 & 缩放
        self.offset_x = self.config.window_width // 2
        self.offset_y = self.config.window_height // 2
        self.zoom = 1.0

        # 交互状态
        self.paused = False
        self.sim_speed = self.config.sim_speed
        self.dragging = False
        self.drag_start = None
        self.offset_start = None

        # 选中的站点 (用于线路编辑)
        self.selected_stations = []
        self.selected_line = None
        self.hover_station = None

        # 线路颜色缓存
        self._line_color_map = {}
        self._rebuild_line_colors()

        # 列车动画位置插值缓存
        self._train_display_pos = {}  # train_id -> (x, y)

        # 拖拽创建线路模式
        self.creating_line = False
        self.line_create_stations = []

        # 延伸线路模式
        self.extending_line = None  # 正在延伸的线路对象

        # 游戏结束画面
        self._game_over_shown = False

    def _rebuild_line_colors(self):
        self._line_color_map.clear()
        colors = self.config.line_colors
        for i, line in enumerate(self.world.metroLine):
            self._line_color_map[line.number] = colors[i % len(colors)]

    def get_line_color(self, line_number):
        if line_number not in self._line_color_map:
            self._rebuild_line_colors()
        return self._line_color_map.get(line_number, (150, 150, 150))

    # ---- 坐标变换 ----

    def world_to_screen(self, wx, wy):
        sx = int(wx * self.zoom + self.offset_x)
        sy = int(-wy * self.zoom + self.offset_y)  # y 轴翻转
        return sx, sy

    def screen_to_world(self, sx, sy):
        wx = (sx - self.offset_x) / self.zoom
        wy = -(sy - self.offset_y) / self.zoom
        return wx, wy

    # ---- 主绘制 ----

    def draw(self):
        self.screen.fill(self.config.bg_color)
        self._draw_lines()
        self._draw_stations()
        self._draw_trains()
        self._draw_hud()
        self._draw_line_creation()
        self._draw_line_extension()
        if self.world.game_over:
            self._draw_game_over()
        elif self.paused:
            self._draw_pause_overlay()
        pygame.display.flip()

    # ---- 线路绘制 ----

    def _draw_lines(self):
        cfg = self.config
        for line in self.world.metroLine:
            if len(line.stationList) < 2:
                continue
            color = self.get_line_color(line.number)
            pts = []
            for s in line.stationList:
                pts.append(self.world_to_screen(s.x, s.y))
            pygame.draw.lines(self.screen, color, False, pts, cfg.line_width)

    # ---- 站点绘制 ----

    def _draw_stations(self):
        cfg = self.config
        limit = cfg.overcrowd_limit
        r = int(cfg.station_radius * self.zoom)

        for s in self.world.stations:
            sx, sy = self.world_to_screen(s.x, s.y)

            # 类别底色圆
            cat_color = cfg.category_colors.get(s.category, (220, 220, 220))
            if s.category:
                pygame.draw.circle(self.screen, cat_color, (sx, sy), r + 6)

            # 拥堵闪烁 — 接近上限时背景变红
            crowd_ratio = s.passengerNm / limit
            if crowd_ratio >= 0.7:
                pulse = abs(math.sin(pygame.time.get_ticks() * 0.005)) * 0.5 + 0.5
                bg_r = int(r * (1.2 + 0.3 * pulse))
                bg_color = tuple(
                    int(c * pulse) for c in cfg.overcrowd_color
                )
                pygame.draw.circle(self.screen, bg_color, (sx, sy), bg_r + 4)

            # 白色填充
            shape_type = s.type
            draw_shape(self.screen, shape_type, sx, sy, r, cfg.station_fill)
            # 边框
            draw_shape(self.screen, shape_type, sx, sy, r, cfg.station_color, 3)

            # 高亮选中站点
            if s in self.selected_stations:
                draw_shape(self.screen, shape_type, sx, sy, r + 6, (255, 200, 0), 3)

            # 高亮 hover 站点
            if s is self.hover_station and s not in self.selected_stations:
                draw_shape(self.screen, shape_type, sx, sy, r + 4, (200, 200, 200), 2)

            # 乘客等候指示
            if s.passengerNm > 0:
                self._draw_station_passengers(s, sx, sy, r)

            # 站点 ID 和类别
            cat_label = CATEGORY_LABEL_CN.get(s.category, "") if s.category else ""
            label_text = f"{s.id}" if not cat_label else f"{s.id} {cat_label}"
            id_surf = self.font_small.render(label_text, True, cfg.text_color)
            self.screen.blit(id_surf, (sx - id_surf.get_width() // 2, sy + r + 4))

    def _draw_station_passengers(self, station, sx, sy, r):
        """在站点周围绘制等候乘客的目标形状"""
        cfg = self.config
        p_size = max(3, int(cfg.passenger_size * self.zoom))

        # 收集乘客目标形状
        shapes = []
        for p in station.passenger_list:
            dest_type = p.destination_station.type
            shapes.append(dest_type)

        # 环绕站点绘制小形状，最多显示12个
        max_display = min(len(shapes), 12)
        if max_display == 0:
            return

        start_angle = -math.pi / 2
        total_angle = math.pi * 1.6
        orbit_r = r + 8 + p_size

        for i in range(max_display):
            angle = start_angle + total_angle * i / max(max_display - 1, 1)
            px = sx + int(orbit_r * math.cos(angle))
            py = sy + int(orbit_r * math.sin(angle))
            draw_passenger_shape(self.screen, shapes[i], px, py, p_size, cfg.station_color)

        if len(shapes) > 12:
            more = self.font_small.render(f"+{len(shapes) - 12}", True, cfg.overcrowd_color)
            self.screen.blit(more, (sx + orbit_r + 4, sy - 6))

    # ---- 列车绘制 ----

    def _draw_trains(self):
        cfg = self.config
        for train in self.world.ti.trainBusyList:
            if train.line is None:
                continue

            # 计算列车屏幕位置
            pos = self._compute_train_position(train)
            if pos is None:
                continue

            tx, ty = pos
            color = self.get_line_color(train.line.number)
            size = int(cfg.train_size * self.zoom)

            # 列车主体 — 圆角矩形
            train_rect = pygame.Rect(tx - size, ty - size // 2, size * 2, size)
            pygame.draw.rect(self.screen, color, train_rect, border_radius=3)
            pygame.draw.rect(self.screen, (255, 255, 255), train_rect, 1, border_radius=3)

            # 方向指示 — 小三角
            direction = train.line.trainDirection.get(train, True)
            dx = size if direction else -size
            tri_pts = [
                (tx + dx, ty),
                (tx + dx - 4 * (1 if direction else -1), ty - 3),
                (tx + dx - 4 * (1 if direction else -1), ty + 3),
            ]
            pygame.draw.polygon(self.screen, (255, 255, 255), tri_pts)

            # 乘客数/容量
            pax = sum(c.currentNum for c in train.carriageList)
            cap = sum(c.capacity for c in train.carriageList)
            pax_text = self.font_small.render(f"{pax}/{cap}", True, (255, 255, 255))
            self.screen.blit(pax_text, (tx - pax_text.get_width() // 2, ty - pax_text.get_height() // 2))

            # 车厢节数 小标记
            n_car = len(train.carriageList)
            car_text = self.font_small.render(f"x{n_car}", True, (255, 255, 255))
            self.screen.blit(car_text, (tx + size + 2, ty - car_text.get_height() // 2))

    def _compute_train_position(self, train):
        """计算列车在屏幕上的位置，支持运行中的插值"""
        if train.status == 5:  # shunting — 不在站点
            return None
        if train.stationNow is None:
            return None

        if train.status == 4:  # running — 在两站之间插值
            next_st = train.line.nextStation(train) if train.line else None
            if next_st is None:
                return self.world_to_screen(train.stationNow.x, train.stationNow.y)

            # 计算运行进度
            total_time = train.nextStatusTime + countTrainRunningTime(
                train.stationNow, next_st, self.config
            )
            if total_time <= 0:
                progress = 1.0
            else:
                progress = 1.0 - (train.nextStatusTime / total_time)
            progress = max(0, min(1, progress))

            from_s = train.stationNow
            to_s = next_st
            ix = from_s.x + (to_s.x - from_s.x) * progress
            iy = from_s.y + (to_s.y - from_s.y) * progress
            return self.world_to_screen(ix, iy)

        if train.status == 6:  # waiting — 在当前站点等待前方空闲
            return self.world_to_screen(train.stationNow.x, train.stationNow.y)

        # 其他状态 — 在当前站点
        return self.world_to_screen(train.stationNow.x, train.stationNow.y)

    # ---- HUD ----

    def _draw_hud(self):
        cfg = self.config
        state = self.world.getGameState()
        metrics = state["metrics"]
        avail = state["available"]
        time_info = state.get("time_of_day", {})

        # 左上: 游戏指标
        y = 10
        period = time_info.get("period", "?")
        period_cn = {
            "night": "夜间", "morning_rush": "早高峰",
            "morning": "上午", "midday": "午间",
            "evening_rush": "晚高峰", "evening": "晚间",
            "late_night": "深夜",
        }.get(period, period)
        self._hud_text(f"Tick: {state['tick']}  Day {state['tick'] // cfg.day_length + 1} {period_cn}", 10, y); y += 22
        self._hud_text(f"Speed: x{self.sim_speed}  {'(||)' if self.paused else '(>)'}", 10, y); y += 22
        self._hud_text(f"Stations: {len(state['stations'])}  Lines: {len(state['lines'])}  Trains: {len(state['trains'])}", 10, y); y += 22

        # 拥堵警告
        at_risk = metrics.get("at_risk_stations", 0)
        if at_risk > 0:
            pulse = abs(math.sin(pygame.time.get_ticks() * 0.008))
            warn_color = (
                int(220 * (0.5 + 0.5 * pulse)),
                50,
                50,
            )
            self._hud_text(f"!! {at_risk} station(s) at risk !!", 10, y, color=warn_color)
            y += 22

        unconnected = metrics.get("unconnected_stations", 0)
        if unconnected > 0:
            self._hud_text(f"Unconnected: {unconnected}", 10, y, color=(180, 120, 40))
            y += 22

        self._hud_text(f"Max queue: {metrics.get('max_station_passengers', 0)}/{cfg.overcrowd_limit}", 10, y); y += 22
        self._hud_text(f"Avg wait: {metrics.get('avg_waiting_time', 0)}", 10, y); y += 22
        self._hud_text(f"Arrived: {metrics.get('total_arrived', 0)}", 10, y); y += 22

        # 右上: 可用资源
        rx = cfg.window_width - 180
        ry = 10
        self._hud_text("Available:", rx, ry); ry += 22
        self._hud_text(f"  Trains: {avail['trains']}", rx, ry); ry += 22
        self._hud_text(f"  Carriages: {avail['carriages']}", rx, ry); ry += 22
        self._hud_text(f"  Lines: {avail['lines_remaining']}", rx, ry)

        # 底部: 类别图例
        legend_y = cfg.window_height - 55
        legend_x = 10
        for cat in cfg.all_categories:
            cat_color = cfg.category_colors.get(cat, (200, 200, 200))
            label = cfg.category_labels.get(cat, cat)
            shape = cfg.category_shape_map.get(cat, "circle")
            # 画背景色圆
            pygame.draw.circle(self.screen, cat_color, (legend_x + 8, legend_y + 8), 8)
            # 画形状
            draw_shape(self.screen, shape, legend_x + 8, legend_y + 8, 6, cfg.station_color, 2)
            # 画文字
            lbl = self.font_small.render(label, True, cfg.text_color)
            self.screen.blit(lbl, (legend_x + 18, legend_y))
            legend_x += lbl.get_width() + 30

        # 底部: 操作提示
        bottom_y = cfg.window_height - 30
        help_text = "[Space] Pause  [+/-] Speed  [Scroll] Zoom  [Drag] Pan  [L] New line  [E] Extend line  [T] Add train  [C] Add carriage  [R-click] Quick connect  [R] Reset view"
        self._hud_text(help_text, 10, bottom_y, font=self.font_small, color=(120, 120, 120))

    def _hud_text(self, text, x, y, font=None, color=None):
        font = font or self.font
        color = color or self.config.text_color
        surf = font.render(text, True, color)
        # 半透明背景
        bg = pygame.Surface((surf.get_width() + 6, surf.get_height() + 2), pygame.SRCALPHA)
        bg.fill((245, 245, 235, 200))
        self.screen.blit(bg, (x - 3, y - 1))
        self.screen.blit(surf, (x, y))

    def _draw_pause_overlay(self):
        overlay = pygame.Surface((self.config.window_width, self.config.window_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 40))
        self.screen.blit(overlay, (0, 0))
        text = self.font_large.render("PAUSED", True, (80, 80, 80))
        self.screen.blit(text, (self.config.window_width // 2 - text.get_width() // 2, 60))

    # ---- 线路创建预览 ----

    def _draw_line_extension(self):
        if self.extending_line is None:
            return
        line = self.extending_line
        color = self.get_line_color(line.number)
        hint = f"Extending Line {line.number} — Click station to add, [Enter] confirm, [Esc] cancel"
        self._hud_text(hint, 10, self.config.window_height - 60, color=color)

        # 高亮该线路的所有站点
        for s in line.stationList:
            sx, sy = self.world_to_screen(s.x, s.y)
            r = int(self.config.station_radius * self.zoom) + 8
            draw_shape(self.screen, s.type, sx, sy, r, color, 3)

        # 如果 hover 了某个非线路站点，画预览连线
        if self.hover_station and self.hover_station not in line.stationList:
            last_s = line.stationList[-1]
            first_s = line.stationList[0]
            mx, my = pygame.mouse.get_pos()
            # 画到末尾的预览线
            lx, ly = self.world_to_screen(last_s.x, last_s.y)
            pygame.draw.line(self.screen, color, (lx, ly), (mx, my), 3)

    def _draw_game_over(self):
        overlay = pygame.Surface((self.config.window_width, self.config.window_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        self.screen.blit(overlay, (0, 0))

        state = self.world.getGameState()
        metrics = state["metrics"]

        cx = self.config.window_width // 2
        cy = self.config.window_height // 2

        # 标题
        title = self.font_large.render("GAME OVER", True, (255, 80, 80))
        self.screen.blit(title, (cx - title.get_width() // 2, cy - 80))

        # 统计
        lines = [
            f"Survived: {state['tick']} ticks",
            f"Passengers arrived: {metrics.get('total_arrived', 0)}",
            f"Stations: {len(state['stations'])}  Lines: {len(state['lines'])}",
            f"Max queue: {metrics.get('max_station_passengers', 0)}",
            "",
            "Press [Esc] to exit",
        ]
        for i, text in enumerate(lines):
            surf = self.font.render(text, True, (220, 220, 220))
            self.screen.blit(surf, (cx - surf.get_width() // 2, cy - 30 + i * 26))

    def _draw_line_creation(self):
        if not self.creating_line or not self.line_create_stations:
            return

        # 画选中的站点之间连线
        color = self.config.line_colors[len(self.world.metroLine) % len(self.config.line_colors)]
        pts = [self.world_to_screen(s.x, s.y) for s in self.line_create_stations]
        if len(pts) >= 2:
            pygame.draw.lines(self.screen, color, False, pts, 4)

        # 鼠标到最近站点的线
        mx, my = pygame.mouse.get_pos()
        if pts:
            pygame.draw.line(self.screen, (*color[:3],), pts[-1], (mx, my), 2)

        # 提示文字
        n = len(self.line_create_stations)
        hint = f"Creating line: {n} station(s) selected — Click station to add, [Enter] confirm, [Esc] cancel"
        self._hud_text(hint, 10, self.config.window_height - 60, color=color)

    # ---- 事件处理 ----

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.creating_line:
                        self.creating_line = False
                        self.line_create_stations = []
                        self.selected_stations = []
                        self.extending_line = None
                    else:
                        return False
                elif event.key == pygame.K_SPACE:
                    self.paused = not self.paused
                elif event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                    self.sim_speed = min(20, self.sim_speed + 1)
                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    self.sim_speed = max(1, self.sim_speed - 1)
                elif event.key == pygame.K_r:
                    self.offset_x = self.config.window_width // 2
                    self.offset_y = self.config.window_height // 2
                    self.zoom = 1.0
                elif event.key == pygame.K_l:
                    self._start_line_creation()
                elif event.key == pygame.K_e:
                    self._start_line_extension()
                elif event.key == pygame.K_t:
                    self._try_employ_train()
                elif event.key == pygame.K_c:
                    self._try_connect_carriage()
                elif event.key == pygame.K_RETURN:
                    self._finish_line_creation()
                    self._finish_line_extension()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # 左键
                    if self.creating_line:
                        self._click_station_for_line(event.pos)
                    elif self.extending_line is not None:
                        self._click_station_for_extension(event.pos)
                    else:
                        self.dragging = True
                        self.drag_start = event.pos
                        self.offset_start = (self.offset_x, self.offset_y)

                elif event.button == 3:  # 右键 — 快速操作菜单
                    self._right_click(event.pos)

                elif event.button == 4:  # 滚轮上
                    self._zoom_at(event.pos, 1.15)
                elif event.button == 5:  # 滚轮下
                    self._zoom_at(event.pos, 1 / 1.15)

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    self.dragging = False

            elif event.type == pygame.MOUSEMOTION:
                if self.dragging and not self.creating_line and self.extending_line is None:
                    dx = event.pos[0] - self.drag_start[0]
                    dy = event.pos[1] - self.drag_start[1]
                    self.offset_x = self.offset_start[0] + dx
                    self.offset_y = self.offset_start[1] + dy
                # Hover 检测
                self.hover_station = self._station_at_screen(event.pos)

        return True

    def _zoom_at(self, screen_pos, factor):
        mx, my = screen_pos
        wx, wy = self.screen_to_world(mx, my)
        self.zoom *= factor
        self.zoom = max(0.3, min(5.0, self.zoom))
        # 保持鼠标下方的世界坐标不变
        self.offset_x = mx - wx * self.zoom
        self.offset_y = my + wy * self.zoom

    def _station_at_screen(self, pos):
        """返回屏幕坐标最近的站点（在点击范围内）"""
        mx, my = pos
        best = None
        best_dist = float('inf')
        threshold = self.config.station_radius * self.zoom + 8
        for s in self.world.stations:
            sx, sy = self.world_to_screen(s.x, s.y)
            d = math.hypot(mx - sx, my - sy)
            if d < threshold and d < best_dist:
                best = s
                best_dist = d
        return best

    # ---- 线路延伸 ----

    def _start_line_extension(self):
        """进入线路延伸模式：如果有选中线路则延伸它，否则选第一条"""
        if not self.world.metroLine:
            return
        if self.extending_line is not None:
            # 切换到下一条线路
            lines = self.world.metroLine
            idx = lines.index(self.extending_line) if self.extending_line in lines else -1
            self.extending_line = lines[(idx + 1) % len(lines)]
        else:
            self.extending_line = self.world.metroLine[0]
        self.creating_line = False
        self.line_create_stations = []
        self.selected_stations = []

    def _click_station_for_extension(self, pos):
        """延伸模式下点击站点，添加到线路末端"""
        if self.extending_line is None:
            return
        station = self._station_at_screen(pos)
        if station is None:
            return
        if station in self.extending_line.stationList:
            return  # 已经在这条线路上
        self.world.playerLineExtension(self.extending_line, station, append=True)

    def _finish_line_extension(self):
        """结束线路延伸模式"""
        self.extending_line = None

    # ---- 右键菜单 ----

    def _right_click(self, pos):
        """右键快捷操作"""
        station = self._station_at_screen(pos)
        if station is None:
            return

        # 右键点击站点：如果站点不在任何线路上，尝试加入最缺站的线路
        lines_at = [l for l in self.world.metroLine if station in l.stationList]
        if not lines_at and self.world.metroLine:
            # 找最需要延伸的线路 — 选站最少且乘客多的
            best_line = None
            best_score = -1
            for line in self.world.metroLine:
                # 找最近的线路端点
                last_s = line.stationList[-1]
                first_s = line.stationList[0]
                d_last = math.hypot(station.x - last_s.x, station.y - last_s.y)
                d_first = math.hypot(station.x - first_s.x, station.y - first_s.y)
                d_min = min(d_last, d_first)
                pax = sum(s.passengerNm for s in line.stationList)
                score = pax / max(1, d_min / 100)
                if score > best_score:
                    best_score = score
                    best_line = line

            if best_line:
                # 判断加在首还是尾
                last_s = best_line.stationList[-1]
                first_s = best_line.stationList[0]
                d_last = math.hypot(station.x - last_s.x, station.y - last_s.y)
                d_first = math.hypot(station.x - first_s.x, station.y - first_s.y)
                append = d_last <= d_first
                self.world.playerLineExtension(best_line, station, append=append)

    # ---- 线路创建 ----

    def _start_line_creation(self):
        if len(self.world.metroLine) >= self.config.max_lines:
            return
        self.creating_line = True
        self.line_create_stations = []
        self.selected_stations = []

    def _click_station_for_line(self, pos):
        station = self._station_at_screen(pos)
        if station is None:
            return
        if station in self.line_create_stations:
            # 再次点击取消选中的站点
            idx = self.line_create_stations.index(station)
            self.line_create_stations = self.line_create_stations[:idx]
            self.selected_stations = list(self.line_create_stations)
            return
        self.line_create_stations.append(station)
        self.selected_stations = list(self.line_create_stations)

    def _finish_line_creation(self):
        if not self.creating_line:
            return
        if len(self.line_create_stations) >= 2:
            new_line = self.world.playerNewLine(self.line_create_stations)
            if new_line:
                # 自动分配一列车到新线路
                if self.world.ti.trainAbleList:
                    first_s = self.line_create_stations[0]
                    self.world.playerEmployTrain(new_line, first_s, True)
                    # 自动挂车厢
                    tr = self.world.ti.trainBusyList[-1]
                    self.world.playerConnectCarriage(tr)
                self._rebuild_line_colors()
        self.creating_line = False
        self.line_create_stations = []
        self.selected_stations = []

    # ---- 列车/车厢操作 ----

    def _try_employ_train(self):
        """将空闲列车分配到选中线路的第一个站点"""
        if not self.world.ti.trainAbleList:
            return
        if not self.world.metroLine:
            return
        # 分配到乘客最多的线路
        best_line = None
        best_need = -1
        for line in self.world.metroLine:
            total_pax = sum(s.passengerNm for s in line.stationList)
            need = total_pax / max(1, line.trainNm)
            if need > best_need:
                best_need = need
                best_line = line
        if best_line and best_line.stationList:
            s = best_line.stationList[0]
            self.world.playerEmployTrain(best_line, s, True)

    def _try_connect_carriage(self):
        """给最短车厢数的列车加一节车厢"""
        if not self.world.ti.carriageAbleList:
            return
        best_train = None
        min_car = float('inf')
        for tr in self.world.ti.trainBusyList:
            if len(tr.carriageList) < min_car:
                min_car = len(tr.carriageList)
                best_train = tr
        if best_train:
            self.world.playerConnectCarriage(best_train)

    # ---- 主循环 (独立运行模式) ----

    def run(self, max_ticks=500):
        """可视化主循环"""
        self.world.setup()
        running = True
        _original_stdout = sys.stdout

        while running:
            # 事件
            running = self.handle_events()

            # 模拟 (抑制控制台输出)
            if not self.paused and not self.world.game_over:
                sys.stdout = io.StringIO()
                try:
                    for _ in range(self.sim_speed):
                        if self.world.game_over:
                            break
                        self.world.updateOneTick()
                finally:
                    sys.stdout = _original_stdout

            # 绘制
            self.draw()
            self.clock.tick(self.config.fps)

        pygame.quit()
