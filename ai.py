"""
ai.py - AI 决策系统（BFS寻路 + 权重评估增强版）
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
        # 记录当前能找到的最小距离
        min_dist = abs(start_piece.row - target_row) + abs(start_piece.col - target_col)

        while queue:
            r, c, path = queue.popleft()
            
            # 记录探索过程中，距离目标最近的有效起步
            dist = abs(r - target_row) + abs(c - target_col)
            if dist < min_dist and len(path) > 0:
                min_dist = dist
                closest_first_step = path[0]

            # 找到了终点，直接返回最优的第一步
            if r == target_row and c == target_col:
                return path[0] if path else None

            for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nr, nc = r + dr, c + dc
                if self.board.is_valid_position(nr, nc) and (nr, nc) not in visited:
                    # 关键修改：第一步必须是空格，后续步骤可以无视棋子碰撞（只为测算最短方向）
                    if len(path) == 0 and self.board.get_piece_at(nr, nc) is not None:
                        continue 
                        
                    visited.add((nr, nc))
                    queue.append((nr, nc, path + [(nr, nc)]))
                    
        # 如果被完全死路卡住，返回能到达的离目标最近的第一步
        return closest_first_step

    def _get_closest_player_piece(self, piece):
        """返回距离当前AI棋子最近的玩家棋子"""
        best = None
        best_dist = 999
        for enemy in self.board.player_pieces:
            dist = abs(enemy.row - piece.row) + abs(enemy.col - piece.col)
            if dist < best_dist:
                best_dist = dist
                best = enemy
        return best, best_dist

    def _evaluate_move_toward(self, piece, target):
        """评估移动方向，优先靠近攻击目标或战斗。"""
        if target is None or not piece.can_move():
            return None
        next_step = self._get_bfs_path(piece, target.row, target.col)
        if next_step and self.board.get_piece_at(next_step[0], next_step[1]) is None:
            return next_step
        return None

    def _evaluate_all_actions(self, capital):
        """遍历所有AI棋子，评估并返回得分最高的行动"""
        best_action = None
        best_score = -9999

        active_battles = self.board.battle_manager.get_all_active_battles()
        closest_enemy_cache = {}

        for piece in self.board.ai_pieces:
            if piece.is_in_battle or piece.is_supporting or not piece.can_act():
                continue

            nearest_enemy, enemy_dist = self._get_closest_player_piece(piece)

            # 1. 评估炮兵轰炸 (高优，白嫖伤害)
            if piece.piece_type == PieceType.ARTILLERY:
                bombard_targets = []
                for enemy in self.board.player_pieces:
                    if piece.can_bombard(enemy.row, enemy.col, self.board):
                        score = 90 if enemy.piece_type == PieceType.CAPITAL else 55
                        bombard_targets.append((score, enemy))
                if bombard_targets:
                    score, enemy = max(bombard_targets, key=lambda item: item[0])
                    if score > best_score:
                        best_score, best_action = score, ('bombard', {'piece': piece, 'target': enemy})
                    continue

                # 2. 评估炮兵支援
                if piece.can_support():
                    for battle in active_battles:
                        if self.board.get_support_range_for_battle(battle, piece):
                            score = 60
                            if score > best_score:
                                best_score, best_action = score, ('support', {'piece': piece, 'battle': battle, 'side': 'attacker' if battle.attacker.owner == 'ai' else 'defender'})

                # 3. 评估炮兵移动到更有利位置
                if piece.can_move():
                    if active_battles:
                        # 让炮兵靠近当前战斗中心
                        battle_target = active_battles[0].attacker if active_battles[0].attacker.owner == 'player' else active_battles[0].defender
                        next_step = self._evaluate_move_toward(piece, battle_target)
                    else:
                        next_step = self._evaluate_move_toward(piece, nearest_enemy)
                    if next_step:
                        score = 30 + max(0, 6 - enemy_dist)
                        if score > best_score:
                            best_score, best_action = score, ('move', {'piece': piece, 'target_row': next_step[0], 'target_col': next_step[1]})
                continue

            # 4. 评估直接攻击
            if piece.can_attack():
                enemies = self.board.get_adjacent_enemy_pieces(piece)
                for enemy in enemies:
                    if enemy.piece_type == PieceType.CAPITAL:
                        score = 1000
                    elif enemy.piece_type == PieceType.ARTILLERY:
                        score = 80
                    else:
                        score = 50
                    if score > best_score:
                        best_score, best_action = score, ('move_and_attack', {'piece': piece, 'target': enemy, 'target_row': enemy.row, 'target_col': enemy.col})

            # 5. 评估支援
            if piece.can_support():
                for battle in active_battles:
                    side = 'attacker' if battle.attacker.owner == 'ai' else ('defender' if battle.defender.owner == 'ai' else None)
                    if side:
                        if self.board.get_support_range_for_battle(battle, piece):
                            score = 70
                            if score > best_score:
                                best_score, best_action = score, ('support', {'piece': piece, 'battle': battle, 'side': side})

            # 6. 评估移动（靠近敌人或战斗）
            if piece.can_move():
                move_target = None
                if active_battles:
                    # 选择最近的激活战斗作为目标
                    battle_centers = [battle.attacker if battle.attacker.owner == 'player' else battle.defender for battle in active_battles]
                    move_target = min(battle_centers, key=lambda t: abs(t.row - piece.row) + abs(t.col - piece.col))
                else:
                    move_target = nearest_enemy

                if move_target:
                    next_step = self._evaluate_move_toward(piece, move_target)
                    if next_step:
                        score = 40 + max(0, 6 - enemy_dist)
                        if piece.piece_type == PieceType.CAVALRY:
                            score += 5
                        elif piece.piece_type == PieceType.INFANTRY:
                            score += 0
                        if score > best_score:
                            best_score, best_action = score, ('move', {'piece': piece, 'target_row': next_step[0], 'target_col': next_step[1]})

        return best_action or ('end_turn', {})

    def make_turn(self, board):
        self.board = board
        self.actions_taken = 0
        self._reset_turn_status()
        actions = []
        player_capital = self.board.get_capital('player')

        while self.actions_taken < self.max_actions:
            action = self._evaluate_all_actions(player_capital)
            action_type, data = action[0], action[1]

            if action_type == 'end_turn':
                break

            data['action_type'] = action_type
            actions.append(data)
            self.actions_taken += 1

            piece = data['piece']
            piece.has_acted_this_turn = True
            piece.actions_used_this_turn += 1

            if action_type == 'move_and_attack':
                piece.has_moved_this_turn = True
                piece.has_attacked_this_turn = True
                self.board.move_piece_force(piece, data['target_row'], data['target_col']) 
            elif action_type == 'move':
                piece.has_moved_this_turn = True
                self.board.move_piece(piece, data['target_row'], data['target_col'])
            # 【新增】脑内预演锁定状态，防止它在同一个回合对同一个棋子下达两次支援/轰炸指令
            elif action_type == 'support':
                piece.is_supporting = True 
            elif action_type == 'bombard':
                piece.has_attacked_this_turn = True

        return actions