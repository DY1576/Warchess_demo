"""
piece.py - 棋子类定义
"""

from Constant import PIECE_STATS, PieceType, PIECE_DISPLAY_TEXT


class Piece:
    """棋子基类 - 所有棋子的父类"""

    def __init__(self, piece_type, owner, row, col):
        self.piece_type = piece_type
        self.owner = owner          # 'player' 或 'ai'
        self.row = row
        self.col = col

        # 战斗状态
        self.is_in_battle = False      # 是否作为主将在战斗中
        self.is_supporting = False     # 是否在支援某场战斗
        self.supporting_battle = None  # 正在支援的 Battle 引用

        # 行动状态（每回合重置）
        self.has_acted_this_turn = False      # 本回合是否已行动（步兵/炮兵/首都用）
        self.has_moved_this_turn = False      # 本回合是否已移动（骑兵专用）
        self.has_attacked_this_turn = False   # 本回合是否已攻击（骑兵专用）
        self.actions_used_this_turn = 0       # 本回合已行动次数（骑兵专用）

        # 从常量表读取属性
        stats = PIECE_STATS[piece_type]
        self.hp = stats[0]
        self.max_hp = stats[0]
        self.attack = stats[1]
        self.defense = stats[2]
        self.support = stats[3]
        self.movement = stats[4]

    def get_display_name(self):
        """返回棋子中文名称"""
        return PIECE_DISPLAY_TEXT.get(self.piece_type, "?")

    def take_damage(self, damage):
        """受到伤害，返回是否死亡"""
        self.hp -= damage
        return self.hp <= 0

    def can_act(self):
        """
        检查本回合是否还能行动（非骑兵专用）
        骑兵使用单独的检查逻辑
        """
        if self.is_in_battle or self.is_supporting:
            return False
        if self.piece_type == PieceType.CAPITAL:
            return True   # 首都可以支援
        return not self.has_acted_this_turn

    def can_move(self):
        """检查是否可以移动"""
        if self.is_in_battle or self.is_supporting:
            return False
        if self.piece_type == PieceType.CAPITAL:
            return False
        if not self.can_act():
            return False
        # 骑兵如果已攻击，不能再移动
        if self.piece_type == PieceType.CAVALRY and self.has_attacked_this_turn:
            return False
        return True

    def can_attack(self):
        """检查是否可以攻击（只有骑兵能主动攻击）"""
        if self.piece_type != PieceType.CAVALRY:
            return False
        if self.is_in_battle or self.is_supporting:
            return False
        if self.actions_used_this_turn >= 2:
            return False
        if self.has_attacked_this_turn:
            return False
        return True

    def can_support(self):
        """检查是否可以主动支援他人"""
        if self.is_in_battle or self.is_supporting:
            return False
        if not self.can_act():
            return False
        # 骑兵如果已攻击，不能再支援
        if self.piece_type == PieceType.CAVALRY and self.has_attacked_this_turn:
            return False
        return True

    def can_retreat(self):
        """检查是否可以撤退（主将专用，由 Battle 类具体判断）"""
        return self.is_in_battle

    def can_move_to(self, target_row, target_col, board):
        """检查是否可以移动到目标位置"""
        if not self.can_move():
            return False
        if not board.is_valid_position(target_row, target_col):
            return False
        if board.get_piece_at(target_row, target_col) is not None:
            return False
        distance = abs(target_row - self.row) + abs(target_col - self.col)
        if distance > self.movement or distance == 0:
            return False
        if board.is_path_blocked(self.row, self.col, target_row, target_col):
            return False
        return True

    def can_bombard(self, target_row, target_col, board):
        """检查是否可以远程轰炸目标（炮兵专用）"""
        if self.piece_type != PieceType.ARTILLERY:
            return False
        if self.is_in_battle or self.is_supporting:
            return False
        if self.has_acted_this_turn:
            return False
        target = board.get_piece_at(target_row, target_col)
        if target is None or target.owner == self.owner:
            return False
        distance = abs(target_row - self.row) + abs(target_col - self.col)
        if distance > 2 or distance == 0:
            return False
        return True

    def bombard(self, target):
        """执行远程轰炸，返回伤害值（炮兵专用）"""
        if self.piece_type != PieceType.ARTILLERY:
            return 0
        if target.piece_type == PieceType.ARTILLERY:
            return 0   # 轰炸炮兵目标伤害为0
        return 3       # 3点伤害

    def get_support_range(self):
        """获取支援范围"""
        if self.piece_type == PieceType.ARTILLERY:
            return 2
        return 1

    def get_text_color(self):
        """获取棋子表面文字颜色"""
        if self.owner == 'player':
            # 玩家棋子是黑色，用白色文字
            return (255, 255, 255)
        else:
            # AI棋子是白色，用黑色文字
            return (0, 0, 0)

    def __repr__(self):
        return f"{self.get_display_name()}({self.owner}, {self.row}, {self.col}, HP={self.hp})"


