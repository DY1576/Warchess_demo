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

    def _evaluate_all_actions(self, capital):
        """遍历所有AI棋子，评估并返回得分最高的行动"""
        best_action = None
        best_score = -9999

        for piece in self.board.ai_pieces:
            if piece.is_in_battle or piece.is_supporting or not piece.can_act():
                continue

            # 1. 评估炮兵轰炸 (高优，白嫖伤害)
            if piece.piece_type == PieceType.ARTILLERY:
                for enemy in self.board.player_pieces:
                    if piece.can_bombard(enemy.row, enemy.col, self.board):
                        score = 80 if enemy.piece_type == PieceType.CAPITAL else 50
                        if score > best_score:
                            best_score, best_action = score, ('bombard', {'piece': piece, 'target': enemy})
                continue # 炮兵不移动，直接结算下一颗棋子

            # 2. 评估直接攻击
            if piece.can_attack():
                enemies = self.board.get_adjacent_enemy_pieces(piece)
                for enemy in enemies:
                    if enemy.piece_type == PieceType.CAPITAL:
                        score = 1000 # 斩首最高优先级
                    elif enemy.piece_type == PieceType.ARTILLERY:
                        score = 70   # 优先秒杀炮兵
                    else:
                        score = 40
                    
                    if score > best_score:
                        best_score, best_action = score, ('move_and_attack', {'piece': piece, 'target': enemy, 'target_row': enemy.row, 'target_col': enemy.col})

            # 3. 评估支援
            if piece.can_support():
                for battle in self.board.battle_manager.get_all_active_battles():
                    # 判断支援阵营
                    side = 'attacker' if battle.attacker.owner == 'ai' else ('defender' if battle.defender.owner == 'ai' else None)
                    if side:
                        main_piece = battle.attacker if side == 'attacker' else battle.defender
                        dist = abs(piece.row - main_piece.row) + abs(piece.col - main_piece.col)
                        if dist <= piece.get_support_range():
                            score = 60 # 支援队友优先级较高
                            if score > best_score:
                                best_score, best_action = score, ('support', {'piece': piece, 'battle': battle, 'side': side})

            # 4. 评估移动（BFS寻路逼近首都）
            if piece.can_move() and capital:
                next_step = self._get_bfs_path(piece, capital.row, capital.col)
                if next_step and self.board.get_piece_at(next_step[0], next_step[1]) is None:
                    # 距离越近，移动意愿越高
                    dist_to_cap = abs(next_step[0] - capital.row) + abs(next_step[1] - capital.col)
                    score = 20 - dist_to_cap 
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