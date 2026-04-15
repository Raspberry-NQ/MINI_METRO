# city_generator.py — 生成初始城市站点布局
import random
from station import (
    station, CATEGORY_SHAPE_MAP,
    CATEGORY_RESIDENTIAL, CATEGORY_COMMERCIAL, CATEGORY_OFFICE,
    CATEGORY_HOSPITAL, CATEGORY_SCENIC, CATEGORY_SCHOOL,
)


def generate_city(config, id_start=0):
    """生成城市站点列表

    Args:
        config: GameConfig 实例
        id_start: 站点 ID 起始值

    Returns:
        list[station]: 生成的站点列表
    """
    cfg = config
    next_id = id_start

    # 确定各类别的聚集中心
    centers = _generate_cluster_centers(cfg)

    all_stations = []

    for category in cfg.all_categories:
        count_range = cfg.city_cluster_count_ranges.get(category, (2, 3))
        count = random.randint(*count_range)
        cx, cy = centers[category]

        for _ in range(count):
            for attempt in range(30):
                x = cx + random.gauss(0, cfg.city_cluster_radius * 0.4)
                y = cy + random.gauss(0, cfg.city_cluster_radius * 0.4)
                # 裁剪到城市范围
                x = max(cfg.city_x_range[0], min(cfg.city_x_range[1], x))
                y = max(cfg.city_y_range[0], min(cfg.city_y_range[1], y))

                # 检查与已有站点最小距离
                too_close = any(
                    ((s.x - x) ** 2 + (s.y - y) ** 2) ** 0.5 < cfg.city_min_distance
                    for s in all_stations
                )
                if not too_close:
                    next_id += 1
                    shape = CATEGORY_SHAPE_MAP[category]
                    s = station(next_id, shape, round(x), round(y), category=category)
                    all_stations.append(s)
                    break

    return all_stations


def _generate_cluster_centers(config):
    """生成各类别的聚集中心坐标

    策略: 将城市空间大致分为区域，让居民区在一侧，办公区在中间，商业区分散等。
    如果 config.city_cluster_centers 已设置，直接使用。
    """
    cfg = config

    if cfg.city_cluster_centers:
        return dict(cfg.city_cluster_centers)

    # 默认布局: 利用城市空间的自然分区
    cx = (cfg.city_x_range[0] + cfg.city_x_range[1]) / 2
    cy = (cfg.city_y_range[0] + cfg.city_y_range[1]) / 2
    half_x = (cfg.city_x_range[1] - cfg.city_x_range[0]) / 2 * 0.6
    half_y = (cfg.city_y_range[1] - cfg.city_y_range[0]) / 2 * 0.6

    return {
        # 居民区: 偏左（郊区）
        CATEGORY_RESIDENTIAL: (cx - half_x * 0.6 + random.gauss(0, 30),
                                cy + random.gauss(0, 40)),
        # 商业区: 中心偏右上
        CATEGORY_COMMERCIAL: (cx + half_x * 0.3 + random.gauss(0, 20),
                               cy + half_y * 0.4 + random.gauss(0, 20)),
        # 办公区: 中心偏右
        CATEGORY_OFFICE: (cx + half_x * 0.5 + random.gauss(0, 25),
                          cy + random.gauss(0, 30)),
        # 医院: 中心附近
        CATEGORY_HOSPITAL: (cx + random.gauss(0, 40),
                            cy - half_y * 0.3 + random.gauss(0, 30)),
        # 景区: 偏上方
        CATEGORY_SCENIC: (cx - half_x * 0.3 + random.gauss(0, 30),
                          cy + half_y * 0.5 + random.gauss(0, 20)),
        # 学校: 居民区和办公区之间
        CATEGORY_SCHOOL: (cx - half_x * 0.1 + random.gauss(0, 35),
                          cy + half_y * 0.2 + random.gauss(0, 30)),
    }
