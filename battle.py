"""
battle.py - 战斗系统
"""

from Constant import PieceType


class Battle:
    """战斗类 - 管理单场战斗"""

    def __init__(self, attacker, defender):
        self.attacker = attacker
        self.defender = defender
        self.attacker_supports = []
        self.defender_supports = []
        self.is_resolved = False
        self.is_finished = False
        self.turns_active = 0

        attacker.is_in_battle = True
        defender.is_in_battle = True

    def add_support(self, supporter, side):
        """添加支援棋子"""
        # 检查支援者是否已经在战斗中
        if supporter.is_in_battle:
            return False
        if supporter.is_supporting:
            return False

        if self.is_resolved or self.is_finished:
            return False

        if side == 'attacker':
            if supporter in self.attacker_supports:
                return False
            self.attacker_supports.append(supporter)
        else:
            if supporter in self.defender_supports:
                return False
            self.defender_supports.append(supporter)

        supporter.is_supporting = True
        supporter.supporting_battle = self
        return True

    def remove_support(self, supporter, side):
        """移除支援"""
        if side == 'attacker':
            if supporter in self.attacker_supports:
                self.attacker_supports.remove(supporter)
        else:
            if supporter in self.defender_supports:
                self.defender_supports.remove(supporter)
        supporter.is_supporting = False
        supporter.supporting_battle = None

    def remove_all_supports(self):
        """移除所有支援"""
        for s in self.attacker_supports:
            s.is_supporting = False
            s.supporting_battle = None
        for s in self.defender_supports:
            s.is_supporting = False
            s.supporting_battle = None
        self.attacker_supports = []
        self.defender_supports = []

    def calculate_attack_value(self):
        """计算攻击值 = 主将攻击 + 所有支援的S值"""
        total = self.attacker.attack
        for s in self.attacker_supports:
            total += s.support
        return total

    def calculate_defense_value(self):
        """计算防御值 = 主将防御 + 所有支援的S值"""
        total = self.defender.defense
        for s in self.defender_supports:
            total += s.support
        return total

    def can_retreat(self, piece):
        """检查主将是否可以撤退（战斗持续至少1回合）"""
        if piece != self.attacker and piece != self.defender:
            return False
        if self.turns_active < 1:
            return False
        return True

    def get_retreat_positions(self, piece, board):
        """获取撤退可用的位置列表"""
        if not self.can_retreat(piece):
            return []

        adjacent = board.get_adjacent_positions(piece.row, piece.col)
        empty_positions = []

        for row, col in adjacent:
            if board.get_piece_at(row, col) is None:
                empty_positions.append((row, col))

        if empty_positions:
            return empty_positions

        # 替代跳跃规则
        supports = self.attacker_supports if piece == self.attacker else self.defender_supports

        for row, col in adjacent:
            has_support_adjacent = False
            for s in supports:
                if abs(s.row - row) + abs(s.col - col) == 1:
                    has_support_adjacent = True
                    break
            if not has_support_adjacent:
                continue

            has_enemy_adjacent = False
            enemy_pieces = board.player_pieces if piece.owner == 'ai' else board.ai_pieces
            for e in enemy_pieces:
                if abs(e.row - row) + abs(e.col - col) == 1:
                    has_enemy_adjacent = True
                    break

            if not has_enemy_adjacent and board.get_piece_at(row, col) is None:
                empty_positions.append((row, col))

        return empty_positions

    def execute_retreat(self, piece, target_row, target_col, board):
        """执行撤退"""
        if (target_row, target_col) not in self.get_retreat_positions(piece, board):
            return False

        board.grid[piece.row][piece.col] = None
        board.grid[target_row][target_col] = piece
        piece.row = target_row
        piece.col = target_col

        if piece.hp > 1:
            piece.hp -= 1

        # 释放双方主将和所有支援
        self.attacker.is_in_battle = False
        self.defender.is_in_battle = False
        self.remove_all_supports()
        self.is_finished = True
        self.is_resolved = True

        piece.has_acted_this_turn = True
        piece.actions_used_this_turn += 1

        return True

    def resolve(self, board):
        """结算战斗伤害，只有一方死亡才结束战斗"""
        if self.is_resolved or self.is_finished:
            return None

        # 检查主将是否还在棋盘上
        if self.attacker not in board.all_pieces:
            self._finish_battle(board, self.attacker)
            return None
        if self.defender not in board.all_pieces:
            self._finish_battle(board, self.defender)
            return None

        attack_value = self.calculate_attack_value()
        defense_value = self.calculate_defense_value()

        result = {
            'attacker_damage': 0,
            'defender_damage': 0,
            'winner': None,
            'attacker_destroyed': False,
            'defender_destroyed': False,
            'battle_continued': True,
        }

        if attack_value > defense_value:
            damage = attack_value - defense_value
            result['defender_damage'] = damage
            result['winner'] = 'attacker'
            destroyed = self.defender.take_damage(damage)
            if destroyed:
                result['defender_destroyed'] = True
                board.remove_piece(self.defender)
                self._finish_battle(board, self.defender)
                result['battle_continued'] = False

        elif defense_value > attack_value:
            damage = defense_value - attack_value
            result['attacker_damage'] = damage
            result['winner'] = 'defender'
            destroyed = self.attacker.take_damage(damage)
            if destroyed:
                result['attacker_destroyed'] = True
                board.remove_piece(self.attacker)
                self._finish_battle(board, self.attacker)
                result['battle_continued'] = False

        else:
            result['winner'] = 'draw'

        # 如果双方都存活，战斗继续
        if result['battle_continued']:
            self.attacker.is_in_battle = True
            self.defender.is_in_battle = True

        return result

    def _finish_battle(self, board, destroyed_piece):
        """结束战斗：释放所有主将和支援者"""
        self.remove_all_supports()

        if self.attacker in board.all_pieces:
            self.attacker.is_in_battle = False
        if self.defender in board.all_pieces:
            self.defender.is_in_battle = False

        self.is_finished = True
        self.is_resolved = True

    def increment_turn(self):
        """增加战斗持续回合数"""
        if not self.is_finished and not self.is_resolved:
            self.turns_active += 1