class Infantry(Piece):
    """步兵 - 基础单位，可移动或触发战斗"""
    def __init__(self, owner, row, col):
        super().__init__(PieceType.INFANTRY, owner, row, col)


class Cavalry(Piece):
    """
    骑兵 - 每回合最多2次行动
    行动组合：
    - 移动 + 移动
    - 移动 + 攻击
    - 移动 + 支援
    - 直接攻击（不移动）
    - 直接支援（不移动）
    - 只移动一次
    """
    def __init__(self, owner, row, col):
        super().__init__(PieceType.CAVALRY, owner, row, col)

    def can_act(self):
        """骑兵可行动条件：未达2次上限，且不在战斗/支援中"""
        if self.is_in_battle or self.is_supporting:
            return False
        return self.actions_used_this_turn < 2

    def can_move(self):
        """骑兵可移动：未达2次上限，不在战斗/支援中，且未攻击过"""
        if self.is_in_battle or self.is_supporting:
            return False
        if self.actions_used_this_turn >= 2:
            return False
        if self.has_attacked_this_turn:
            return False
        return True

    def can_attack(self):
        """骑兵可攻击：未达2次上限，不在战斗/支援中，且未攻击过"""
        if self.is_in_battle or self.is_supporting:
            return False
        if self.actions_used_this_turn >= 2:
            return False
        if self.has_attacked_this_turn:
            return False
        return True

    def can_support(self):
        """骑兵可支援：未达2次上限，不在战斗/支援中，且未攻击过"""
        if self.is_in_battle or self.is_supporting:
            return False
        if self.actions_used_this_turn >= 2:
            return False
        if self.has_attacked_this_turn:
            return False
        return True

    def can_move_to(self, target_row, target_col, board):
        """骑兵移动检查"""
        if not self.can_move():
            return False
        if not board.is_valid_position(target_row, target_col):
            return False
        if board.get_piece_at(target_row, target_col) is not None:
            return False
        distance = abs(target_row - self.row) + abs(target_col - self.col)
        if distance > self.movement or distance == 0:
            return False
        if board.is_path_blocked(self.row, self.col, target_row, target_col):
            return False
        return True


class Artillery(Piece):
    """
    炮兵 - 特殊单位
    1. 可以远程轰炸（射程2，3点伤害）
    2. 轰炸炮兵目标无效（伤害0）
    3. 被攻击时直接死亡（不进入战斗）
    4. 支援范围2
    5. 移动力1
    6. 每回合1次行动
    """
    def __init__(self, owner, row, col):
        super().__init__(PieceType.ARTILLERY, owner, row, col)

    def can_move(self):
        """炮兵移动判断"""
        if self.is_in_battle or self.is_supporting:
            return False
        if self.has_acted_this_turn:
            return False
        return True


class Capital(Piece):
    """
    首都 - 特殊单位
    1. 不能移动
    2. 不能主动攻击
    3. 可以支援相邻战斗（can_act返回True）
    4. 被攻击时作为主将进入战斗
    5. 被摧毁则游戏结束
    """
    def __init__(self, owner, row, col):
        super().__init__(PieceType.CAPITAL, owner, row, col)
        self.hp = 10
        self.max_hp = 10
        self.attack = 0
        self.defense = 2
        self.support = 2
        self.movement = 0

    def can_act(self):
        """首都可以行动（支援）"""
        if self.is_in_battle or self.is_supporting:
            return False
        return True

    def can_move(self):
        """首都不能移动"""
        return False

    def can_attack(self):
        """首都不能攻击"""
        return False

    def can_support(self):
        """首都可以支援"""
        if self.is_in_battle or self.is_supporting:
            return False
        return True

    def can_move_to(self, target_row, target_col, board):
        return False