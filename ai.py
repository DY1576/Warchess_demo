"""
ai.py - AI 决策系统（强化版）
"""
import random
from collections import deque
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

    def _get_bfs_path(self, start_piece, target_row, target_col):
        """改进版 BFS：允许穿透棋子计算大致方向，但第一步必须是空格"""
        queue = deque([(start_piece.row, start_piece.col, [])])
        visited = set([(start_piece.row, start_piece.col)])
        closest_first_step = None
        min_dist = abs(start_piece.row - target_row) + abs(start_piece.col - target_col)

        while queue:
            r, c, path = queue.popleft()
            dist = abs(r - target_row) + abs(c - target_col)
            if dist < min_dist and len(path) > 0:
                min_dist = dist
                closest_first_step = path[0]
            if r == target_row and c == target_col:
                return path[0] if path else None

            for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nr, nc = r + dr, c + dc
                if self.board.is_valid_position(nr, nc) and (nr, nc) not in visited:
                    if len(path) == 0 and self.board.get_piece_at(nr, nc) is not None:
                        continue
                    visited.add((nr, nc))
                    queue.append((nr, nc, path + [(nr, nc)]))

        return closest_first_step

    def _get_closest_player_piece(self, piece):
        best = None
        best_dist = 999
        for enemy in self.board.player_pieces:
            dist = abs(enemy.row - piece.row) + abs(enemy.col - piece.col)
            if dist < best_dist:
                best_dist = dist
                best = enemy
        return best, best_dist

    def _piece_value(self, piece):
        if piece.piece_type == PieceType.CAPITAL:
            return 200
        if piece.piece_type == PieceType.ARTILLERY:
            return 130
        if piece.piece_type == PieceType.CAVALRY:
            return 110
        if piece.piece_type == PieceType.INFANTRY:
            return 90
        return 50

    def _attack_score(self, piece, enemy):
        score = self._piece_value(enemy) + 20
        if piece.piece_type == PieceType.CAVALRY:
            score += 15
        if enemy.piece_type == PieceType.ARTILLERY:
            score += 15
        if enemy.piece_type == PieceType.CAPITAL:
            score += 200
        return score

    def _bombard_score(self, artillery, enemy):
        score = self._piece_value(enemy) + 40
        if enemy.piece_type == PieceType.CAPITAL:
            score += 150
        if enemy.piece_type == PieceType.ARTILLERY:
            score += 50
        return score

    def _support_score(self, supporter, battle):
        score = 90
        if battle.attacker.piece_type == PieceType.CAPITAL or battle.defender.piece_type == PieceType.CAPITAL:
            score += 40
        if supporter.piece_type == PieceType.ARTILLERY:
            score += 15
        if supporter.piece_type == PieceType.CAVALRY:
            score += 10
        return score

    def _distance_to_nearest_enemy(self, row, col):
        best = 999
        for enemy in self.board.player_pieces:
            dist = abs(enemy.row - row) + abs(enemy.col - col)
            if dist < best:
                best = dist
        return best

    def _get_average_ai_row(self):
        if not self.board.ai_pieces:
            return 0
        return sum(piece.row for piece in self.board.ai_pieces) / len(self.board.ai_pieces)

    def _position_score(self, piece, target_row, target_col, priority_enemy, capital, active_battles):
        score = 0
        current_dist = self._distance_to_nearest_enemy(piece.row, piece.col)
        target_dist = self._distance_to_nearest_enemy(target_row, target_col)

        score += (current_dist - target_dist) * 40
        if target_dist == 1:
            score += 150
        elif target_dist == 2:
            score += 50

        if target_dist >= current_dist:
            score -= 12

        if capital is not None:
            current_capital_dist = abs(piece.row - capital.row) + abs(piece.col - capital.col)
            target_capital_dist = abs(target_row - capital.row) + abs(target_col - capital.col)
            score += (current_capital_dist - target_capital_dist) * 30
            if target_capital_dist <= 3:
                score += 80

        enemy_rows = [enemy.row for enemy in self.board.player_pieces]
        if enemy_rows:
            avg_enemy_row = sum(enemy_rows) / len(enemy_rows)
            preferred_direction = 1 if avg_enemy_row > piece.row else -1
            score += max(0, (target_row - piece.row) * preferred_direction) * 18

        avg_ai_row = self._get_average_ai_row()
        if piece.row < avg_ai_row and target_row > piece.row:
            score += 30
        if target_row == piece.row and target_dist >= current_dist:
            score -= 18

        if capital is not None:
            current_capital_col_dist = abs(piece.col - capital.col)
            target_capital_col_dist = abs(target_col - capital.col)
            score += max(0, current_capital_col_dist - target_capital_col_dist) * 10

        for enemy in self.board.player_pieces:
            dist = abs(enemy.row - target_row) + abs(enemy.col - target_col)
            if dist == 1:
                score += self._piece_value(enemy) + 50
            elif dist == 2:
                score += 30

        if priority_enemy is not None:
            dist = abs(priority_enemy.row - target_row) + abs(priority_enemy.col - target_col)
            score += max(0, 90 - dist * 5)
            if priority_enemy.piece_type == PieceType.CAPITAL:
                score += 30

        if active_battles:
            for battle in active_battles:
                dist_to_attacker = abs(target_row - battle.attacker.row) + abs(target_col - battle.attacker.col)
                dist_to_defender = abs(target_row - battle.defender.row) + abs(target_col - battle.defender.col)
                support_range = piece.get_support_range()
                if dist_to_attacker <= support_range or dist_to_defender <= support_range:
                    score += 40
                    break

        if piece.piece_type == PieceType.ARTILLERY:
            for enemy in self.board.player_pieces:
                dist = abs(enemy.row - target_row) + abs(enemy.col - target_col)
                if 0 < dist <= 2:
                    score += self._piece_value(enemy) // 2 + 20

        return score

    def _best_move_action(self, piece, active_battles, nearest_enemy, capital):
        moves = self.board.get_valid_moves_for_piece(piece)
        if not moves:
            return None, -9999

        priority_enemy = None
        if active_battles:
            battle_centers = [battle.attacker if battle.attacker.owner == 'player' else battle.defender for battle in active_battles]
            priority_enemy = min(battle_centers, key=lambda x: abs(x.row - piece.row) + abs(x.col - piece.col))
        else:
            priority_enemy = nearest_enemy

        best_score = -9999
        best_move = None
        best_dist = 999
        for row, col in moves:
            score = self._position_score(piece, row, col, priority_enemy, capital, active_battles)
            dist = self._distance_to_nearest_enemy(row, col)
            if score > best_score or (score == best_score and dist < best_dist):
                best_score = score
                best_move = (row, col)
                best_dist = dist

        if best_move is None:
            return None, -9999

        return ('move', {'piece': piece, 'target_row': best_move[0], 'target_col': best_move[1]}), best_score

    def _evaluate_all_actions(self, capital):
        best_action = None
        best_score = -9999
        active_battles = self.board.battle_manager.get_all_active_battles()

        for piece in self.board.ai_pieces:
            if piece.is_in_battle or piece.is_supporting or not piece.can_act():
                continue

            nearest_enemy, enemy_dist = self._get_closest_player_piece(piece)

            if piece.can_attack():
                for enemy in self.board.get_adjacent_enemy_pieces(piece):
                    if enemy.owner != piece.owner:
                        score = self._attack_score(piece, enemy)
                        if score > best_score:
                            best_score = score
                            best_action = ('move_and_attack', {'piece': piece, 'target': enemy, 'target_row': enemy.row, 'target_col': enemy.col})

            if piece.piece_type == PieceType.ARTILLERY:
                if piece.can_act():
                    for enemy, row, col in self.board.get_valid_bombard_targets(piece):
                        if enemy.owner != piece.owner:
                            score = self._bombard_score(piece, enemy)
                            if score > best_score:
                                best_score = score
                                best_action = ('bombard', {'piece': piece, 'target': enemy})

                if piece.can_support():
                    for battle in active_battles:
                        if self.board.get_support_range_for_battle(battle, piece):
                            score = self._support_score(piece, battle)
                            if score > best_score:
                                best_score = score
                                best_action = ('support', {'piece': piece, 'battle': battle, 'side': 'attacker' if battle.attacker.owner == 'ai' else 'defender'})

                if piece.can_move():
                    move_action, move_score = self._best_move_action(piece, active_battles, nearest_enemy, capital)
                    if move_action and move_score > best_score:
                        best_score = move_score
                        best_action = move_action
                continue

            if piece.can_support():
                for battle in active_battles:
                    if self.board.get_support_range_for_battle(battle, piece):
                        score = self._support_score(piece, battle)
                        if score > best_score:
                            best_score = score
                            best_action = ('support', {'piece': piece, 'battle': battle, 'side': 'attacker' if battle.attacker.owner == 'ai' else 'defender'})

            if piece.can_move():
                move_action, move_score = self._best_move_action(piece, active_battles, nearest_enemy, capital)
                if move_action and move_score > best_score:
                    best_score = move_score
                    best_action = move_action

        return best_action or ('end_turn', {})

    def make_turn(self, board):
        self.board = board
        self.actions_taken = 0
        self._reset_turn_status()
        actions = []

        while self.actions_taken < self.max_actions:
            action = self._evaluate_all_actions(self.board.get_capital('player'))
            action_type, data = action[0], action[1]
            if action_type == 'end_turn':
                break

            data['action_type'] = action_type
            actions.append(data)
            self.actions_taken += 1

            piece = data['piece']
            piece.has_acted_this_turn = True
            piece.actions_used_this_turn += 1

            if action_type == 'move':
                piece.has_moved_this_turn = True
                self.board.move_piece(piece, data['target_row'], data['target_col'])
            elif action_type == 'move_and_attack':
                piece.has_moved_this_turn = True
                piece.has_attacked_this_turn = True
                target = data['target']
                if target.piece_type == PieceType.ARTILLERY:
                    self.board.remove_piece(target)
                else:
                    battle = self.board.battle_manager.create_battle(piece, target, self.board)
                    if battle:
                        piece.has_attacked_this_turn = True
                        piece.has_acted_this_turn = True
                self.board.move_piece_force(piece, data['target_row'], data['target_col'])
            elif action_type == 'bombard':
                artillery = data['piece']
                target = data['target']
                damage = artillery.bombard(target)
                if damage > 0:
                    destroyed = target.take_damage(damage)
                    if destroyed:
                        self.board.remove_piece(target)
                artillery.has_attacked_this_turn = True
                artillery.has_acted_this_turn = True
            elif action_type == 'support':
                supporter = data['piece']
                battle = data['battle']
                side = data['side']
                if self.board.battle_manager.add_support_to_battle(battle, supporter, side):
                    supporter.has_acted_this_turn = True

        return actions