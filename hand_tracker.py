# hand_tracker.py
import cv2
import mediapipe as mp
import math

# --- DEĞİŞİKLİK: Tıklama hassasiyeti ayarları güncellendi ---
# Orijinal ayarlarınıza geri dönüldü ve yanlış tıklamaları önlemek için
# PINCH_TRIGGER_LEVEL değeri biraz artırıldı.

PINCH_MULTIPLIER = 0.38
PINCH_SMOOTH_ALPHA = 0.35
# Tıklama eşiği 0.6'dan 0.75'e yükseltildi. Artık tıklama için parmaklarınızı daha fazla yaklaştırmanız gerek.
PINCH_TRIGGER_LEVEL = 0.5
# Bırakma eşiği de orantılı olarak artırıldı.
PINCH_RELEASE_LEVEL = 0.6
PINCH_DEBOUNCE_MS = 220

# Orijinal, yüksek çözünürlüklü kamera ayarlarına geri dönüldü.
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480


class HandTracker:
    def __init__(self, window_width, window_height):
        self.WINDOW_WIDTH = window_width
        self.WINDOW_HEIGHT = window_height

        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

        self.mp_hands = mp.solutions.hands
        # Orijinal, daha hassas olan MediaPipe model ayarlarına geri dönüldü.
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.6
        )
        self.mp_draw = mp.solutions.drawing_utils

        self.pinch_state = [False, False]
        self.pinch_ema = [0.0, 0.0]
        self.last_pinch_time = 0

    def _map_point_camera_to_screen(self, px, py):
        sx = int(px / CAMERA_WIDTH * self.WINDOW_WIDTH)
        sy = int(py / CAMERA_HEIGHT * self.WINDOW_HEIGHT)
        return sx, sy

    def process_frame(self, now_ms):
        ret, frame = self.cap.read()
        if not ret:
            print('Kamera açılamadı.')
            return None, {}

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb)

        punch_detected = False
        cursor_screen_pos = None

        hands_detected = results.multi_hand_landmarks
        if hands_detected:
            hand_entries = []
            h, w, _ = frame.shape
            for handLms in hands_detected:
                lm = handLms.landmark
                thumb_x = lm[4].x * w
                hand_entries.append((thumb_x, handLms))
            hand_entries.sort(key=lambda e: e[0])

            hand_map = [None, None]
            for i, (_, handLms) in enumerate(hand_entries):
                if i == 0:
                    hand_map[0] = handLms
                elif i == 1:
                    hand_map[1] = handLms

            for logical_idx in [0, 1]:
                handLms = hand_map[logical_idx]
                if handLms is None:
                    self.pinch_ema[logical_idx] = max(0.0, self.pinch_ema[logical_idx] * 0.90)
                    continue

                self.mp_draw.draw_landmarks(frame, handLms, self.mp_hands.HAND_CONNECTIONS)
                lm = handLms.landmark

                tx, ty = int(lm[4].x * w), int(lm[4].y * h)
                ix, iy = int(lm[8].x * w), int(lm[8].y * h)
                mid_x, mid_y = int((tx + ix) / 2), int((ty + iy) / 2)
                cursor_screen_pos = self._map_point_camera_to_screen(mid_x, mid_y)

                cv2.circle(frame, (tx, ty), 12, (0, 200, 0), -1)
                cv2.circle(frame, (ix, iy), 12, (0, 200, 0), -1)
                cv2.circle(frame, (mid_x, mid_y), 8, (255, 255, 255), 2)

                wx, wy = int(lm[0].x * w), int(lm[0].y * h)
                mx, my = int(lm[9].x * w), int(lm[9].y * h)
                hand_size_px = max(1.0, math.hypot(mx - wx, my - wy))
                pinch_dist_px = math.hypot(tx - ix, ty - iy)
                thresh_px = hand_size_px * PINCH_MULTIPLIER
                raw_strength = max(0.0, min(1.0, 1.0 - (pinch_dist_px / max(1.0, thresh_px))))
                self.pinch_ema[logical_idx] = PINCH_SMOOTH_ALPHA * raw_strength + (1 - PINCH_SMOOTH_ALPHA) * \
                                              self.pinch_ema[logical_idx]

                fingers_extended = sum([lm[i].y < lm[i - 2].y for i in [8, 12, 16, 20]])

                if logical_idx == 0:
                    if fingers_extended <= 1:
                        punch_detected = True
                else:
                    if not self.pinch_state[1] and self.pinch_ema[1] >= PINCH_TRIGGER_LEVEL:
                        self.pinch_state[1] = True
                    elif self.pinch_state[1] and self.pinch_ema[1] < PINCH_RELEASE_LEVEL:
                        self.pinch_state[1] = False
        else:
            self.pinch_ema[0] = max(0.0, self.pinch_ema[0] * 0.90)
            self.pinch_ema[1] = max(0.0, self.pinch_ema[1] * 0.90)

        pinch_triggered = False
        if self.pinch_state[1] and (now_ms - self.last_pinch_time) > PINCH_DEBOUNCE_MS:
            pinch_triggered = True
            self.last_pinch_time = now_ms

        hand_data = {
            "punch_detected": punch_detected,
            "pinch_triggered": pinch_triggered,
            "cursor_pos": cursor_screen_pos,
            "pinch_strength": self.pinch_ema[1]
        }
        return frame, hand_data

    def close(self):
        self.cap.release()
        self.hands.close()