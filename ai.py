"""
ai.py - AI 决策系统（全力进攻首都版）
"""

from Constant import PieceType


class AI:
    def __init__(self, board):
        self.owner = 'ai'
        self.board = board
        self.actions_taken = 0
        self.max_actions = 5

    def _reset_turn_status(self):
        for piece in self.board.ai_pieces:
            piece.has_acted_this_turn = False
            piece.has_moved_this_turn = False
            piece.has_attacked_this_turn = False
            piece.actions_used_this_turn = 0

    def _get_capital(self, owner):
        pieces = self.board.player_pieces if owner == 'player' else self.board.ai_pieces
        for piece in pieces:
            if piece.piece_type == PieceType.CAPITAL:
                return piece
        return None

    def _get_adjacent_enemy_positions(self, piece):
        enemies = []
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        for dr, dc in directions:
            nr, nc = piece.row + dr, piece.col + dc
            if self.board.is_valid_position(nr, nc):
                target = self.board.get_piece_at(nr, nc)
                if target and target.owner != piece.owner:
                    enemies.append((target, nr, nc))
        return enemies

    def _can_attack_capital(self, piece, capital):
        """检查棋子是否能攻击首都"""
        if not piece.can_act():
            return False
        if piece.piece_type == PieceType.CAPITAL:
            return False

        distance = abs(piece.row - capital.row) + abs(piece.col - capital.col)

        # 首都就在相邻位置
        if distance == 1:
            if piece.piece_type == PieceType.CAVALRY:
                return piece.can_attack()
            if piece.piece_type == PieceType.INFANTRY:
                return piece.can_act()
            if piece.piece_type == PieceType.ARTILLERY:
                # 炮兵不能直接攻击首都（只能轰炸）
                return False
        return False

    def _get_action_attack_capital(self, piece, capital):
        """生成攻击首都的动作"""
        distance = abs(piece.row - capital.row) + abs(piece.col - capital.col)

        if distance == 1:
            if piece.piece_type == PieceType.CAVALRY:
                return ('move_and_attack', {
                    'target': capital,
                    'target_row': capital.row,
                    'target_col': capital.col
                })
            elif piece.piece_type == PieceType.INFANTRY:
                return ('move_and_attack', {
                    'target': capital,
                    'target_row': capital.row,
                    'target_col': capital.col
                })
        return None

    def _move_towards_capital(self, piece, capital):
        """向首都方向移动一步"""
        if not piece.can_move():
            return None

        # 计算方向
        dr = 1 if capital.row > piece.row else -1 if capital.row < piece.row else 0
        dc = 1 if capital.col > piece.col else -1 if capital.col < piece.col else 0

        # 尝试各种移动组合
        moves = [(dr, dc), (dr, 0), (0, dc), (dc, dr), (-dc, -dr)]
        for r_off, c_off in moves:
            nr, nc = piece.row + r_off, piece.col + c_off
            if self.board.is_valid_position(nr, nc):
                if self.board.get_piece_at(nr, nc) is None:
                    if not self.board.is_path_blocked(piece.row, piece.col, nr, nc):
                        return ('move', {
                            'target_row': nr,
                            'target_col': nc
                        })

        # 如果没有可移动的位置，尝试任何有效移动
        valid_moves = self.board.get_all_valid_moves(piece)
        if valid_moves:
            import random
            move = random.choice(valid_moves)
            return ('move', {
                'target_row': move[0],
                'target_col': move[1]
            })

        return None

    def _get_available_action(self, piece, capital):
        """
        检查一个棋子可以执行什么行动
        优先级：首都攻击 > 炮兵轰炸 > 骑兵攻击 > 步兵攻击 > 支援 > 向首都移动
        """
        # 1. 攻击首都（最高优先级）
        if self._can_attack_capital(piece, capital):
            return self._get_action_attack_capital(piece, capital)

        # 2. 炮兵轰炸
        if piece.piece_type == PieceType.ARTILLERY and piece.can_act():
            for enemy in self.board.player_pieces:
                if piece.can_bombard(enemy.row, enemy.col, self.board):
                    return ('bombard', {'target': enemy})

        # 3. 骑兵攻击（攻击相邻敌方棋子）
        if piece.piece_type == PieceType.CAVALRY and piece.can_attack():
            enemies = self._get_adjacent_enemy_positions(piece)
            for enemy, nr, nc in enemies:
                # 避免攻击首都（首都已经最高优先级处理了）
                if enemy.piece_type != PieceType.CAPITAL:
                    return ('move_and_attack', {
                        'target': enemy,
                        'target_row': nr,
                        'target_col': nc
                    })

        # 4. 步兵攻击（移动到相邻敌方位置）
        if piece.piece_type == PieceType.INFANTRY and piece.can_act():
            enemies = self._get_adjacent_enemy_positions(piece)
            for enemy, nr, nc in enemies:
                if enemy.piece_type != PieceType.CAPITAL:
                    return ('move_and_attack', {
                        'target': enemy,
                        'target_row': nr,
                        'target_col': nc
                    })

        # 5. 支援己方战斗
        if piece.can_support():
            battles = self.board.battle_manager.get_all_active_battles()
            for battle in battles:
                if battle.attacker.owner == 'ai':
                    main_piece = battle.attacker
                    side = 'attacker'
                elif battle.defender.owner == 'ai':
                    main_piece = battle.defender
                    side = 'defender'
                else:
                    continue

                distance = abs(piece.row - main_piece.row) + abs(piece.col - main_piece.col)
                support_range = piece.get_support_range()
                if distance <= support_range:
                    return ('support', {
                        'battle': battle,
                        'side': side,
                        'target_row': main_piece.row,
                        'target_col': main_piece.col
                    })

        # 6. 向首都移动
        return self._move_towards_capital(piece, capital)

    def select_best_action(self):
        """选择最佳行动"""
        capital = self._get_capital('player')
        if capital is None:
            return {'action_type': 'end_turn'}

        pieces = self.board.ai_pieces.copy()

        # 按距离首都远近排序（近的优先）
        pieces.sort(key=lambda p: abs(p.row - capital.row) + abs(p.col - capital.col))

        # 按类型优先级排序（骑兵优先攻击）
        type_priority = {
            PieceType.CAVALRY: 0,
            PieceType.ARTILLERY: 1,
            PieceType.INFANTRY: 2,
        }
        pieces.sort(key=lambda p: type_priority.get(p.piece_type, 3))

        for piece in pieces:
            if piece.is_in_battle or piece.is_supporting:
                continue
            if not piece.can_act():
                continue

            action = self._get_available_action(piece, capital)
            if action:
                action_type, data = action
                return {
                    'action_type': action_type,
                    'piece': piece,
                    **data
                }

        return {'action_type': 'end_turn'}

    def make_turn(self, board):
        """执行AI回合（最多5次行动）"""
        self.board = board
        self.actions_taken = 0
        self._reset_turn_status()

        actions = []

        while self.actions_taken < self.max_actions:
            action = self.select_best_action()

            if action['action_type'] == 'end_turn':
                break

            actions.append(action)
            self.actions_taken += 1

            piece = action['piece']
            piece.has_acted_this_turn = True
            piece.actions_used_this_turn += 1

            if action['action_type'] == 'move_and_attack':
                piece.has_moved_this_turn = True
                piece.has_attacked_this_turn = True
            elif action['action_type'] == 'move':
                piece.has_moved_this_turn = True
            elif action['action_type'] == 'bombard':
                pass
            elif action['action_type'] == 'support':
                pass

        return actions