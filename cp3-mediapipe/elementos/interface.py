"""Desenho da interface sobre o frame da câmera."""
import cv2

from . import config, gestos
from .jogo import LADOS, NOMES_LADO

FONTE = cv2.FONT_HERSHEY_SIMPLEX


def _texto(frame, texto, centro, escala, cor, espessura=3):
    """Texto centrado, com contorno preto para ficar legível sobre qualquer fundo."""
    (tw, th), _ = cv2.getTextSize(texto, FONTE, escala, espessura)
    x = max(5, min(frame.shape[1] - tw - 5, centro[0] - tw // 2))
    y = max(th + 5, centro[1])
    cv2.putText(frame, texto, (x, y), FONTE, escala, (0, 0, 0), espessura + 4, cv2.LINE_AA)
    cv2.putText(frame, texto, (x, y), FONTE, escala, cor, espessura, cv2.LINE_AA)


def _bolha(frame, centro, raio, elemento):
    cv2.circle(frame, centro, raio, elemento.cor_bgr, -1)
    cv2.circle(frame, centro, raio, (255, 255, 255), 2)


def desenhar(frame, jogo, debug=False):
    h, w = frame.shape[:2]
    # barra superior: elemento escolhido em cada mão
    cv2.rectangle(frame, (0, 0), (w, 110), (0, 0, 0), -1)
    for i, lado in enumerate(LADOS):
        est = jogo.estados[lado]
        x = 40 + i * 300
        cv2.putText(frame, f"Mao {NOMES_LADO[lado]}", (x, 30), FONTE, 0.6, (200, 200, 200), 1, cv2.LINE_AA)
        _bolha(frame, (x + 28, 68), 24, est.elemento)
        cv2.putText(frame, est.elemento.nome, (x + 65, 78), FONTE, 0.9, (255, 255, 255), 2, cv2.LINE_AA)
    if jogo.resultado:
        cv2.putText(frame, "Ultima criacao", (w - 300, 30), FONTE, 0.6, (200, 200, 200), 1, cv2.LINE_AA)
        _bolha(frame, (w - 270, 68), 24, jogo.resultado)
        cv2.putText(frame, jogo.resultado.nome, (w - 235, 78), FONTE, 0.9, (255, 255, 255), 2, cv2.LINE_AA)

    # nome do elemento bem visível acima de cada mão
    for est in jogo.estados.values():
        if jogo.precisa_calibrar(est):
            topo = min(pt.y for pt in est.mao.pontos)
            xs = [pt.x for pt in est.mao.pontos]
            centro = (int(sum(xs) / len(xs) * w), int(topo * h) - 50)
            pct = int(100 * est.calib / config.FRAMES_CALIBRACAO)
            _texto(frame, "CALIBRANDO: mostre a PALMA", centro, 0.8, (0, 255, 255), 2)
            _texto(frame, f"aberta, de frente para a camera  {pct}%", (centro[0], centro[1] + 30), 0.6, (255, 255, 255), 2)
            continue
        if est.mao is None or jogo.segurando:   # com o elemento fundido, só o nome dele aparece
            continue
        xs = [p.x for p in est.mao.pontos]
        topo = min(p.y for p in est.mao.pontos)
        centro = (int(sum(xs) / len(xs) * w), int(topo * h) - 25)
        escala = 1.6 if est.aberta else 1.0   # maior quando o elemento está sendo exibido
        _texto(frame, est.elemento.nome, centro, escala, est.elemento.cor_bgr)

    # elemento fundido preso às mãos: nome acima dele
    if jogo.segurando and jogo.resultado:
        centro = (int(jogo.fusao_pos[0] * w), max(150, int(jogo.fusao_pos[1] * h) - 150))
        _texto(frame, jogo.resultado.nome, centro, 1.8, jogo.resultado.cor_bgr)
        _texto(frame, "mantenha as maos fechadas; abra e afaste para soltar", (w // 2, h - 80), 0.7, (255, 255, 255), 2)

    if debug:
        for lado, est in jogo.estados.items():
            if est.mao is None:
                continue
            p = est.mao.pontos[0]
            texto = (f"{lado} | {'PALMA' if gestos.virada_para_camera(est.mao) else 'COSTAS'}"
                     f" | dedos {gestos.dedos_estendidos(est.mao)}")
            _texto(frame, texto, (int(p.x * w), int(p.y * h) + 40), 0.6, (0, 255, 0), 2)

    if jogo.mensagem:
        _texto(frame, jogo.mensagem, (w // 2, h - 40), 1.0, (0, 255, 255))
    cv2.putText(frame, "q: sair   d: depurar   c: calibrar palma", (w - 400, h - 15), FONTE, 0.5, (200, 200, 200), 1)
