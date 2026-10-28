"""Reconhecimento de gestos a partir dos landmarks das mãos."""
import json
import math

from . import config
from .hand_tracker import Mao

# índices dos landmarks do MediaPipe Hands
PULSO = 0
PONTA_DEDOS = [8, 12, 16, 20]
PIP_DEDOS = [6, 10, 14, 18]
BASE_INDICADOR, BASE_MINDINHO = 5, 17

# Calibração de palma/costas por mão ("Left"/"Right"): None = ainda não calibrada,
# True = inverter a decisão do cálculo geométrico, False = usar como está.
_INVERSAO = {"Left": config.INVERTER_PALMA, "Right": config.INVERTER_PALMA}


def calibrado(lado: str) -> bool:
    return _INVERSAO[lado] is not None


def carregar_calibracao() -> bool:
    """Lê assets/calibracao.json (se existir). Retorna True se havia calibração salva."""
    try:
        dados = json.loads(config.ARQUIVO_CALIBRACAO.read_text())
        for lado in _INVERSAO:
            if isinstance(dados.get(lado), bool):
                _INVERSAO[lado] = dados[lado]
        return True
    except (OSError, ValueError, AttributeError):
        return False


def _salvar_calibracao():
    try:
        config.ARQUIVO_CALIBRACAO.write_text(json.dumps(_INVERSAO))
    except OSError as e:
        print("Não consegui salvar a calibração:", e)


def definir_palma(mao: "Mao"):
    """O usuário garante que está mostrando a PALMA: ajusta a inversão dessa mão (esquerda
    ou direita) para que a leitura atual passe a ser 'palma', e salva em arquivo."""
    _INVERSAO[mao.lado] = not _palma_geometrica(mao)
    _salvar_calibracao()


def calibrar_palma(maos) -> str:
    """Tecla 'c': recalibra imediatamente as mãos visíveis (todas mostrando a PALMA)."""
    if not maos:
        return "Calibracao: mostre a PALMA de uma mao para a camera"
    for mao in maos:
        definir_palma(mao)
    nomes = {"Left": "esquerda", "Right": "direita"}
    return "Calibrado: mao " + " e ".join(nomes[m.lado] for m in maos)


carregar_calibracao()


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


def _palma_geometrica(mao: Mao) -> bool:
    """Palma ou costas segundo a geometria, SEM a calibração do usuário.

    Em 2D uma mão esquerda de palma e uma direita de costas têm o mesmo formato,
    então usamos dois dados juntos:
      1. o rótulo Left/Right do MediaPipe (qual mão é);
      2. o sinal do produto vetorial pulso->base do indicador x pulso->base do mindinho,
         que diz se o polegar fica "antes" ou "depois" do mindinho na imagem.
    Mão direita com a palma para a câmera (imagem espelhada): polegar à esquerda
    -> produto vetorial positivo. A mão esquerda é o espelho disso.
    """
    p = mao.pontos
    v1 = (p[BASE_INDICADOR].x - p[PULSO].x, p[BASE_INDICADOR].y - p[PULSO].y)
    v2 = (p[BASE_MINDINHO].x - p[PULSO].x, p[BASE_MINDINHO].y - p[PULSO].y)
    cruz = v1[0] * v2[1] - v1[1] * v2[0]
    palma = cruz > 0 if mao.lado == "Right" else cruz < 0
    if not config.ESPELHAR:      # imagem sem espelho inverte a geometria
        palma = not palma
    return palma


def virada_para_camera(mao: Mao) -> bool:
    """True se a PALMA está voltada para a câmera; False se são as COSTAS da mão
    (já considerando a calibração feita pelo usuário)."""
    return _palma_geometrica(mao) != bool(_INVERSAO[mao.lado])


def palma_para_cima(mao: Mao) -> bool:
    """Palma voltada para a câmera, com a mão aberta."""
    return virada_para_camera(mao) and mao_aberta(mao)


def distancia_palmas(maos: list[Mao]) -> float:
    """Distância entre os centros das duas palmas, em 'tamanhos de mão' (1 = palmas coladas)."""
    a, b = maos[0], maos[1]
    ca, cb = centro_palma(a), centro_palma(b)
    escala = (tamanho_mao(a) + tamanho_mao(b)) / 2
    return math.hypot(ca[0] - cb[0], ca[1] - cb[1]) / escala


def palmas(maos: list[Mao]) -> bool:
    """True se duas mãos estão juntas (palmas das mãos próximas)."""
    return len(maos) >= 2 and distancia_palmas(maos) < config.LIMIAR_PALMAS


class Estabilizador:
    """Confirma um gesto só depois de N frames consecutivos (reduz ruído)."""

    def __init__(self, frames: int = config.FRAMES_ESTAVEIS):
        self.frames, self.cont = frames, 0

    def atualizar(self, ativo: bool) -> bool:
        self.cont = self.cont + 1 if ativo else 0
        return self.cont >= self.frames
