# main.py
import pygame
import sys
from game_state import GameState, SHIELD_DURATION_MS, SHIELD_COOLDOWN_MS
from hand_tracker import HandTracker
from ui_manager import UIManager

# Ayarlar
WINDOW_WIDTH, WINDOW_HEIGHT = 1440, 960
FPS = 60


def main():
    # Sınıfları başlat
    ui = UIManager(WINDOW_WIDTH, WINDOW_HEIGHT)
    game = GameState(ui.bird_img, WINDOW_WIDTH, WINDOW_HEIGHT)
    tracker = HandTracker(WINDOW_WIDTH, WINDOW_HEIGHT)
    clock = pygame.time.Clock()

    running = True
    while running:
        now_ms = pygame.time.get_ticks()

        # El hareketlerini işle
        cam_frame, hand_data = tracker.process_frame(now_ms)
        if cam_frame is None:
            running = False
            continue

        hand_data["frame"] = cam_frame

        # Pygame olaylarını işle
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    if not game.game_started or game.game_over:
                        game.start_new_game()
                    else:
                        game.bird.jump()

        # El hareketi girdilerini işle
        # Buton tıklamaları
        if hand_data["pinch_triggered"]:
            cursor_pos = hand_data["cursor_pos"]
            if cursor_pos:
                if not game.game_started and ui.start_button.collidepoint(cursor_pos):
                    game.start_new_game()
                elif game.game_over and ui.restart_button.collidepoint(cursor_pos):
                    game.start_new_game()
                # Oyun içi zıplama
                elif game.game_started and not game.game_over:
                    game.bird.jump()

        # Kalkan aktivasyonu
        if hand_data["punch_detected"] and game.game_started and not game.game_over:
            if game.shield_charges > 0 and now_ms - game.last_shield_time >= SHIELD_COOLDOWN_MS:
                game.shield_charges -= 1
                game.bird.shield_active = True
                game.bird.shield_end_time = now_ms + SHIELD_DURATION_MS
                game.last_shield_time = now_ms

        # Oyun mantığını güncelle
        game.update_game_logic()

        # Her şeyi ekrana çiz
        ui.draw_all(game, hand_data, now_ms)

        clock.tick(FPS)

    # Temizlik
    tracker.close()
    pygame.quit()
    sys.exit()


if __name__ == '__main__':
    main()