# ui_manager.py
import pygame
import cv2


class UIManager:
    def __init__(self, width, height):
        self.WINDOW_WIDTH = width
        self.WINDOW_HEIGHT = height

        pygame.init()
        self.screen = pygame.display.set_mode((self.WINDOW_WIDTH, self.WINDOW_HEIGHT))
        pygame.display.set_caption('Socitek Fly')
        self.font = pygame.font.SysFont(None, 36)
        self.big_font = pygame.font.SysFont(None, 64)

        self.bird_img, self.bg = self._load_assets()
        self._create_pre_rendered_surfaces()

        self.start_button = pygame.Rect(self.WINDOW_WIDTH // 2 - 120, self.WINDOW_HEIGHT // 2 - 40, 240, 80)
        self.restart_button = pygame.Rect(self.WINDOW_WIDTH // 2 - 150, self.WINDOW_HEIGHT // 2 + 20, 300, 80)
        self.cam_w, self.cam_h = 280, 210
        self.cam_pos = (self.WINDOW_WIDTH - self.cam_w - 16, 12)

    def _load_assets(self):
        bird_img = pygame.image.load("bg/logo.png").convert_alpha()
        bird_img = pygame.transform.smoothscale(bird_img, (100, 100))
        bg = pygame.image.load("bg/background.png").convert()
        bg = pygame.transform.scale(bg, (self.WINDOW_WIDTH, self.WINDOW_HEIGHT))
        return bird_img, bg

    def _create_pre_rendered_surfaces(self):
        # Shield surface
        SHIELD_SURF_SIZE = 96
        self.shield_surf = pygame.Surface((SHIELD_SURF_SIZE, SHIELD_SURF_SIZE), pygame.SRCALPHA)
        shield_radius = SHIELD_SURF_SIZE // 2 - 6
        shield_color = (80, 200, 255, 110)
        pygame.draw.circle(self.shield_surf, shield_color, (SHIELD_SURF_SIZE // 2, SHIELD_SURF_SIZE // 2),
                           shield_radius)
        pygame.draw.circle(self.shield_surf, (0, 120, 160, 160), (SHIELD_SURF_SIZE // 2, SHIELD_SURF_SIZE // 2),
                           shield_radius, width=4)

        # Heart icon
        self.heart_img = pygame.Surface((20, 20), pygame.SRCALPHA)
        pygame.draw.polygon(self.heart_img, (255, 80, 100), [(10, 3), (17, 8), (17, 14), (10, 18), (3, 14), (3, 8)])
        self.faded_heart = self.heart_img.copy()
        self.faded_heart.fill((255, 255, 255, 60), None, pygame.BLEND_RGBA_MULT)

    def draw_all(self, game_state, hand_data, now_ms):
        # Background
        self.screen.blit(self.bg, (0, 0))

        # Pipes and Bird
        for p in game_state.pipes:
            p.draw(self.screen)
        game_state.bird.draw(self.screen)

        # Shield effect
        if game_state.bird.shield_active:
            blit_pos = (game_state.bird.rect.centerx - self.shield_surf.get_width() // 2,
                        game_state.bird.rect.centery - self.shield_surf.get_height() // 2)
            self.screen.blit(self.shield_surf, blit_pos)

        # HUD (Heads-Up Display)
        self._draw_hud(game_state, now_ms)

        # Start/Game Over screens
        if not game_state.game_started:
            self._draw_start_screen(hand_data['cursor_pos'])
        if game_state.game_over:
            self._draw_game_over_screen(game_state.score, hand_data['cursor_pos'])

        # Camera and cursor
        self._draw_camera_and_cursor(hand_data)

        pygame.display.flip()

    def _draw_hud(self, game_state, now_ms):
        score_surf = self.font.render(f"Skor {game_state.score}", True, (255, 255, 255))
        max_surf = self.font.render(f"Maksimum Skor: {game_state.max_score}", True, (255, 215, 0))
        self.screen.blit(score_surf, (12, 12))
        self.screen.blit(max_surf, (12, 52))

        # Shield charges (hearts)
        for i in range(3):
            x = 12 + i * 28
            y = 130
            if i < game_state.shield_charges:
                self.screen.blit(self.heart_img, (x, y))
            else:
                self.screen.blit(self.faded_heart, (x, y))

        # Shield timer/cooldown
        if game_state.bird.shield_active:
            remaining_ms = game_state.bird.shield_end_time - now_ms
            remaining_s = max(0, remaining_ms // 100) / 10
            shield_text = self.font.render(f"Kalkan: {remaining_s:.1f} sn", True, (80, 200, 255))
            self.screen.blit(shield_text, (12, 92))
        else:
            from game_state import SHIELD_COOLDOWN_MS
            cooldown_remaining = (SHIELD_COOLDOWN_MS - (now_ms - game_state.last_shield_time)) / 1000
            if cooldown_remaining > 0:
                cd_text = self.font.render(f"Kalkan: Hazır değil ({cooldown_remaining:.1f}s)", True, (150, 150, 150))
                self.screen.blit(cd_text, (12, 92))

    def _draw_start_screen(self, cursor_pos):
        btn_color, hover_color = (70, 130, 180), (80, 200, 120)
        is_hover = cursor_pos is not None and self.start_button.collidepoint(cursor_pos)
        pygame.draw.rect(self.screen, hover_color if is_hover else btn_color, self.start_button, border_radius=12)
        label = self.big_font.render('BAŞLA', True, (255, 255, 255))
        self.screen.blit(label, (self.start_button.centerx - label.get_width() // 2,
                                 self.start_button.centery - label.get_height() // 2))

    def _draw_game_over_screen(self, score, cursor_pos):
        over = self.big_font.render('KAYBETTİN', True, (255, 60, 60))
        self.screen.blit(over, (self.WINDOW_WIDTH // 2 - over.get_width() // 2, self.WINDOW_HEIGHT // 2 - 140))
        sub = self.font.render(f'Skorun: {score}', True, (255, 255, 255))
        self.screen.blit(sub, (self.WINDOW_WIDTH // 2 - sub.get_width() // 2, self.WINDOW_HEIGHT // 2 - 80))
        btn_color, hover_color = (178, 34, 34), (255, 69, 0)
        is_hover = cursor_pos is not None and self.restart_button.collidepoint(cursor_pos)
        pygame.draw.rect(self.screen, hover_color if is_hover else btn_color, self.restart_button, border_radius=12)
        label = self.font.render('YENİDEN OYNA', True, (255, 255, 255))
        self.screen.blit(label, (self.restart_button.centerx - label.get_width() // 2,
                                 self.restart_button.centery - label.get_height() // 2))

    def _draw_camera_and_cursor(self, hand_data):
        frame = hand_data.get('frame')
        cursor_pos = hand_data.get('cursor_pos')
        pinch_strength = hand_data.get('pinch_strength')

        if frame is not None:
            try:
                small = cv2.resize(frame, (self.cam_w, self.cam_h))
                small_rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
                cam_surf = pygame.image.frombuffer(small_rgb.tobytes(), small_rgb.shape[1::-1], 'RGB')
                border_rect = pygame.Rect(self.cam_pos[0] - 4, self.cam_pos[1] - 4, self.cam_w + 8, self.cam_h + 8)
                pygame.draw.rect(self.screen, (30, 30, 30), border_rect, border_radius=8)
                self.screen.blit(cam_surf, self.cam_pos)
            except Exception:
                pass

        if cursor_pos is not None:
            pygame.draw.circle(self.screen, (255, 255, 255), cursor_pos, 10, 3)
            arc_radius = 22
            pygame.draw.circle(self.screen, (0, 200, 0), cursor_pos, int(arc_radius * pinch_strength), 2)