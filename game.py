"""
game.py - 游戏主控制器
"""

import os
import pygame
from Constant import (
    WINDOW_WIDTH, WINDOW_HEIGHT, BOARD_SIZE, CELL_SIZE,
    BOARD_OFFSET_X, BOARD_OFFSET_Y, COLORS, PLAYER_COLOR, AI_COLOR,
    PIECE_DISPLAY_TEXT, PieceType
)
from board import Board
from battle import BattleManager
from ai import AI


class Game:
    """游戏主类"""

    def __init__(self, screen):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 40)
        self.small_font = pygame.font.Font(None, 28)
        self.title_font = pygame.font.Font(None, 60)

        # 游戏状态
        self.state = 'menu'           # menu, select_side, player_turn, ai_turn, battle_resolution, game_over
        self.current_turn = 0
        self.actions_used = 0
        self.max_actions = 5
        self.winner = None
        self.player_side = None       # 'black' 或 'white'

        # 棋盘和战斗
        self.board = None
        self.battle_manager = None
        self.ai = None

        # 选中状态
        self.selected_piece = None
        self.valid_moves = []
        self.valid_targets = []
        self.valid_bombard_targets = []
        self.valid_support_targets = []
        self.valid_retreat_positions = []

        # 操作模式
        self.action_mode = 'idle'          # idle, retreating

        # 消息系统
        self.message = ""
        self.message_timer = 0

        # 按钮区域
        self.end_turn_button = pygame.Rect(WINDOW_WIDTH - 160, WINDOW_HEIGHT - 60, 140, 42)

        # 加载棋子图像
        self.piece_images = {}
        self._load_piece_images()

    def _load_piece_images(self):
        """加载所有棋子图像"""
        piece_types = ['infantry', 'cavalry', 'artillery', 'capital']
        colors = ['black', 'white']
        base_dir = os.path.dirname(os.path.abspath(__file__))

        for color in colors:
            for ptype in piece_types:
                key = f"{color}_{ptype}"
                paths = [
                    os.path.join(base_dir, "graphics", "pieces", f"{key}.png"),
                    os.path.join(base_dir, "graphics", "pieces", f"{key}.PNG"),
                    os.path.join(base_dir, "graphics", f"{key}.png"),
                ]
                loaded = False
                for path in paths:
                    try:
                        if os.path.exists(path):
                            img = pygame.image.load(path).convert_alpha()
                            scaled = pygame.transform.scale(img, (CELL_SIZE - 6, CELL_SIZE - 6))
                            self.piece_images[key] = scaled
                            loaded = True
                            break
                    except pygame.error:
                        continue
                if not loaded:
                    print(f"Warning: Could not load {key}")
                    self.piece_images[key] = None

    def _get_piece_color(self, piece):
        """返回棋子的实际颜色（'black' 或 'white'）"""
        if piece.owner == 'player':
            return self.player_side
        else:
            return 'white' if self.player_side == 'black' else 'black'

    def _get_piece_image(self, piece):
        """根据棋子获取对应的图像"""
        color = self._get_piece_color(piece)
        key = f"{color}_{piece.piece_type}"
        return self.piece_images.get(key)

    def reset_game(self, player_side):
        """重置游戏"""
        self.player_side = player_side
        self.board = Board(player_side)
        self.battle_manager = BattleManager()
        self.ai = AI(self.board)
        self.ai.board.battle_manager = self.battle_manager

        self.current_turn = 0
        self.actions_used = 0
        self.winner = None
        self._clear_selection()
        self._reset_turn_status()

        # [新增逻辑]：根据阵营决定谁先动
        if player_side == 'black':
            self.state = 'player_turn'
            self.message = "Right-click to select, Left-click to act"
        else:
            # 玩家选白棋，黑棋（AI）先动
            self.state = 'ai_turn'
            self.message = "AI thinking..."
            self._switch_to_ai()

    def _reset_turn_status(self):
        """重置所有棋子的回合状态"""
        if self.board:
            self.board.reset_turn_status()

    def _get_player_color(self):
        return (0, 0, 0) if self.player_side == 'black' else (255, 255, 255)

    def _get_ai_color(self):
        return (255, 255, 255) if self.player_side == 'black' else (0, 0, 0)

    def _get_player_outline(self):
        return (255, 255, 255) if self.player_side == 'black' else (0, 0, 0)

    def _get_ai_outline(self):
        return (0, 0, 0) if self.player_side == 'black' else (255, 255, 255)

    def handle_event(self, event):
        """处理事件"""
        if self.state == 'menu':
            self._handle_menu_event(event)
        elif self.state == 'select_side':
            self._handle_side_select_event(event)
        elif self.state == 'player_turn':
            self._handle_player_event(event)
        elif self.state == 'game_over':
            self._handle_game_over_event(event)

    # ============ 菜单事件 ============

    def _handle_menu_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            x, y = event.pos
            btn = pygame.Rect(WINDOW_WIDTH // 2 - 100, 350, 200, 60)
            if btn.collidepoint(x, y):
                self.state = 'select_side'

    def _handle_side_select_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            x, y = event.pos
            black_btn = pygame.Rect(WINDOW_WIDTH // 2 - 120, 300, 220, 60)
            if black_btn.collidepoint(x, y):
                self.reset_game('black')
                return
            white_btn = pygame.Rect(WINDOW_WIDTH // 2 - 120, 400, 220, 60)
            if white_btn.collidepoint(x, y):
                self.reset_game('white')
                return

    def _handle_game_over_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            x, y = event.pos
            btn = pygame.Rect(WINDOW_WIDTH // 2 - 100, 400, 200, 50)
            if btn.collidepoint(x, y):
                self.state = 'menu'
                self._clear_selection()
                self.message = ""

    # ============ 玩家事件 ============

    def _handle_player_event(self, event):
        if event.type != pygame.MOUSEBUTTONDOWN:
            return

        x, y = event.pos
        row, col = self._get_board_position(x, y)

        # 检查"结束回合"按钮（左键点击）
        if event.button == 1 and self.end_turn_button.collidepoint(x, y):
            self._end_player_turn()
            return

        # 点击棋盘外 → 取消选中
        if row is None or col is None:
            self._clear_selection()
            return

        # 获取点击位置的棋子
        piece = self.board.get_piece_at(row, col)

        # ===== 特殊模式：撤退 =====
        if self.action_mode == 'retreating':
            if event.button == 1:
                self._handle_retreat_click(row, col)
            elif event.button == 3:
                self._clear_selection()
                self.action_mode = 'idle'
            return

        # ===== 右键：选中 =====
        if event.button == 3:
            if piece and piece.owner == 'player':
                # 战斗中 → 检查撤退
                if piece.is_in_battle:
                    self._select_piece_for_retreat(piece)
                    return
                # 支援中 → 不能操作
                if piece.is_supporting:
                    self._clear_selection()
                    return
                # 检查是否还能行动
                if not piece.can_act():
                    self._clear_selection()
                    return
                # 正常选中
                self._select_piece(piece)
            else:
                self._clear_selection()
            return

        # ===== 左键：执行操作 =====
        if event.button == 1:
            if self.selected_piece is None:
                return
            self._handle_target_click(row, col)
            return

    def _get_board_position(self, x, y):
        rel_x = x - BOARD_OFFSET_X
        rel_y = y - BOARD_OFFSET_Y
        if rel_x < 0 or rel_y < 0:
            return None, None
        col = rel_x // CELL_SIZE
        row = rel_y // CELL_SIZE
        if row >= BOARD_SIZE or col >= BOARD_SIZE:
            return None, None
        return row, col

    # ============ 选中和清除 ============

    def _select_piece(self, piece):
        """选中一个己方棋子（正常模式）"""
        self.selected_piece = piece
        self.valid_moves = self.board.get_all_valid_moves(piece)
        self.valid_targets = []
        self.valid_bombard_targets = []
        self.valid_support_targets = []
        self.valid_retreat_positions = []
        self.action_mode = 'idle'

        # ===== 骑兵 =====
        if piece.piece_type == PieceType.CAVALRY:
            enemies = self.board.get_adjacent_enemy_pieces(piece)
            for enemy in enemies:
                # 如果敌方棋子在战斗中，不显示为攻击目标
                if not enemy.is_in_battle:
                    self.valid_targets.append((enemy.row, enemy.col))
            # 支援目标
            battles = self.battle_manager.get_all_active_battles()
            support_targets = self.board.get_available_support_targets(piece, battles)
            self.valid_support_targets = support_targets

        # ===== 炮兵 =====
        elif piece.piece_type == PieceType.ARTILLERY:
            for enemy in self.board.ai_pieces:
                if piece.can_bombard(enemy.row, enemy.col, self.board):
                    self.valid_bombard_targets.append((enemy.row, enemy.col))
            battles = self.battle_manager.get_all_active_battles()
            support_targets = self.board.get_available_support_targets(piece, battles)
            self.valid_support_targets = support_targets

        # ===== 步兵 =====
        elif piece.piece_type == PieceType.INFANTRY:
            # 生成攻击目标（相邻敌方棋子）
            enemies = self.board.get_adjacent_enemy_pieces(piece)
            for enemy in enemies:
                # 排除战斗中的敌人（支援逻辑会处理）
                if not enemy.is_in_battle:
                    self.valid_targets.append((enemy.row, enemy.col))
            # 支援目标
            battles = self.battle_manager.get_all_active_battles()
            support_targets = self.board.get_available_support_targets(piece, battles)
            self.valid_support_targets = support_targets

        # ===== 首都 =====
        elif piece.piece_type == PieceType.CAPITAL:
            battles = self.battle_manager.get_all_active_battles()
            support_targets = self.board.get_available_support_targets(piece, battles)
            self.valid_support_targets = support_targets

    def _select_piece_for_retreat(self, piece):
        """选中一个战斗中的棋子，进入撤退模式"""
        self.selected_piece = piece
        self.valid_moves = []
        self.valid_targets = []
        self.valid_bombard_targets = []
        self.valid_support_targets = []
        self.valid_retreat_positions = []
        self.action_mode = 'idle'

        for battle in self.battle_manager.get_all_active_battles():
            if battle.attacker == piece or battle.defender == piece:
                if battle.can_retreat(piece):
                    retreat_positions = battle.get_retreat_positions(piece, self.board)
                    if retreat_positions:
                        self.valid_retreat_positions = retreat_positions
                        self.action_mode = 'retreating'
                        self.message = "Left-click cyan to retreat, Right-click to cancel"
                    else:
                        self._clear_selection()
                else:
                    self._clear_selection()
                return

    def _clear_selection(self):
        """清除选中状态"""
        self.selected_piece = None
        self.valid_moves = []
        self.valid_targets = []
        self.valid_bombard_targets = []
        self.valid_support_targets = []
        self.valid_retreat_positions = []
        self.action_mode = 'idle'
        self.message = ""

    # ============ 目标点击（左键执行） ============

    def _handle_target_click(self, row, col):
        """
        处理左键点击目标
        检测顺序：轰炸 > 支援 > 攻击 > 移动
        """
        piece = self.selected_piece
        if piece is None:
            return

        # 1. 检查轰炸目标（炮兵）
        if (row, col) in self.valid_bombard_targets:
            target = self.board.get_piece_at(row, col)
            if target:
                self._execute_bombard(piece, target)
            return

        # 2. 检查支援目标（优先于攻击）
        # 点击攻击方主将或防守方主将都可以触发支援
        if self.valid_support_targets:
            for battle in self.valid_support_targets:
                if (battle.attacker.row == row and battle.attacker.col == col) or \
                   (battle.defender.row == row and battle.defender.col == col):
                    self._execute_support(piece, battle)
                    return

        # 3. 检查攻击目标（骑兵 / 步兵）
        if (row, col) in self.valid_targets:
            target = self.board.get_piece_at(row, col)
            if target:
                if piece.piece_type == PieceType.CAVALRY:
                    self._execute_cavalry_attack(piece, target)
                elif piece.piece_type == PieceType.INFANTRY:
                    self._execute_infantry_attack(piece, target, row, col)
            return

        # 4. 检查移动目标
        if (row, col) in self.valid_moves:
            self._execute_move(piece, row, col)
            return

        # 5. 检查是否点击了敌方棋子（直接攻击/轰炸）
        target = self.board.get_piece_at(row, col)
        if target and target.owner == 'ai':
            self._try_attack_or_bombard(row, col)
            return

        # 无效点击 → 取消选中
        self._clear_selection()

    def _try_attack_or_bombard(self, row, col):
        """尝试攻击或轰炸敌方棋子"""
        piece = self.selected_piece
        if piece is None:
            return

        target = self.board.get_piece_at(row, col)
        if target is None or target.owner == piece.owner:
            return

        distance = abs(piece.row - row) + abs(piece.col - col)

        # 炮兵：轰炸
        if piece.piece_type == PieceType.ARTILLERY:
            if distance <= 2 and distance > 0:
                self._execute_bombard(piece, target)
            return

        # 骑兵：攻击
        if piece.piece_type == PieceType.CAVALRY:
            if distance != 1:
                return
            self._execute_cavalry_attack(piece, target)
            return

        # 步兵：攻击
        if piece.piece_type == PieceType.INFANTRY:
            if distance != 1:
                return
            self._execute_infantry_attack(piece, target, row, col)
            return

    # ============ 执行动作 ============

    def _execute_infantry_attack(self, piece, target, target_row, target_col):
        """
        执行步兵攻击
        步兵不移动，只触发战斗（战斗在主将相邻位置进行）
        """
        # 炮兵直接摧毁（步兵不移动）
        if target.piece_type == PieceType.ARTILLERY:
            self.board.remove_piece(target)
            piece.has_acted_this_turn = True
            self.actions_used += 1
            self._clear_selection()
            self._check_game_over()
            return

        # 非炮兵：创建战斗，步兵留在原地
        battle = self.battle_manager.create_battle(piece, target, self.board)
        if battle:
            piece.has_acted_this_turn = True
            self.actions_used += 1
            self._clear_selection()
        else:
            self._clear_selection()

    def _execute_move(self, piece, target_row, target_col):
        """执行移动"""
        target = self.board.get_piece_at(target_row, target_col)

        if target and target.owner != piece.owner:
            if target.piece_type == PieceType.ARTILLERY:
                self.board.remove_piece(target)
                self.board.move_piece(piece, target_row, target_col)
                piece.has_acted_this_turn = True
                self.actions_used += 1
                self._clear_selection()
                self._check_game_over()
                return

            battle = self.battle_manager.create_battle(piece, target, self.board)
            if battle:
                self.board.move_piece(piece, target_row, target_col)
                piece.has_acted_this_turn = True
                self.actions_used += 1
                self._clear_selection()
                return
            else:
                self._clear_selection()
                return

        if self.board.move_piece(piece, target_row, target_col):
            self.actions_used += 1
            if piece.piece_type == PieceType.CAVALRY and piece.actions_used_this_turn < 2:
                self._select_piece(piece)
            else:
                self._clear_selection()

    def _execute_cavalry_attack(self, piece, target):
        """执行骑兵攻击"""
        if piece.piece_type != PieceType.CAVALRY:
            return

        if not piece.can_attack():
            self._clear_selection()
            return

        distance = abs(piece.row - target.row) + abs(piece.col - target.col)
        if distance != 1:
            self._clear_selection()
            return

        if target.owner == piece.owner:
            self._clear_selection()
            return

        if target.piece_type == PieceType.ARTILLERY:
            self.board.remove_piece(target)
            piece.has_attacked_this_turn = True
            piece.has_acted_this_turn = True
            piece.actions_used_this_turn += 1
            self.actions_used += 1
            self._clear_selection()
            self._check_game_over()
            return

        battle = self.battle_manager.create_battle(piece, target, self.board)
        if battle:
            piece.has_attacked_this_turn = True
            piece.has_acted_this_turn = True
            piece.actions_used_this_turn += 1
            self.actions_used += 1
            self._clear_selection()
        else:
            self._clear_selection()

    def _execute_bombard(self, piece, target):
        """执行炮兵远程轰炸"""
        if piece.piece_type != PieceType.ARTILLERY:
            return

        if piece.has_acted_this_turn:
            self._clear_selection()
            return

        distance = abs(piece.row - target.row) + abs(piece.col - target.col)
        if distance > 2 or distance == 0:
            self._clear_selection()
            return

        if target.owner == piece.owner:
            self._clear_selection()
            return

        damage = piece.bombard(target)
        if damage > 0:
            destroyed = target.take_damage(damage)
            if destroyed:
                self.board.remove_piece(target)

        piece.has_acted_this_turn = True
        piece.actions_used_this_turn += 1
        self.actions_used += 1
        self._clear_selection()
        self._check_game_over()

    def _execute_support(self, supporter, battle):
        """执行支援"""
        if supporter.is_in_battle or supporter.is_supporting:
            self._clear_selection()
            return

        if supporter.piece_type == PieceType.CAVALRY and supporter.has_attacked_this_turn:
            self._clear_selection()
            return

        # 确定阵营
        if battle.attacker.owner == supporter.owner:
            side = 'attacker'
            friendly_main = battle.attacker
            enemy_main = battle.defender
        elif battle.defender.owner == supporter.owner:
            side = 'defender'
            friendly_main = battle.defender
            enemy_main = battle.attacker
        else:
            self._clear_selection()
            return

        # 检查距离：与任意主将相邻即可
        support_range = supporter.get_support_range()
        dist_to_friendly = abs(supporter.row - friendly_main.row) + abs(supporter.col - friendly_main.col)
        dist_to_enemy = abs(supporter.row - enemy_main.row) + abs(supporter.col - enemy_main.col)

        if dist_to_friendly > support_range and dist_to_enemy > support_range:
            self._clear_selection()
            return

        # 执行支援
        if self.battle_manager.add_support_to_battle(battle, supporter, side):
            supporter.has_acted_this_turn = True
            supporter.actions_used_this_turn += 1
            self.actions_used += 1
            self._clear_selection()
        else:
            self._clear_selection()

    def _handle_retreat_click(self, row, col):
        """执行撤退（左键点击撤退位置）"""
        if self.action_mode != 'retreating':
            return

        if self.selected_piece is None:
            self.action_mode = 'idle'
            return

        if (row, col) in self.valid_retreat_positions:
            for battle in self.battle_manager.get_all_active_battles():
                if battle.attacker == self.selected_piece or battle.defender == self.selected_piece:
                    if battle.execute_retreat(self.selected_piece, row, col, self.board):
                        self.actions_used += 1
                        self._clear_selection()
                        self.action_mode = 'idle'
                        self._check_game_over()
                        return

        self._clear_selection()
        self.action_mode = 'idle'

    # ============ 回合管理 ============

    def _end_player_turn(self):
        self._clear_selection()

        if self.battle_manager.get_pending_count() > 0:
            self.state = 'battle_resolution'
            self.message = "Resolving battles..."
            self.message_timer = 30
            return

        self._switch_to_ai()

    def _switch_to_ai(self):
        self.state = 'ai_turn'
        self.message = "AI thinking..."
        self.actions_used = 0
        self._reset_turn_status()
        self._ai_turn()

    def _ai_turn(self):
        actions = self.ai.make_turn(self.board)

        for action in actions:
            action_type = action['action_type']

            if action_type == 'move':
                piece = action['piece']
                row, col = action['target_row'], action['target_col']
                self.board.move_piece(piece, row, col)

            elif action_type == 'move_and_attack':
                piece = action['piece']
                target = action['target']
                row, col = action['target_row'], action['target_col']
                self.board.move_piece(piece, row, col)
                if target.piece_type == PieceType.ARTILLERY:
                    self.board.remove_piece(target)
                    piece.has_attacked_this_turn = True
                    piece.has_acted_this_turn = True
                else:
                    battle = self.battle_manager.create_battle(piece, target, self.board)
                    if battle:
                        piece.has_attacked_this_turn = True
                        piece.has_acted_this_turn = True

            elif action_type == 'bombard':
                artillery = action['piece']
                target = action['target']
                damage = artillery.bombard(target)
                if damage > 0:
                    destroyed = target.take_damage(damage)
                    if destroyed:
                        self.board.remove_piece(target)
                artillery.has_acted_this_turn = True

            elif action_type == 'support':
                supporter = action['piece']
                battle = action['battle']
                side = action['side']
                if self.battle_manager.add_support_to_battle(battle, supporter, side):
                    supporter.has_acted_this_turn = True

        if self.battle_manager.get_pending_count() > 0:
            self.state = 'battle_resolution'
            self.message = "Resolving battles..."
            self.message_timer = 30
        else:
            self._resolve_battles()

    def _resolve_battles(self):
        self.battle_manager.increment_all_turns()
        self.battle_manager.resolve_all(self.board)

        if self._check_game_over():
            return

        self.state = 'player_turn'
        self.current_turn += 1
        self.actions_used = 0
        self._reset_turn_status()
        self.message = "Right-click to select, Left-click to act"

    def _check_game_over(self):
        player_capital = self.board.get_capital('player')
        ai_capital = self.board.get_capital('ai')

        if player_capital is None or player_capital.hp <= 0:
            self.winner = 'ai'
            self.state = 'game_over'
            self.message = "Game Over! AI Wins!"
            return True

        if ai_capital is None or ai_capital.hp <= 0:
            self.winner = 'player'
            self.state = 'game_over'
            self.message = "Game Over! Player Wins!"
            return True

        return False

    def update(self):
        if self.state == 'battle_resolution':
            if self.message_timer > 0:
                self.message_timer -= 1
            else:
                self._resolve_battles()

    # ============ 绘制 ============

    def draw(self):
        if self.state == 'menu':
            self._draw_menu()
        elif self.state == 'select_side':
            self._draw_side_select()
        elif self.state == 'game_over':
            self._draw_game()
            self._draw_game_over()
        else:
            self._draw_game()

    def _draw_menu(self):
        self.screen.fill(COLORS["BEIGE"])
        title = self.title_font.render("War Chess", True, COLORS["BLACK"])
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, 180))
        self.screen.blit(title, title_rect)

        subtitle = self.small_font.render("A Turn-Based Strategy Game", True, COLORS["DARK_GRAY"])
        sub_rect = subtitle.get_rect(center=(WINDOW_WIDTH // 2, 230))
        self.screen.blit(subtitle, sub_rect)

        btn = pygame.Rect(WINDOW_WIDTH // 2 - 100, 350, 200, 60)
        pygame.draw.rect(self.screen, COLORS["BLACK"], btn)
        pygame.draw.rect(self.screen, COLORS["WHITE"], btn, 2)
        btn_text = self.font.render("Start Game", True, COLORS["WHITE"])
        btn_rect = btn_text.get_rect(center=(WINDOW_WIDTH // 2, 380))
        self.screen.blit(btn_text, btn_rect)

    def _draw_side_select(self):
        self.screen.fill(COLORS["BEIGE"])
        title = self.title_font.render("Choose Your Side", True, COLORS["BLACK"])
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, 150))
        self.screen.blit(title, title_rect)

        black_btn = pygame.Rect(WINDOW_WIDTH // 2 - 120, 270, 240, 70)
        pygame.draw.rect(self.screen, COLORS["BLACK"], black_btn)
        pygame.draw.rect(self.screen, COLORS["WHITE"], black_btn, 3)
        pygame.draw.circle(self.screen, COLORS["BLACK"], (WINDOW_WIDTH // 2 - 80, 305), 20)
        pygame.draw.circle(self.screen, COLORS["WHITE"], (WINDOW_WIDTH // 2 - 80, 305), 20, 2)
        black_text = self.font.render("Black (First)", True, COLORS["WHITE"])
        black_rect = black_text.get_rect(midleft=(WINDOW_WIDTH // 2 - 45, 305))
        self.screen.blit(black_text, black_rect)

        white_btn = pygame.Rect(WINDOW_WIDTH // 2 - 120, 380, 240, 70)
        pygame.draw.rect(self.screen, COLORS["WHITE"], white_btn)
        pygame.draw.rect(self.screen, COLORS["BLACK"], white_btn, 3)
        pygame.draw.circle(self.screen, COLORS["WHITE"], (WINDOW_WIDTH // 2 - 80, 415), 20)
        pygame.draw.circle(self.screen, COLORS["BLACK"], (WINDOW_WIDTH // 2 - 80, 415), 20, 2)
        white_text = self.font.render("White (Second)", True, COLORS["BLACK"])
        white_rect = white_text.get_rect(midleft=(WINDOW_WIDTH // 2 - 45, 415))
        self.screen.blit(white_text, white_rect)

        hint = self.small_font.render("Black moves first, White moves second", True, COLORS["DARK_GRAY"])
        hint_rect = hint.get_rect(center=(WINDOW_WIDTH // 2, 500))
        self.screen.blit(hint, hint_rect)

    def _draw_game(self):
        self.screen.fill(COLORS["BEIGE"])
        self._draw_board()
        self._draw_pieces()
        self._draw_selection()
        self._draw_ui()
        self._draw_info()

    def _draw_board(self):
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                x = BOARD_OFFSET_X + col * CELL_SIZE
                y = BOARD_OFFSET_Y + row * CELL_SIZE
                if (row + col) % 2 == 0:
                    color = COLORS["BEIGE"]
                else:
                    color = COLORS["DARK_BEIGE"]
                pygame.draw.rect(self.screen, color, (x, y, CELL_SIZE, CELL_SIZE))
                pygame.draw.rect(self.screen, COLORS["GRAY"], (x, y, CELL_SIZE, CELL_SIZE), 1)

    def _draw_pieces(self):
        sorted_pieces = sorted(self.board.all_pieces, key=lambda p: (p.row, p.col))

        for piece in sorted_pieces:
            x = BOARD_OFFSET_X + piece.col * CELL_SIZE + CELL_SIZE // 2
            y = BOARD_OFFSET_Y + piece.row * CELL_SIZE + CELL_SIZE // 2
            radius = CELL_SIZE // 2 - 3

            # 绘制棋子图像
            image = self._get_piece_image(piece)
            if image:
                rect = image.get_rect(center=(x, y))
                self.screen.blit(image, rect)
            else:
                # Fallback: 圆形绘制
                color = self._get_player_color() if piece.owner == 'player' else self._get_ai_color()
                outline = self._get_player_outline() if piece.owner == 'player' else self._get_ai_outline()
                pygame.draw.circle(self.screen, color, (x, y), radius)
                pygame.draw.circle(self.screen, outline, (x, y), radius, 2)
                text = PIECE_DISPLAY_TEXT.get(piece.piece_type, "?")
                text_color = (255, 255, 255) if color == (0, 0, 0) else (0, 0, 0)
                text_surface = self.small_font.render(text, True, text_color)
                text_rect = text_surface.get_rect(center=(x, y))
                self.screen.blit(text_surface, text_rect)

            # 状态高亮圆环
            if piece.is_in_battle:
                can_ret = False
                for battle in self.battle_manager.get_all_active_battles():
                    if battle.attacker == piece or battle.defender == piece:
                        if battle.can_retreat(piece):
                            can_ret = True
                            break
                if can_ret:
                    pygame.draw.circle(self.screen, COLORS["CYAN"], (x, y), radius + 2, 4)
                else:
                    pygame.draw.circle(self.screen, COLORS["YELLOW"], (x, y), radius + 2, 3)
            if piece.is_supporting:
                pygame.draw.circle(self.screen, COLORS["ORANGE"], (x, y), radius + 2, 3)

            # HP条
            if piece.piece_type != PieceType.CAPITAL:
                self._draw_hp_bar(piece, x, y)

        # 首都HP
        for piece in self.board.all_pieces:
            if piece.piece_type == PieceType.CAPITAL:
                x = BOARD_OFFSET_X + piece.col * CELL_SIZE + CELL_SIZE // 2
                y = BOARD_OFFSET_Y + piece.row * CELL_SIZE + CELL_SIZE // 2
                self._draw_capital_hp(piece, x, y)

    def _draw_hp_bar(self, piece, x, y):
        radius = CELL_SIZE // 2 - 3
        hp_ratio = piece.hp / piece.max_hp
        hp_width = CELL_SIZE - 12
        hp_x = x - hp_width // 2
        hp_y = y + radius + 4
        pygame.draw.rect(self.screen, COLORS["DARK_GRAY"], (hp_x, hp_y, hp_width, 4))
        hp_color = COLORS["GREEN"] if hp_ratio > 0.5 else COLORS["YELLOW"] if hp_ratio > 0.25 else COLORS["RED"]
        pygame.draw.rect(self.screen, hp_color, (hp_x, hp_y, hp_width * hp_ratio, 4))

    def _draw_capital_hp(self, piece, x, y):
        radius = CELL_SIZE // 2 - 3
        hp_ratio = piece.hp / piece.max_hp
        hp_width = CELL_SIZE - 6
        hp_x = x - hp_width // 2
        hp_y = y + radius + 6
        pygame.draw.rect(self.screen, COLORS["DARK_GRAY"], (hp_x, hp_y, hp_width, 6))
        hp_color = COLORS["GREEN"] if hp_ratio > 0.5 else COLORS["YELLOW"] if hp_ratio > 0.25 else COLORS["RED"]
        pygame.draw.rect(self.screen, hp_color, (hp_x, hp_y, hp_width * hp_ratio, 6))
        hp_text = self.small_font.render(f"HP: {piece.hp}", True, COLORS["BLACK"])
        hp_text_rect = hp_text.get_rect(center=(x, y - radius - 14))
        self.screen.blit(hp_text, hp_text_rect)

    def _draw_selection(self):
        """
        绘制选中高亮和目标标记
        绘制顺序：移动 > 支援 > 攻击 > 轰炸
        """
        if self.selected_piece:
            x = BOARD_OFFSET_X + self.selected_piece.col * CELL_SIZE
            y = BOARD_OFFSET_Y + self.selected_piece.row * CELL_SIZE
            pygame.draw.rect(self.screen, COLORS["YELLOW"], (x, y, CELL_SIZE, CELL_SIZE), 3)

        # 移动目标（绿色）
        for row, col in self.valid_moves:
            x = BOARD_OFFSET_X + col * CELL_SIZE + CELL_SIZE // 2
            y = BOARD_OFFSET_Y + row * CELL_SIZE + CELL_SIZE // 2
            pygame.draw.circle(self.screen, COLORS["GREEN"], (x, y), 8, 2)

        # 支援目标（蓝色）- 同时标记攻击方和防守方主将
        for battle in self.valid_support_targets:
            # 攻击方主将
            ax = BOARD_OFFSET_X + battle.attacker.col * CELL_SIZE + CELL_SIZE // 2
            ay = BOARD_OFFSET_Y + battle.attacker.row * CELL_SIZE + CELL_SIZE // 2
            pygame.draw.circle(self.screen, COLORS["BLUE"], (ax, ay), 14, 3)
            # 防守方主将
            dx = BOARD_OFFSET_X + battle.defender.col * CELL_SIZE + CELL_SIZE // 2
            dy = BOARD_OFFSET_Y + battle.defender.row * CELL_SIZE + CELL_SIZE // 2
            pygame.draw.circle(self.screen, COLORS["BLUE"], (dx, dy), 14, 3)

        # 攻击目标（红色）- 仅显示不在战斗中的敌人
        for row, col in self.valid_targets:
            x = BOARD_OFFSET_X + col * CELL_SIZE + CELL_SIZE // 2
            y = BOARD_OFFSET_Y + row * CELL_SIZE + CELL_SIZE // 2
            pygame.draw.circle(self.screen, COLORS["RED"], (x, y), 14, 3)
            pygame.draw.circle(self.screen, COLORS["RED"], (x, y), 6, 3)

        # 轰炸目标（紫色十字准星）
        for row, col in self.valid_bombard_targets:
            x = BOARD_OFFSET_X + col * CELL_SIZE + CELL_SIZE // 2
            y = BOARD_OFFSET_Y + row * CELL_SIZE + CELL_SIZE // 2
            pygame.draw.circle(self.screen, COLORS["PURPLE"], (x, y), 14, 3)
            pygame.draw.line(self.screen, COLORS["PURPLE"], (x - 8, y), (x + 8, y), 2)
            pygame.draw.line(self.screen, COLORS["PURPLE"], (x, y - 8), (x, y + 8), 2)

        # 撤退位置（青色）
        for row, col in self.valid_retreat_positions:
            x = BOARD_OFFSET_X + col * CELL_SIZE + CELL_SIZE // 2
            y = BOARD_OFFSET_Y + row * CELL_SIZE + CELL_SIZE // 2
            pygame.draw.circle(self.screen, COLORS["CYAN"], (x, y), 14, 3)
            pygame.draw.circle(self.screen, COLORS["CYAN"], (x, y), 6, 3)

    def _draw_ui(self):
        if self.state == 'player_turn':
            turn_text = self.font.render(f"Your Turn (Round {self.current_turn})", True, COLORS["BLACK"])
        elif self.state == 'ai_turn':
            turn_text = self.font.render("AI Turn", True, COLORS["RED"])
        elif self.state == 'battle_resolution':
            turn_text = self.font.render("Resolving Battles...", True, COLORS["PURPLE"])
        else:
            turn_text = self.font.render("Game Over", True, COLORS["BLACK"])
        self.screen.blit(turn_text, (20, 20))

        if self.state == 'player_turn':
            action_text = self.font.render(f"Actions Left: {self.max_actions - self.actions_used}", True, COLORS["BLACK"])
            self.screen.blit(action_text, (20, 65))

            btn_color = COLORS["GRAY"] if self.actions_used >= self.max_actions else COLORS["BLUE"]
            pygame.draw.rect(self.screen, btn_color, self.end_turn_button)
            pygame.draw.rect(self.screen, COLORS["BLACK"], self.end_turn_button, 2)
            btn_text = self.font.render("End Turn", True, COLORS["WHITE"])
            btn_rect = btn_text.get_rect(center=self.end_turn_button.center)
            self.screen.blit(btn_text, btn_rect)

        if self.action_mode == 'retreating':
            hint = self.small_font.render("Left-click cyan to retreat, Right-click to cancel", True, COLORS["CYAN"])
            self.screen.blit(hint, (20, 105))

        player_capital = self.board.get_capital('player')
        ai_capital = self.board.get_capital('ai')
        player_color = self._get_player_color()
        ai_color = self._get_ai_color()

        if player_capital:
            hp_text = self.small_font.render(f"Player Capital HP: {player_capital.hp}", True, player_color)
            self.screen.blit(hp_text, (20, WINDOW_HEIGHT - 80))
        if ai_capital:
            hp_text = self.small_font.render(f"AI Capital HP: {ai_capital.hp}", True, ai_color)
            self.screen.blit(hp_text, (20, WINDOW_HEIGHT - 55))

        battle_count = self.battle_manager.get_pending_count()
        if battle_count > 0:
            battle_text = self.small_font.render(f"Pending Battles: {battle_count}", True, COLORS["RED"])
            self.screen.blit(battle_text, (WINDOW_WIDTH - 200, 20))

    def _draw_info(self):
        info_bg = pygame.Rect(0, WINDOW_HEIGHT - 30, WINDOW_WIDTH, 30)
        pygame.draw.rect(self.screen, COLORS["LIGHT_GRAY"], info_bg)
        pygame.draw.rect(self.screen, COLORS["GRAY"], info_bg, 1)
        info_text = self.small_font.render(self.message, True, COLORS["BLACK"])
        self.screen.blit(info_text, (10, WINDOW_HEIGHT - 25))

    def _draw_game_over(self):
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        self.screen.blit(overlay, (0, 0))

        if self.winner == 'player':
            text = "Player Wins!"
            color = COLORS["GREEN"]
        else:
            text = "AI Wins!"
            color = COLORS["RED"]

        title = self.title_font.render(text, True, color)
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, 250))
        self.screen.blit(title, title_rect)

        btn = pygame.Rect(WINDOW_WIDTH // 2 - 100, 400, 200, 50)
        pygame.draw.rect(self.screen, COLORS["WHITE"], btn)
        pygame.draw.rect(self.screen, COLORS["BLACK"], btn, 2)
        btn_text = self.font.render("Main Menu", True, COLORS["BLACK"])
        btn_rect = btn_text.get_rect(center=(WINDOW_WIDTH // 2, 425))
        self.screen.blit(btn_text, btn_rect)