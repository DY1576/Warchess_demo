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
            return 240
        if piece.piece_type == PieceType.ARTILLERY:
            return 140
        if piece.piece_type == PieceType.CAVALRY:
            return 120
        if piece.piece_type == PieceType.INFANTRY:
            return 100
        return 60

    def _target_importance(self, enemy):
        score = self._piece_value(enemy)
        if enemy.piece_type == PieceType.CAPITAL:
            score += 260
        if enemy.piece_type == PieceType.ARTILLERY:
            score += 80
        return score

    def _attack_score(self, piece, enemy):
        score = self._target_importance(enemy) + 100
        if piece.piece_type == PieceType.CAVALRY:
            score += 40
        if enemy.piece_type == PieceType.ARTILLERY:
            score += 30
        if enemy.piece_type == PieceType.CAPITAL:
            score += 220

        score += len(self.board.get_adjacent_enemy_pieces(enemy)) * 15

        capital = self.board.get_capital('player')
        if capital and abs(enemy.row - capital.row) + abs(enemy.col - capital.col) <= 3:
            score += 60

        if piece.row < self._get_average_ai_row():
            score += 25

        return score

    def _bombard_score(self, artillery, enemy):
        score = self._target_importance(enemy) + 80
        if enemy.piece_type == PieceType.CAPITAL:
            score += 200
        if enemy.piece_type == PieceType.ARTILLERY:
            score += 70

        capital = self.board.get_capital('player')
        if capital and abs(enemy.row - capital.row) + abs(enemy.col - capital.col) <= 3:
            score += 35

        return score

    def _support_score(self, supporter, battle):
        score = 90
        score += (self._piece_value(battle.attacker) + self._piece_value(battle.defender)) // 3
        if battle.attacker.piece_type == PieceType.CAPITAL or battle.defender.piece_type == PieceType.CAPITAL:
            score += 70
        if supporter.piece_type == PieceType.ARTILLERY:
            score += 25
        if supporter.piece_type == PieceType.CAVALRY:
            score += 20
        if supporter.row > self._get_average_ai_row():
            score += 20
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

    def _future_value(self, piece, target_row, target_col):
        value = 0
        for enemy in self.board.player_pieces:
            dist = abs(enemy.row - target_row) + abs(enemy.col - target_col)
            if piece.piece_type == PieceType.ARTILLERY and 0 < dist <= 2:
                value += self._piece_value(enemy) * 0.18
            if piece.can_attack() and dist == 1:
                value += 30
            elif piece.can_attack() and dist == 2:
                value += 12
        return value

    def _move_score(self, piece, target_row, target_col, priority_enemy, capital, active_battles):
        score = 0
        current_dist = self._distance_to_nearest_enemy(piece.row, piece.col)
        target_dist = self._distance_to_nearest_enemy(target_row, target_col)

        score += (current_dist - target_dist) * 50
        if target_dist == 1:
            score += 200
        elif target_dist == 2:
            score += 80

        score += (target_row - piece.row) * 28
        if piece.row < self._get_average_ai_row() and target_row > piece.row:
            score += 45

        if target_row == piece.row and target_dist >= current_dist:
            score -= 35

        if capital is not None:
            current_capital_dist = abs(piece.row - capital.row) + abs(piece.col - capital.col)
            target_capital_dist = abs(target_row - capital.row) + abs(target_col - capital.col)
            score += (current_capital_dist - target_capital_dist) * 40
            if target_capital_dist <= 3:
                score += 120

            current_capital_col_dist = abs(piece.col - capital.col)
            target_capital_col_dist = abs(target_col - capital.col)
            score += max(0, current_capital_col_dist - target_capital_col_dist) * 15

        if priority_enemy is not None:
            dist = abs(priority_enemy.row - target_row) + abs(priority_enemy.col - target_col)
            score += max(0, 130 - dist * 8)
            if priority_enemy.piece_type == PieceType.CAPITAL:
                score += 50

        for enemy in self.board.player_pieces:
            dist = abs(enemy.row - target_row) + abs(enemy.col - target_col)
            if dist == 1:
                score += self._piece_value(enemy) + 65
            elif dist == 2:
                score += 45

        if active_battles:
            for battle in active_battles:
                support_range = piece.get_support_range()
                if abs(target_row - battle.attacker.row) + abs(target_col - battle.attacker.col) <= support_range or abs(target_row - battle.defender.row) + abs(target_col - battle.defender.col) <= support_range:
                    score += 60
                    break

        score += int(self._future_value(piece, target_row, target_col))

        if piece.piece_type == PieceType.ARTILLERY:
            for enemy in self.board.player_pieces:
                dist = abs(enemy.row - target_row) + abs(enemy.col - target_col)
                if 0 < dist <= 2:
                    score += self._piece_value(enemy) * 0.3

        return score

    def _validate_candidate(self, action_type, data):
        piece = data['piece']
        if piece.is_in_battle or piece.is_supporting or not piece.can_act():
            return False
        if action_type == 'move':
            return (data['target_row'], data['target_col']) in self.board.get_valid_moves_for_piece(piece)
        if action_type == 'move_and_attack':
            return data['target'] in self.board.get_adjacent_enemy_pieces(piece)
        if action_type == 'bombard':
            return any(data['target'] == enemy for enemy, row, col in self.board.get_valid_bombard_targets(piece))
        if action_type == 'support':
            return self.board.get_support_range_for_battle(data['battle'], piece)
        return False

    def _build_action_queue(self, capital):
        import heapq
        queue = []
        action_id = 0
        active_battles = self.board.battle_manager.get_all_active_battles()

        for piece in self.board.ai_pieces:
            if piece.is_in_battle or piece.is_supporting or not piece.can_act():
                continue

            nearest_enemy, enemy_dist = self._get_closest_player_piece(piece)

            if piece.can_attack():
                for enemy in self.board.get_adjacent_enemy_pieces(piece):
                    if enemy.owner != piece.owner:
                        score = self._attack_score(piece, enemy)
                        heapq.heappush(queue, (-score, action_id, ('move_and_attack', {'piece': piece, 'target': enemy, 'target_row': enemy.row, 'target_col': enemy.col})))
                        action_id += 1

            if piece.piece_type == PieceType.ARTILLERY and piece.can_act():
                for enemy, row, col in self.board.get_valid_bombard_targets(piece):
                    if enemy.owner != piece.owner:
                        score = self._bombard_score(piece, enemy)
                        heapq.heappush(queue, (-score, action_id, ('bombard', {'piece': piece, 'target': enemy})))
                        action_id += 1

            if piece.can_support():
                for battle in active_battles:
                    if self.board.get_support_range_for_battle(battle, piece):
                        score = self._support_score(piece, battle)
                        heapq.heappush(queue, (-score, action_id, ('support', {'piece': piece, 'battle': battle, 'side': 'attacker' if battle.attacker.owner == 'ai' else 'defender'})))
                        action_id += 1

            if piece.can_move():
                for row, col in self.board.get_valid_moves_for_piece(piece):
                    score = self._move_score(piece, row, col, nearest_enemy, capital, active_battles)
                    heapq.heappush(queue, (-score, action_id, ('move', {'piece': piece, 'target_row': row, 'target_col': col})))
                    action_id += 1

        return queue

    def _execute_action(self, action_type, data):
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

    def make_turn(self, board):
        import heapq
        self.board = board
        self.actions_taken = 0
        self._reset_turn_status()
        actions = []
        capital = self.board.get_capital('player')

        while self.actions_taken < self.max_actions:
            queue = self._build_action_queue(capital)
            if not queue:
                break

            while queue:
                _, _, candidate = heapq.heappop(queue)
                action_type, data = candidate
                if not self._validate_candidate(action_type, data):
                    continue
                self._execute_action(action_type, data)
                data['action_type'] = action_type
                actions.append(data)
                self.actions_taken += 1
                break
            else:
                break

        return actions