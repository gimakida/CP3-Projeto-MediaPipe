"""Efeitos visuais de partículas para cada elemento (inspirado no reel de referência).

Cada elemento tem um Estilo; o mesmo emissor desenha fogo, água, terra, ar e
os elementos fundidos. Para criar um novo visual, basta adicionar um Estilo.
"""
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class Estilo:
    cores: tuple            # gradiente BGR do nascimento até o fim da vida
    taxa: float = 160       # partículas por segundo (escala 1)
    vida: float = 0.9       # segundos
    tamanho: float = 22     # raio inicial em px (escala 1)
    velocidade: float = 160 # px/s para cima (negativo = cai)
    espalhamento: float = 50
    gravidade: float = 0.0  # px/s² (positivo = cai)
    turbulencia: float = 60 # oscilação lateral
    giro: float = 0.0       # rotação ao redor do centro (rad/s), p/ ar e tempestade
    encolhe: bool = True    # raio diminui com a idade
    brilho: bool = True     # soma de luz (fogo); False = pintura opaca (terra, lama)


ESTILOS = {
    "fogo": Estilo(((60, 255, 255), (0, 180, 255), (0, 60, 255), (20, 20, 120))),
    "agua": Estilo(((255, 240, 200), (255, 170, 60), (200, 90, 20)),
                   taxa=140, vida=1.1, tamanho=12, velocidade=-60, gravidade=420,
                   espalhamento=90, turbulencia=40, encolhe=False),
    "terra": Estilo(((80, 140, 180), (50, 100, 140), (30, 60, 90)),
                    taxa=70, vida=1.3, tamanho=14, velocidade=-40, gravidade=500,
                    espalhamento=80, turbulencia=20, encolhe=False, brilho=False),
    "ar": Estilo(((255, 255, 255), (230, 220, 200), (170, 160, 150)),
                 taxa=120, vida=1.2, tamanho=8, velocidade=40, espalhamento=30,
                 turbulencia=30, giro=5.0, encolhe=False),
    "vapor": Estilo(((255, 255, 255), (220, 215, 210), (150, 150, 150)),
                    taxa=90, vida=1.6, tamanho=28, velocidade=110, turbulencia=40),
    "lava": Estilo(((0, 220, 255), (0, 90, 255), (0, 30, 150)),
                   taxa=110, vida=1.2, tamanho=20, velocidade=70, gravidade=160,
                   espalhamento=70, turbulencia=30),
    "lama": Estilo(((60, 100, 130), (40, 70, 95), (25, 45, 60)),
                   taxa=80, vida=1.2, tamanho=16, velocidade=30, gravidade=380,
                   espalhamento=70, turbulencia=20, encolhe=False, brilho=False),
    "fumaca": Estilo(((170, 170, 170), (110, 110, 110), (50, 50, 50)),
                     taxa=90, vida=1.8, tamanho=26, velocidade=120, turbulencia=70,
                     brilho=False),
    "tempestade": Estilo(((255, 230, 200), (200, 160, 110), (120, 90, 60)),
                         taxa=200, vida=1.0, tamanho=10, velocidade=20,
                         espalhamento=120, turbulencia=90, giro=7.0, encolhe=False),
    "poeira": Estilo(((170, 200, 215), (130, 165, 190), (90, 120, 145)),
                     taxa=130, vida=1.5, tamanho=9, velocidade=50, espalhamento=100,
                     turbulencia=80, giro=2.0, encolhe=False),
}


def _cor(estilo: Estilo, t: np.ndarray) -> np.ndarray:
    """Cor (N,3) interpolada no gradiente para t em [0,1]."""
    g = np.array(estilo.cores, dtype=np.float32)
    x = t * (len(g) - 1)
    i = np.clip(x.astype(int), 0, len(g) - 2)
    f = (x - i)[:, None]
    return g[i] * (1 - f) + g[i + 1] * f


class Emissor:
    """Sistema de partículas vetorizado com NumPy, ancorado em um ponto (a palma)."""

    MAX = 600

    def __init__(self):
        self.estilo = None
        self.pos = np.zeros((0, 2), np.float32)
        self.vel = np.zeros((0, 2), np.float32)
        self.idade = np.zeros(0, np.float32)
        self.vida = np.zeros(0, np.float32)
        self.fase = np.zeros(0, np.float32)
        self._resto = 0.0
        self._rng = np.random.default_rng()

    def trocar_estilo(self, estilo: Estilo | None):
        if estilo is not self.estilo:
            self.estilo = estilo
            self.pos = self.pos[:0]; self.vel = self.vel[:0]
            self.idade = self.idade[:0]; self.vida = self.vida[:0]; self.fase = self.fase[:0]

    def atualizar(self, dt: float, origem, escala: float, ativo: bool):
        e = self.estilo
        if e is None:
            return
        if ativo and origem is not None:
            self._resto += e.taxa * escala * dt
            n = min(int(self._resto), self.MAX - len(self.idade))
            self._resto -= int(self._resto)
            if n > 0:
                r = self._rng
                novos = np.array(origem, np.float32) + r.normal(0, 18 * escala, (n, 2)).astype(np.float32)
                v = np.stack([r.normal(0, e.espalhamento, n),
                              -e.velocidade * escala + r.normal(0, e.espalhamento * 0.3, n)], 1)
                self.pos = np.vstack([self.pos, novos])
                self.vel = np.vstack([self.vel, v.astype(np.float32)])
                self.idade = np.append(self.idade, np.zeros(n, np.float32))
                self.vida = np.append(self.vida, (e.vida * r.uniform(0.7, 1.2, n)).astype(np.float32))
                self.fase = np.append(self.fase, r.uniform(0, 6.28, n).astype(np.float32))
        if not len(self.idade):
            return
        self.idade += dt
        self.vel[:, 1] += e.gravidade * dt
        self.vel[:, 0] += np.sin(self.idade * 9 + self.fase) * e.turbulencia * dt * 6
        if e.giro and origem is not None:
            dx = self.pos[:, 0] - origem[0]; dy = self.pos[:, 1] - origem[1]
            self.vel[:, 0] += -dy * e.giro * dt * 3
            self.vel[:, 1] += dx * e.giro * dt * 3
        self.pos += self.vel * dt
        vivos = self.idade < self.vida
        self.pos, self.vel = self.pos[vivos], self.vel[vivos]
        self.idade, self.vida, self.fase = self.idade[vivos], self.vida[vivos], self.fase[vivos]

    def desenhar(self, frame, escala: float):
        e = self.estilo
        if e is None or not len(self.idade):
            return
        h, w = frame.shape[:2]
        tela = np.zeros_like(frame) if e.brilho else frame  # opaco: pinta direto no frame
        t = self.idade / self.vida
        cores = _cor(e, t)
        raios = e.tamanho * escala * ((1 - 0.7 * t) if e.encolhe else np.ones_like(t))
        for (x, y), r, c in zip(self.pos, raios, cores):
            cv2.circle(tela, (int(x), int(y)), max(1, int(r)), c.tolist(), -1)
        if e.brilho:
            tela = cv2.GaussianBlur(tela, (0, 0), 6 * max(escala, 0.5))
            cv2.add(frame, tela, dst=frame)
