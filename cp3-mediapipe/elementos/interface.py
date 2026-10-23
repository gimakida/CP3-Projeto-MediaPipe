"""Desenho da interface sobre o frame da câmera."""
import cv2

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


def desenhar(frame, jogo):
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
        if est.mao is None:
            continue
        xs = [p.x for p in est.mao.pontos]
        topo = min(p.y for p in est.mao.pontos)
        centro = (int(sum(xs) / len(xs) * w), int(topo * h) - 25)
        escala = 1.6 if est.aberta else 1.0   # maior quando o elemento está sendo exibido
        _texto(frame, est.elemento.nome, centro, escala, est.elemento.cor_bgr)

    if jogo.mensagem:
        _texto(frame, jogo.mensagem, (w // 2, h - 40), 1.0, (0, 255, 255))
    cv2.putText(frame, "q: sair", (w - 110, h - 15), FONTE, 0.5, (200, 200, 200), 1)
