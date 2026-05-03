# station.py — 站点模块
#
# 本文件定义了地铁站点的功能类别常量和站点类。
# 站点类别包括：居民区、商业区、办公区、医院、景区、学校等。

# 站点功能类别常量
CATEGORY_RESIDENTIAL = "residential"   # 居民区
CATEGORY_COMMERCIAL = "commercial"     # 商业区
CATEGORY_OFFICE = "office"             # 办公写字楼区
CATEGORY_HOSPITAL = "hospital"        # 医院
CATEGORY_SCENIC = "scenic"             # 景区
CATEGORY_SCHOOL = "school"             # 学校

ALL_CATEGORIES = [
    CATEGORY_RESIDENTIAL,
    CATEGORY_COMMERCIAL,
    CATEGORY_OFFICE,
    CATEGORY_HOSPITAL,
    CATEGORY_SCENIC,
    CATEGORY_SCHOOL,
]

# 类别 → 形状 映射（用于可视化区分）
CATEGORY_SHAPE_MAP = {
    CATEGORY_RESIDENTIAL: "triangle",
    CATEGORY_COMMERCIAL: "diamond",
    CATEGORY_OFFICE: "square",
    CATEGORY_HOSPITAL: "pentagon",
    CATEGORY_SCENIC: "star",
    CATEGORY_SCHOOL: "circle",
}

# 类别中文名
CATEGORY_LABEL_CN = {
    CATEGORY_RESIDENTIAL: "居民区",
    CATEGORY_COMMERCIAL: "商业区",
    CATEGORY_OFFICE: "办公区",
    CATEGORY_HOSPITAL: "医院",
    CATEGORY_SCENIC: "景区",
    CATEGORY_SCHOOL: "学校",
}


class station:
    """站点类，表示地铁系统中的一个站点"""

    def __init__(self, id, type, x, y, category=None):
        """初始化站点

        参数:
            id: 站点唯一标识符
            type: 站点视觉形状 (circle, triangle, square, diamond, star, pentagon)
            x: 站点x坐标
            y: 站点y坐标
            category: 站点功能类别，默认为None时根据type反推
        """
        self.id = id
        self.type = type  # 视觉形状 (circle, triangle, square, diamond, star, pentagon)
        self.category = category or CATEGORY_SHAPE_MAPReverse.get(type)  # 功能类别
        self.x = x
        self.y = y
        self.passengerNm = 0
        self.passenger_list = []  # 存储等待的乘客对象
        self.connections = []  # 存储连接的Station对象

    def __str__(self):
        """返回站点的字符串表示

        返回:
            str: 站点信息字符串
        """
        cat = self.category or "?"
        return f"<STATION/ID:{self.id}/{cat}/{self.type} / x:{self.x} y:{self.y} /> "

    def printStation(self):
        """打印站点详细信息"""
        cat = self.category or "?"
        print(f"Category:{cat} Type:{self.type} x:{self.x} y:{self.y}", end=" /")


# 形状 → 类别 反向映射（兼容旧代码只传 type 的情况）
CATEGORY_SHAPE_MAPReverse = {v: k for k, v in CATEGORY_SHAPE_MAP.items()}
