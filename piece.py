"""
piece.py - 棋子类定义
"""

from Constant import PIECE_STATS, PieceType, PIECE_DISPLAY_TEXT

class Piece:
    """棋子基类 - 所有棋子的父类"""
    def __init__(self, piece_type, owner, row, col):
        self.piece_type = piece_type
        self.owner = owner
        self.row = row
        self.col = col

        # 战斗状态
        self.is_in_battle = False
        self.is_supporting = False
        self.supporting_battle = None

        # 行动状态（每回合重置）
        self.has_acted_this_turn = False
        self.has_moved_this_turn = False
        self.has_attacked_this_turn = False
        self.actions_used_this_turn = 0

        # 从常量表读取属性
        stats = PIECE_STATS[piece_type]
        self.hp = stats[0]
        self.max_hp = stats[0]
        self.attack = stats[1]
        self.defense = stats[2]
        self.support = stats[3]
        self.movement = stats[4]

    @property
    def is_busy(self):
        """是否因战斗或支援被锁定"""
        return self.is_in_battle or self.is_supporting

    def get_display_name(self):
        """返回棋子中文名称"""
        return PIECE_DISPLAY_TEXT.get(self.piece_type, "?")

    def take_damage(self, damage):
        """受到伤害，返回是否死亡"""
        self.hp -= damage
        return self.hp <= 0

    def can_act(self):
        """检查本回合是否还能行动"""
        if self.is_busy: 
            return False
        return not self.has_acted_this_turn

    def can_move(self):
        """检查是否可以移动"""
        if self.is_busy or self.piece_type == PieceType.CAPITAL: 
            return False
        return self.can_act()

    def can_attack(self):
        """默认只有骑兵能主动攻击，其他兵种在子类中不覆盖则为False"""
        return False

    def can_support(self):
        """检查是否可以主动支援他人"""
        if self.is_busy or self.piece_type == PieceType.CAPITAL: 
            return False
        return self.can_act()

    def can_retreat(self):
        """检查是否可以撤退"""
        return self.is_in_battle

    def can_move_to(self, target_row, target_col, board):
        """检查是否可以移动到目标位置"""
        if not self.can_move() or not board.is_valid_position(target_row, target_col): 
            return False
        if board.get_piece_at(target_row, target_col) is not None: 
            return False
        distance = abs(target_row - self.row) + abs(target_col - self.col)
        if distance > self.movement or distance == 0: 
            return False
        return not board.is_path_blocked(self.row, self.col, target_row, target_col)
    
    def can_bombard(self, target_row, target_col, board):
        """检查是否可以远程轰炸目标（炮兵专用）"""
        if self.piece_type != PieceType.ARTILLERY: 
            return False
        if self.is_busy: 
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
            return 0
        return 3

    def get_support_range(self):
        """获取支援范围"""
        if self.piece_type == PieceType.ARTILLERY: 
            return 2
        return 1

    def get_text_color(self):
        """获取棋子表面文字颜色"""
        if self.owner == 'player':
            return (255, 255, 255)
        else:
            return (0, 0, 0)

    def __repr__(self):
        return f"{self.get_display_name()}({self.owner}, {self.row}, {self.col}, HP={self.hp})"


class Infantry(Piece):
    """步兵"""
    def __init__(self, owner, row, col):
        super().__init__(PieceType.INFANTRY, owner, row, col)


class Cavalry(Piece):
    """骑兵"""
    def __init__(self, owner, row, col):
        super().__init__(PieceType.CAVALRY, owner, row, col)

    def can_act(self):
        if self.is_busy: 
            return False
        return self.actions_used_this_turn < 2

    def can_move(self):
        return self.can_act() and not self.has_attacked_this_turn

    def can_attack(self):
        return self.can_act() and not self.has_attacked_this_turn

    def can_support(self):
        return self.can_act() and not self.has_attacked_this_turn


class Artillery(Piece):
    """炮兵"""
    def __init__(self, owner, row, col):
        super().__init__(PieceType.ARTILLERY, owner, row, col)


class Capital(Piece):
    """首都"""
    def __init__(self, owner, row, col):
        super().__init__(PieceType.CAPITAL, owner, row, col)
        
    def can_act(self):
        return not self.is_busy

    def can_support(self):
        return self.can_act()