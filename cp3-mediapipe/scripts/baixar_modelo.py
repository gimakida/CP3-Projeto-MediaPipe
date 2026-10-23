"""Baixa o modelo hand_landmarker.task do MediaPipe para assets/modelos/."""
from pathlib import Path
from urllib.request import urlretrieve

URL = ("https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
       "hand_landmarker/float16/latest/hand_landmarker.task")
DESTINO = Path(__file__).resolve().parent.parent / "assets" / "modelos" / "hand_landmarker.task"

if __name__ == "__main__":
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    if DESTINO.exists():
        print("Modelo já existe:", DESTINO)
    else:
        urlretrieve(URL, DESTINO)
        print("Modelo salvo em", DESTINO)