class BattleManager:
    """战斗管理器 - 管理所有待结算的战斗"""

    def __init__(self):
        self.pending_battles = []
        self.resolved_battles = []

    def create_battle(self, attacker, defender, board):
        """创建战斗"""
        if attacker.piece_type == PieceType.ARTILLERY:
            return None
        if attacker.is_in_battle or defender.is_in_battle:
            return None
        if attacker.owner == defender.owner:
            return None

        battle = Battle(attacker, defender)
        self.pending_battles.append(battle)
        return battle

    def add_support_to_battle(self, battle, supporter, side):
        """手动添加支援"""
        if battle.is_resolved or battle.is_finished:
            return False
        return battle.add_support(supporter, side)

    def get_battles_by_owner(self, owner):
        """获取某一方的所有战斗"""
        result = []
        for battle in self.pending_battles:
            if battle.is_resolved or battle.is_finished:
                continue
            if battle.attacker.owner == owner or battle.defender.owner == owner:
                result.append(battle)
        return result

    def increment_all_turns(self):
        """所有活跃战斗增加回合计数"""
        for battle in self.pending_battles:
            if not battle.is_resolved and not battle.is_finished:
                battle.increment_turn()

    def resolve_all(self, board):
        """结算所有待结算的战斗"""
        results = []

        for battle in self.pending_battles:
            if not battle.is_resolved and not battle.is_finished:
                result = battle.resolve(board)
                if result is not None:
                    results.append(result)

        self.pending_battles = [
            b for b in self.pending_battles
            if not b.is_resolved and not b.is_finished
        ]

        return results

    def get_pending_count(self):
        return len([b for b in self.pending_battles if not b.is_resolved and not b.is_finished])

    def clear(self):
        for battle in self.pending_battles:
            battle.remove_all_supports()
        self.pending_battles = []
        self.resolved_battles = []

    def get_all_active_battles(self):
        return [b for b in self.pending_battles if not b.is_resolved and not b.is_finished]