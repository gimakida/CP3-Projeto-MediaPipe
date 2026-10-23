"""Constantes e parâmetros ajustáveis do projeto."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DEBUG_SOM = True   # imprime no terminal cada som tocado (útil para diagnosticar)
# volume dos sons ambiente conforme quantos tocam ao mesmo tempo (1, 2 ou 3)
GANHO_AMBIENTE_JUNTOS = {1: 1.0, 2: 0.55, 3: 0.4}
PASTA_SONS = RAIZ / "assets" / "sons"
MODELO_MAOS = RAIZ / "assets" / "modelos" / "hand_landmarker.task"

CAMERA_INDICE = 0
LARGURA, ALTURA = 1280, 720
ESPELHAR = True  # imagem em espelho, mais natural para o usuário

NUM_MAOS = 2
CONFIANCA_DETECCAO = 0.6
CONFIANCA_RASTREIO = 0.5

# Gestos
LIMIAR_DEDO_ESTENDIDO = 1.15   # dist(ponta, pulso) / dist(articulação PIP, pulso)
MIN_DEDOS_MAO_ABERTA = 4
MAX_DEDOS_MAO_FECHADA = 1
LIMIAR_PALMAS = 1.2            # distância entre as palmas / tamanho da mão
FRAMES_ESTAVEIS = 4            # frames seguidos para confirmar um gesto
COOLDOWN_PALMAS_S = 1.5
DURACAO_EFEITO_FUSAO_S = 4.0   # quanto tempo o efeito do elemento fundido fica na tela

