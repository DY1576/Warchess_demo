"""
constants.py - 全局常量定义
"""

# ============ 窗口设置 ============

WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 800
FPS = 60

# ============ 棋盘设置 ============

BOARD_SIZE = 11
CELL_SIZE = 50
BOARD_OFFSET_X = 200
BOARD_OFFSET_Y = 100

# ============ 颜色定义 ============

COLORS = {
    "WHITE": (255, 255, 255),
    "BLACK": (0, 0, 0),
    "GRAY": (128, 128, 128),
    "LIGHT_GRAY": (200, 200, 200),
    "DARK_GRAY": (64, 64, 64),
    "RED": (255, 0, 0),
    "GREEN": (0, 255, 0),
    "BLUE": (0, 0, 255),
    "CYAN": (0, 255, 255),
    "YELLOW": (255, 255, 0),
    "ORANGE": (255, 165, 0),
    "PURPLE": (128, 0, 128),
    "BROWN": (139, 69, 19),
    "BEIGE": (240, 230, 210),
    "DARK_BEIGE": (180, 160, 140),
}

# 棋子颜色（黑 vs 白）
PLAYER_COLOR = (0, 0, 0)        # 玩家默认黑色
AI_COLOR = (255, 255, 255)      # AI默认白色

# 棋子描边颜色（白色棋子用黑边，黑色棋子用白边）
OUTLINE_COLOR = (255, 255, 255)  # 黑色棋子的描边
AI_OUTLINE_COLOR = (0, 0, 0)     # 白色棋子的描边

# ============ 棋子类型枚举 ============

class PieceType:
    INFANTRY = "infantry"
    CAVALRY = "cavalry"
    ARTILLERY = "artillery"
    CAPITAL = "capital"

# ============ 棋子属性 ============
# 格式: (HP, Attack, Defense, Support, Movement)

PIECE_STATS = {
    PieceType.INFANTRY:  (2, 1, 2, 1, 2),
    PieceType.CAVALRY:   (3, 3, 2, 1, 3),
    PieceType.ARTILLERY: (1, 3, 1, 3, 1),
    PieceType.CAPITAL:   (10, 0, 2, 2, 0),
}

# 棋子显示文字
PIECE_DISPLAY_TEXT = {
    PieceType.INFANTRY: "步",
    PieceType.CAVALRY: "骑",
    PieceType.ARTILLERY: "炮",
    PieceType.CAPITAL: "首",
}

# ============ 默认初始布局 ============
# 0 = 空, 1 = 步兵, 2 = 骑兵, 3 = 炮兵, 4 = 首都
# 行0-4为AI方（上方），行6-10为玩家方（下方）

INITIAL_LAYOUT = [
    [2, 1, 1, 1, 1, 4, 1, 1, 1, 1, 2],
    [0, 2, 1, 1, 3, 1, 3, 1, 1, 2, 0],
    [0, 0, 0, 3, 1, 1, 1, 3, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 3, 1, 1, 1, 3, 0, 0, 0],
    [0, 2, 1, 1, 3, 1, 3, 1, 1, 2, 0],
    [2, 1, 1, 1, 1, 4, 1, 1, 1, 1, 2],
]