"""Constantes e parâmetros ajustáveis do projeto."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DEBUG_SOM = True   # imprime no terminal cada som tocado (útil para diagnosticar)
# volume dos sons ambiente conforme quantos tocam ao mesmo tempo (1, 2 ou 3)
GANHO_AMBIENTE_JUNTOS = {1: 1.0, 2: 0.45, 3: 0.35}
DUCK_FATOR = 0.3          # volume dos ambientes enquanto um efeito curto (troca/fusao/erro) toca
DUCK_S = {"troca": 0.35, "fusao": 1.2, "erro": 0.9}   # quanto tempo cada efeito abaixa os ambientes
DUCK_VOLTA_S = 0.5        # tempo para os ambientes voltarem ao volume normal
INTERVALO_MIN_EFEITO_S = 0.25   # o mesmo efeito não toca de novo antes disso
PASTA_SONS = RAIZ / "assets" / "sons"
MODELO_MAOS = RAIZ / "assets" / "modelos" / "hand_landmarker.task"

CAMERA_INDICE = 0
LARGURA, ALTURA = 1280, 720
ESPELHAR = True  # imagem em espelho, mais natural para o usuário

NUM_MAOS = 2
INVERTER_PALMA = None   # None = o jogo pede uma calibração na primeira vez (salva em ARQUIVO_CALIBRACAO); True/False força
ARQUIVO_CALIBRACAO = RAIZ / "assets" / "calibracao.json"
CONFIANCA_DETECCAO = 0.6
CONFIANCA_RASTREIO = 0.5

# Gestos
LIMIAR_DEDO_ESTENDIDO = 1.15   # dist(ponta, pulso) / dist(articulação PIP, pulso)
MIN_DEDOS_MAO_ABERTA = 4
MAX_DEDOS_MAO_FECHADA = 1
LIMIAR_PALMAS = 1.5            # distância entre as palmas / tamanho da mão
FRAMES_CALIBRACAO = 25         # quadros mostrando a palma aberta para calibrar (~1 s)
FRAMES_PALMAS = 2              # quadros com as mãos juntas para confirmar as palmas
FRAMES_OCLUSAO = 8             # se uma mão some logo depois de se aproximar, conta como palmas
LIMIAR_PRE_PALMAS = 2.2        # distância máxima (em tamanhos de mão) da última vez que as duas apareceram
FRAMES_GRACA = 6               # quadros em que o efeito continua se a mão some ou o gesto falha
LIMIAR_SOLTAR = 2.0            # distância entre as mãos para soltar o elemento fundido
FRAMES_UMA_MAO = 90            # quadros com uma só mão visível (3 s) para soltar o elemento fundido
FRAMES_ESTAVEIS = 4            # frames seguidos para confirmar um gesto
COOLDOWN_PALMAS_S = 1.5
FRAMES_SOLTAR = 10             # quadros com as mãos abertas e separadas para soltar o elemento fundido
FRAMES_SEM_MAOS = 45           # quadros sem nenhuma mão para soltar o elemento fundido
SUAVIZACAO_SEGUIR = 0.35       # 0-1: quão rápido o elemento fundido acompanha as mãos

