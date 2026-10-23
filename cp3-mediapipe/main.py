"""Jogo de elementos com MediaPipe Hands. Execute: python main.py"""
import time

import cv2

from elementos import config, interface
from elementos.cena import Cena
from elementos.audio import Audio
from elementos.hand_tracker import HandTracker
from elementos.jogo import Jogo


def main():
    cap = cv2.VideoCapture(config.CAMERA_INDICE)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.LARGURA)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.ALTURA)
    if not cap.isOpened():
        raise SystemExit("Não foi possível abrir a câmera.")

    tracker = HandTracker()
    audio = Audio()
    jogo = Jogo(audio)
    cena = Cena(audio)
    audio.tocar("troca")  # confirma que o som funciona ao abrir o jogo
    inicio = ultimo = time.time()
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if config.ESPELHAR:
                frame = cv2.flip(frame, 1)
            maos = tracker.detectar(frame, int((time.time() - inicio) * 1000))
            jogo.atualizar(maos)
            # fundo em tons de cinza, como no vídeo de referência
            frame = cv2.cvtColor(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)
            agora = time.time()
            cena.atualizar_e_desenhar(frame, jogo, agora - ultimo)
            ultimo = agora
            tracker.desenhar(frame, maos)
            interface.desenhar(frame, jogo)
            cv2.imshow("Jogo de Elementos", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        tracker.fechar()
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
