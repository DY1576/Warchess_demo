"""
main.py - 程序入口
"""

import pygame
import sys
from game import Game
from Constant import WINDOW_WIDTH, WINDOW_HEIGHT, FPS


def main():
    pygame.init()

    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("战争象棋 - War Chess")

    game = Game(screen)
    clock = pygame.time.Clock()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break
            game.handle_event(event)

        if not running:
            break

        game.update()
        game.draw()
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()