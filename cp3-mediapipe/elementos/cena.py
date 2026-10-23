"""Liga o estado do jogo aos efeitos visuais e ao som ambiente."""
import time

from . import gestos
from .efeitos import ESTILOS, Emissor
from .jogo import LADOS


class Cena:
    def __init__(self, audio):
        self.audio = audio
        self.emissores = {lado: Emissor() for lado in LADOS}
        self.emissor_fusao = Emissor()

    def atualizar_e_desenhar(self, frame, jogo, dt: float):
        h, w = frame.shape[:2]

        tocando = 0
        # Um efeito por mão, colado na palma e proporcional à abertura dela
        for canal, lado in enumerate(LADOS):
            est, emissor = jogo.estados[lado], self.emissores[lado]
            mostrando = est.aberta and est.mao is not None
            origem, escala = None, 1.0
            if mostrando:
                emissor.trocar_estilo(ESTILOS[est.elemento.estilo])
                cx, cy = gestos.centro_palma(est.mao)
                origem = (cx * w, cy * h)
                escala = 0.6 + 1.0 * gestos.abertura(est.mao)
            emissor.atualizar(dt, origem, escala, mostrando)
            emissor.desenhar(frame, escala)
            self.audio.ambiente(canal, est.elemento.estilo if mostrando else None)
            tocando += mostrando

        # Efeito do elemento criado pela fusão, onde as mãos se juntaram
        fusao_ativa = jogo.resultado is not None and time.time() < jogo.fusao_ate
        if fusao_ativa:
            self.emissor_fusao.trocar_estilo(ESTILOS[jogo.resultado.estilo])
        pos = (jogo.fusao_pos[0] * w, jogo.fusao_pos[1] * h) if jogo.fusao_pos else None
        self.emissor_fusao.atualizar(dt, pos, 1.5, fusao_ativa)
        self.emissor_fusao.desenhar(frame, 1.5)
        # o elemento fundido também tem o seu som, enquanto o efeito dura
        self.audio.ambiente(2, jogo.resultado.estilo if fusao_ativa else None)
        self.audio.ajustar_mistura(tocando + fusao_ativa)
