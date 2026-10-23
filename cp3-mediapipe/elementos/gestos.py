"""Reconhecimento de gestos a partir dos landmarks das mãos."""
import math

from . import config
from .hand_tracker import Mao

# índices dos landmarks do MediaPipe Hands
PULSO = 0
PONTA_DEDOS = [8, 12, 16, 20]
PIP_DEDOS = [6, 10, 14, 18]
BASE_INDICADOR, BASE_MINDINHO = 5, 17


def _dist(a, b) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def tamanho_mao(mao: Mao) -> float:
    return _dist(mao.pontos[PULSO], mao.pontos[9]) + 1e-6


def centro_palma(mao: Mao) -> tuple[float, float]:
    ids = [PULSO, BASE_INDICADOR, 9, 13, BASE_MINDINHO]
    return (sum(mao.pontos[i].x for i in ids) / 5,
            sum(mao.pontos[i].y for i in ids) / 5)


def dedos_estendidos(mao: Mao) -> int:
    """Conta indicador, médio, anelar e mindinho estendidos (polegar ignorado)."""
    p = mao.pontos
    return sum(
        _dist(p[ponta], p[PULSO]) > config.LIMIAR_DEDO_ESTENDIDO * _dist(p[pip], p[PULSO])
        for ponta, pip in zip(PONTA_DEDOS, PIP_DEDOS))


def abertura(mao: Mao) -> float:
    """Quão aberta está a mão (0 = fechada, ~1 = bem aberta). Controla o tamanho do efeito."""
    p = mao.pontos
    cx, cy = centro_palma(mao)
    media = sum(math.hypot(p[i].x - cx, p[i].y - cy) for i in (4, 8, 12, 16, 20)) / 5
    return max(0.0, min(1.0, (media / tamanho_mao(mao) - 0.6) / 0.9))


def mao_aberta(mao: Mao) -> bool:
    return dedos_estendidos(mao) >= config.MIN_DEDOS_MAO_ABERTA


def mao_fechada(mao: Mao) -> bool:
    return dedos_estendidos(mao) <= config.MAX_DEDOS_MAO_FECHADA


def palma_para_cima(mao: Mao) -> bool:
    """Palma voltada para a câmera, com a mão aberta (dedos para cima).

    Usa o produto vetorial pulso->base do indicador x pulso->base do mindinho;
    o sinal depende de a mão ser esquerda ou direita. TODO: calibrar com a
    câmera real e, se a ideia for palma realmente "para o teto", usar o eixo z.
    """
    p = mao.pontos
    v1 = (p[BASE_INDICADOR].x - p[PULSO].x, p[BASE_INDICADOR].y - p[PULSO].y)
    v2 = (p[BASE_MINDINHO].x - p[PULSO].x, p[BASE_MINDINHO].y - p[PULSO].y)
    cruz = v1[0] * v2[1] - v1[1] * v2[0]
    voltada_camera = cruz > 0 if mao.lado == "Right" else cruz < 0
    return voltada_camera and mao_aberta(mao)


def palmas(maos: list[Mao]) -> bool:
    """True se duas mãos estão juntas (palmas das mãos próximas)."""
    if len(maos) < 2:
        return False
    a, b = maos[0], maos[1]
    ca, cb = centro_palma(a), centro_palma(b)
    d = math.hypot(ca[0] - cb[0], ca[1] - cb[1])
    escala = (tamanho_mao(a) + tamanho_mao(b)) / 2
    return d / escala < config.LIMIAR_PALMAS


class Estabilizador:
    """Confirma um gesto só depois de N frames consecutivos (reduz ruído)."""

    def __init__(self, frames: int = config.FRAMES_ESTAVEIS):
        self.frames, self.cont = frames, 0

    def atualizar(self, ativo: bool) -> bool:
        self.cont = self.cont + 1 if ativo else 0
        return self.cont >= self.frames
