# game_state.py
import pygame
import random

# Oyun ayarları ve fizik sabitleri
GRAVITY = 1.5
JUMP_VELOCITY = -13
PIPE_SPEED = 8
PIPE_GAP = 180
PIPE_WIDTH = 90
PIPE_INTERVAL_MS = 2500
SHIELD_DURATION_MS = 3000
SHIELD_COOLDOWN_MS = 10000


class Bird:
    def __init__(self, x, y, image):
        self.x = x
        self.y = y
        self.vel = 0.0
        self.image = image
        self.rect = self.image.get_rect(center=(self.x, self.y))
        self.mask = pygame.mask.from_surface(self.image)
        self.shield_active = False
        self.shield_end_time = 0

    def update(self):
        self.vel += GRAVITY
        self.y += self.vel
        self.rect.center = (int(self.x), int(self.y))

    def jump(self, multiplier=1.0):
        self.vel = JUMP_VELOCITY * multiplier

    def draw(self, surf):
        surf.blit(self.image, self.rect)


class Pipe:
    def __init__(self, x, window_height):
        self.x = x
        self.width = PIPE_WIDTH
        self.gap = PIPE_GAP
        self.gap_y = random.randint(150, window_height - 250 - self.gap)  # Kenarlara daha az yakın
        self.passed = False
        self.window_height = window_height

        # --- PERFORMANS DÜZELTMESİ: Rect ve Mask'lar burada, BİR KEZ oluşturulur ---
        self.rect_upper = pygame.Rect(self.x, 0, self.width, self.gap_y)
        self.rect_lower = pygame.Rect(self.x, self.gap_y + self.gap, self.width,
                                      self.window_height - (self.gap_y + self.gap))

        self.mask_upper = pygame.mask.Mask((int(self.width), int(self.gap_y)), fill=True) if self.gap_y > 0 else None

        lower_top = self.gap_y + self.gap
        h_lower = self.window_height - lower_top
        self.mask_lower = pygame.mask.Mask((int(self.width), int(h_lower)), fill=True) if h_lower > 0 else None

    def update(self):
        self.x -= PIPE_SPEED
        # Rect'lerin pozisyonunu da güncelle
        self.rect_upper.x = int(self.x)
        self.rect_lower.x = int(self.x)

    def off_screen(self):
        return self.x + self.width < -10

    def draw(self, surf):
        # Çizim için de artık önceden oluşturulmuş Rect'leri kullanıyoruz
        pygame.draw.rect(surf, (34, 139, 34), self.rect_upper)
        pygame.draw.rect(surf, (0, 128, 0), self.rect_lower)


class GameState:
    def __init__(self, bird_image, window_width, window_height):
        self.WINDOW_WIDTH = window_width
        self.WINDOW_HEIGHT = window_height
        self.bird_img = bird_image
        self.reset_game()

    def reset_game(self):
        self.bird = Bird(180, self.WINDOW_HEIGHT // 2, self.bird_img)
        self.pipes = []
        self.score = 0
        self.max_score = getattr(self, 'max_score', 0)
        self.shield_charges = 3
        self.game_started = False
        self.game_over = False
        self.last_pipe_time = pygame.time.get_ticks() - PIPE_INTERVAL_MS
        self.last_shield_time = -SHIELD_COOLDOWN_MS
        self.slow_motion_end = 0

    def start_new_game(self):
        self.game_started = True
        self.game_over = False
        self.score = 0
        self.pipes.clear()
        self.bird = Bird(180, self.WINDOW_HEIGHT // 2, self.bird_img)
        self.last_pipe_time = pygame.time.get_ticks()
        self.bird.shield_active = False
        self.last_shield_time = -SHIELD_COOLDOWN_MS
        self.shield_charges = 3

    def update_game_logic(self):
        now_ms = pygame.time.get_ticks()

        if self.bird.shield_active and now_ms >= self.bird.shield_end_time:
            self.bird.shield_active = False

        if not self.game_started or self.game_over:
            return

        if now_ms - self.last_pipe_time > PIPE_INTERVAL_MS:
            self.pipes.append(Pipe(self.WINDOW_WIDTH + 20, self.WINDOW_HEIGHT))
            self.last_pipe_time = now_ms

        self.bird.update()

        for p in self.pipes:
            p.update()
            if not p.passed and p.x + p.width < self.bird.x:
                p.passed = True
                self.score += 1
                if self.score > self.max_score:
                    self.max_score = self.score

        self.pipes = [p for p in self.pipes if not p.off_screen()]

        if not self.bird.shield_active:
            self.check_collisions()  # Ayrı bir fonksiyona taşıdık
            # Sınır çarpışması
            if self.bird.y - 8 <= 0 or self.bird.y + 8 >= self.WINDOW_HEIGHT - 70:
                self.game_over = True

    def check_collisions(self):
        # --- PERFORMANS DÜZELTMESİ: İki Aşamalı Çarpışma Kontrolü ---
        for p in self.pipes:
            # 1. Aşama: Hızlı Rect çarpışma kontrolü
            if self.bird.rect.colliderect(p.rect_upper) or self.bird.rect.colliderect(p.rect_lower):
                # 2. Aşama: Sadece Rect'ler çarpışıyorsa yavaş ve hassas Mask kontrolü yap
                offset_upper = (int(p.rect_upper.x - self.bird.rect.left), int(p.rect_upper.y - self.bird.rect.top))
                if p.mask_upper and self.bird.mask.overlap(p.mask_upper, offset_upper):
                    self.game_over = True
                    return  # Çarpışma bulundu, döngüden çık

                offset_lower = (int(p.rect_lower.x - self.bird.rect.left), int(p.rect_lower.y - self.bird.rect.top))
                if p.mask_lower and self.bird.mask.overlap(p.mask_lower, offset_lower):
                    self.game_over = True
                    return  # Çarpışma bulundu, döngüden çık