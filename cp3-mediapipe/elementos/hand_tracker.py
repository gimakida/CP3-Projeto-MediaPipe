"""Detecção de mãos com MediaPipe Tasks (HandLandmarker)."""
from dataclasses import dataclass

import cv2
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions, vision

from . import config


@dataclass
class Mao:
    pontos: list      # 21 landmarks normalizados (x, y, z)
    lado: str         # "Left" / "Right" (já considerando o espelhamento)


class HandTracker:
    def __init__(self):
        if not config.MODELO_MAOS.exists():
            raise FileNotFoundError(
                f"Modelo não encontrado: {config.MODELO_MAOS}\n"
                "Rode: python scripts/baixar_modelo.py")
        opcoes = vision.HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(config.MODELO_MAOS)),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=config.NUM_MAOS,
            min_hand_detection_confidence=config.CONFIANCA_DETECCAO,
            min_tracking_confidence=config.CONFIANCA_RASTREIO,
        )
        self._detector = vision.HandLandmarker.create_from_options(opcoes)

    def detectar(self, frame_bgr, timestamp_ms: int) -> list[Mao]:
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        imagem = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        res = self._detector.detect_for_video(imagem, timestamp_ms)
        maos = []
        for pontos, handed in zip(res.hand_landmarks, res.handedness):
            lado = handed[0].category_name
            if config.ESPELHAR:  # o frame já foi espelhado antes da detecção
                lado = "Left" if lado == "Right" else "Right"
            maos.append(Mao(pontos=pontos, lado=lado))
        return maos

    def fechar(self):
        self._detector.close()

    @staticmethod
    def desenhar(frame, maos: list[Mao]):
        h, w = frame.shape[:2]
        ligacoes = vision.HandLandmarksConnections.HAND_CONNECTIONS
        for mao in maos:
            for c in ligacoes:
                a, b = mao.pontos[c.start], mao.pontos[c.end]
                cv2.line(frame, (int(a.x * w), int(a.y * h)),
                         (int(b.x * w), int(b.y * h)), (255, 255, 255), 1)
            for p in mao.pontos:
                cv2.circle(frame, (int(p.x * w), int(p.y * h)), 5, (0, 0, 0), -1)
