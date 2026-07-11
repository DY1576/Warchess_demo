"""
board.py - 棋盘管理
"""

from Constant import BOARD_SIZE, INITIAL_LAYOUT, PieceType
from piece import Infantry, Cavalry, Artillery, Capital


class Board:
    """
    棋盘类 - 管理 11x11 棋盘上所有棋子的位置和移动
    """

    def __init__(self, player_color='black'):
        # 11x11 网格，存储 Piece 对象或 None
        self.grid = [[None for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]

        # 棋子列表（方便遍历）
        self.player_pieces = []   # 玩家棋子
        self.ai_pieces = []       # AI棋子
        self.all_pieces = []      # 所有棋子

        self.player_color = player_color  # 'black' 或 'white'

        self._initialize_board()

    # ============ 初始化 ============

    def _initialize_board(self):
        """根据 INITIAL_LAYOUT 初始化棋盘"""
        type_map = {
            1: Infantry,
            2: Cavalry,
            3: Artillery,
            4: Capital,
        }

        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                value = INITIAL_LAYOUT[row][col]
                if value == 0:
                    continue

                # 行0-4为AI方（上方），行6-10为玩家方（下方）
                if row <= 4:
                    owner = 'ai'
                elif row >= 6:
                    owner = 'player'
                else:
                    # 中间行（5）通常为空，但安全处理
                    owner = 'player' if row >= 5 else 'ai'

                piece_class = type_map[value]
                piece = piece_class(owner, row, col)
                self.place_piece(piece, row, col)

    # ============ 基础操作 ============

    def place_piece(self, piece, row, col):
        """将棋子放置到指定位置"""
        if not self.is_valid_position(row, col):
            return False

        # 如果该位置已有棋子，先移除
        existing = self.grid[row][col]
        if existing is not None:
            self.remove_piece(existing)

        self.grid[row][col] = piece
        piece.row = row
        piece.col = col

        if piece not in self.all_pieces:
            self.all_pieces.append(piece)
            if piece.owner == 'player':
                self.player_pieces.append(piece)
            else:
                self.ai_pieces.append(piece)

        return True

    def remove_piece(self, piece):
        """从棋盘移除棋子"""
        if piece is None:
            return False

        row, col = piece.row, piece.col

        # 从网格移除
        if self.is_valid_position(row, col) and self.grid[row][col] == piece:
            self.grid[row][col] = None

        # 从所有列表中移除
        if piece in self.all_pieces:
            self.all_pieces.remove(piece)
        if piece in self.player_pieces:
            self.player_pieces.remove(piece)
        if piece in self.ai_pieces:
            self.ai_pieces.remove(piece)

        return True

    def get_piece_at(self, row, col):
        """获取指定位置的棋子"""
        if not self.is_valid_position(row, col):
            return None
        return self.grid[row][col]

    def is_valid_position(self, row, col):
        """检查位置是否在棋盘内"""
        return 0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE

    def is_occupied(self, row, col):
        """检查位置是否被占据"""
        return self.get_piece_at(row, col) is not None

    def is_empty(self, row, col):
        """检查位置是否为空"""
        return not self.is_occupied(row, col)

    # ============ 移动操作 ============

    def move_piece(self, piece, target_row, target_col):
        """
        移动棋子到目标位置
        返回: bool 是否成功
        """
        if piece is None:
            return False

        # 检查目标位置是否有效
        if not self.is_valid_position(target_row, target_col):
            return False

        # 检查目标位置是否被占据
        if self.is_occupied(target_row, target_col):
            # 检查是否是自己（移动到同一位置）
            target_piece = self.get_piece_at(target_row, target_col)
            if target_piece == piece:
                return False
            # 目标被其他棋子占据，不能移动
            return False

        # 检查路径是否被阻挡
        if self.is_path_blocked(piece.row, piece.col, target_row, target_col):
            return False

        # 从原位置移除
        self.grid[piece.row][piece.col] = None

        # 放置到新位置
        self.grid[target_row][target_col] = piece
        piece.row = target_row
        piece.col = target_col

        # 更新移动状态
        piece.has_moved_this_turn = True
        piece.has_acted_this_turn = True
        piece.actions_used_this_turn += 1

        return True

    def move_piece_force(self, piece, target_row, target_col):
        """
        强制移动棋子（覆盖目标位置，用于战斗中的覆盖）
        警告：此方法会删除目标位置的棋子
        返回: bool 是否成功
        """
        if piece is None:
            return False

        if not self.is_valid_position(target_row, target_col):
            return False

        # 检查目标位置是否有棋子（如果有，移除它）
        target = self.get_piece_at(target_row, target_col)
        if target is not None and target != piece:
            self.remove_piece(target)

        # 从原位置移除
        self.grid[piece.row][piece.col] = None

        # 放置到新位置
        self.grid[target_row][target_col] = piece
        piece.row = target_row
        piece.col = target_col

        piece.has_moved_this_turn = True
        piece.has_acted_this_turn = True
        piece.actions_used_this_turn += 1

        return True

    # ============ 路径检查 ============

    def is_path_blocked(self, start_row, start_col, end_row, end_col):
        """
        检查从起点到终点的曼哈顿路径是否被阻挡
        检查路径上的所有中间格子（不包括起点，包括终点）
        返回: True 表示路径被阻挡
        """
        # 如果是同一个位置，视为无路径
        if start_row == end_row and start_col == end_col:
            return True

        # 检查终点是否被占据（调用者通常已经检查过，但防御性检查）
        if self.is_occupied(end_row, end_col):
            return True

        current_row, current_col = start_row, start_col

        # 计算步进方向
        step_row = 1 if end_row > start_row else -1 if end_row < start_row else 0
        step_col = 1 if end_col > start_col else -1 if end_col < start_col else 0

        # 先沿行方向移动
        while current_row != end_row:
            current_row += step_row
            # 检查中间格子（不包括起点）
            if current_row != start_row or current_col != start_col:
                if self.is_occupied(current_row, current_col):
                    return True

        # 再沿列方向移动
        while current_col != end_col:
            current_col += step_col
            # 检查中间格子（不包括起点）
            if current_row != start_row or current_col != start_col:
                if self.is_occupied(current_row, current_col):
                    return True

        return False

    def get_valid_moves_for_piece(self, piece):
        """获取棋子的所有有效移动目标"""
        if piece is None:
            return []

        if not piece.can_move():
            return []

        valid_moves = []

        for dr in range(-piece.movement, piece.movement + 1):
            for dc in range(-piece.movement, piece.movement + 1):
                # 跳过原地
                if dr == 0 and dc == 0:
                    continue
                # 跳过超出曼哈顿距离的位置
                if abs(dr) + abs(dc) > piece.movement:
                    continue

                nr, nc = piece.row + dr, piece.col + dc

                # 检查位置有效性
                if not self.is_valid_position(nr, nc):
                    continue

                # 检查是否被占据
                if self.is_occupied(nr, nc):
                    continue

                # 检查路径是否被阻挡
                if self.is_path_blocked(piece.row, piece.col, nr, nc):
                    continue

                valid_moves.append((nr, nc))

        return valid_moves

    def get_valid_attack_targets(self, piece):
        """
        获取棋子的有效攻击目标（骑兵专用）
        返回: List[(target_piece, target_row, target_col)]
        """
        if piece is None:
            return []

        if piece.piece_type != PieceType.CAVALRY:
            return []

        if not piece.can_attack():
            return []

        targets = []
        for row, col in self.get_adjacent_positions(piece.row, piece.col):
            target = self.get_piece_at(row, col)
            if target is not None and target.owner != piece.owner:
                targets.append((target, row, col))

        return targets

    def get_valid_bombard_targets(self, piece):
        """
        获取炮兵的有效轰炸目标
        返回: List[(target_piece, target_row, target_col)]
        """
        if piece is None:
            return []

        if piece.piece_type != PieceType.ARTILLERY:
            return []

        if not piece.can_act():
            return []

        targets = []
        # 获取范围内所有敌方棋子（曼哈顿距离 ≤ 2）
        for row in range(piece.row - 2, piece.row + 3):
            for col in range(piece.col - 2, piece.col + 3):
                if not self.is_valid_position(row, col):
                    continue
                if row == piece.row and col == piece.col:
                    continue
                distance = abs(row - piece.row) + abs(col - piece.col)
                if distance > 2:
                    continue
                target = self.get_piece_at(row, col)
                if target is not None and target.owner != piece.owner:
                    targets.append((target, row, col))

        return targets

    # ============ 相邻和范围查找 ============

    def get_adjacent_positions(self, row, col):
        """获取相邻的四个位置（上下左右）"""
        positions = []
        for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nr, nc = row + dr, col + dc
            if self.is_valid_position(nr, nc):
                positions.append((nr, nc))
        return positions

    def get_adjacent_enemy_pieces(self, piece):
        """获取与指定棋子相邻的敌方棋子"""
        if piece is None:
            return []

        enemies = []
        for row, col in self.get_adjacent_positions(piece.row, piece.col):
            target = self.get_piece_at(row, col)
            if target is not None and target.owner != piece.owner:
                enemies.append(target)

        return enemies

    def get_pieces_in_range(self, row, col, range_limit, owner=None):
        """
        获取范围内（曼哈顿距离）的所有棋子
        owner: None 表示所有，'player' 或 'ai' 表示特定阵营
        """
        pieces = []
        for piece in self.all_pieces:
            distance = abs(piece.row - row) + abs(piece.col - col)
            if distance <= range_limit:
                if owner is None or piece.owner == owner:
                    pieces.append(piece)
        return pieces

    def get_adjacent_pieces(self, row, col, owner=None):
        """获取相邻位置的棋子"""
        return self.get_pieces_in_range(row, col, 1, owner)

    # ============ 支援相关 ============

    def get_available_support_targets(self, supporter, battles):
        """
        获取一个棋子可以支援的所有己方战斗
        支援条件：与攻击方主将或防守方主将的距离 ≤ 支援范围
        （因为战斗中两枚主将相邻，与任意一枚相邻即可）
        """
        if supporter is None:
            return []

        if not supporter.can_support():
            return []

        targets = []

        for battle in battles:
            if battle.is_resolved or battle.is_finished:
                continue

            # 检查与攻击方或防守方主将的距离
            dist_to_attacker = abs(supporter.row - battle.attacker.row) + abs(supporter.col - battle.attacker.col)
            dist_to_defender = abs(supporter.row - battle.defender.row) + abs(supporter.col - battle.defender.col)

            support_range = supporter.get_support_range()

            # 只要与任意一枚主将距离 ≤ 支援范围即可支援
            if dist_to_attacker <= support_range or dist_to_defender <= support_range:
                targets.append(battle)

        return targets

    def get_support_range_for_battle(self, battle, piece):
        """
        检查一个棋子是否能支援某场战斗（用于距离检查）
        返回: bool
        """
        if piece is None or battle is None:
            return False

        if battle.is_resolved or battle.is_finished:
            return False

        dist_to_attacker = abs(piece.row - battle.attacker.row) + abs(piece.col - battle.attacker.col)
        dist_to_defender = abs(piece.row - battle.defender.row) + abs(piece.col - battle.defender.col)

        support_range = piece.get_support_range()

        return dist_to_attacker <= support_range or dist_to_defender <= support_range

    # ============ 统计和查询 ============

    def get_total_hp(self, owner):
        """获取某一方的总HP"""
        pieces = self.player_pieces if owner == 'player' else self.ai_pieces
        total = 0
        for piece in pieces:
            total += piece.hp
        return total

    def get_capital(self, owner):
        """获取某一方的首都"""
        pieces = self.player_pieces if owner == 'player' else self.ai_pieces
        for piece in pieces:
            if piece.piece_type == PieceType.CAPITAL:
                return piece
        return None

    def get_pieces_by_type(self, owner, piece_type):
        """获取某一方特定类型的所有棋子"""
        pieces = self.player_pieces if owner == 'player' else self.ai_pieces
        return [p for p in pieces if p.piece_type == piece_type]

    def get_all_pieces_in_battle(self):
        """获取所有在战斗中的棋子（主将和支援）"""
        result = []
        for piece in self.all_pieces:
            if piece.is_in_battle or piece.is_supporting:
                result.append(piece)
        return result

    def get_all_valid_moves(self, piece):
        """获取棋子的所有有效移动位置（兼容旧接口）"""
        return self.get_valid_moves_for_piece(piece)

    # ============ 回合管理 ============

    def reset_turn_status(self):
        """重置所有棋子的回合状态"""
        for piece in self.all_pieces:
            piece.has_acted_this_turn = False
            piece.has_moved_this_turn = False
            piece.has_attacked_this_turn = False
            piece.actions_used_this_turn = 0

    # ============ 调试 ============

    def print_board(self):
        """打印棋盘状态（调试用）"""
        print("\n" + "=" * 60)
        print("   " + " ".join(f"{i:2}" for i in range(BOARD_SIZE)))
        print("  " + "-" * (BOARD_SIZE * 3 + 2))

        for row in range(BOARD_SIZE):
            print(f"{row:2}|", end=" ")
            for col in range(BOARD_SIZE):
                piece = self.get_piece_at(row, col)
                if piece is None:
                    print(" .", end=" ")
                else:
                    # 显示棋子类型缩写
                    if piece.piece_type == PieceType.INFANTRY:
                        char = "I"
                    elif piece.piece_type == PieceType.CAVALRY:
                        char = "C"
                    elif piece.piece_type == PieceType.ARTILLERY:
                        char = "A"
                    elif piece.piece_type == PieceType.CAPITAL:
                        char = "K"
                    else:
                        char = "?"
                    # 显示阵营
                    owner_char = "P" if piece.owner == 'player' else "E"
                    print(f"{owner_char}{char}", end=" ")
            print(f"|{row}")
        print("  " + "-" * (BOARD_SIZE * 3 + 2))
        print("   " + " ".join(f"{i:2}" for i in range(BOARD_SIZE)))
        print("=" * 60)