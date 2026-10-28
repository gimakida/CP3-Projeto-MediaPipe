"""Liga o estado do jogo aos efeitos visuais e ao som ambiente."""
from . import gestos
from .efeitos import Emissor
from .jogo import LADOS


class Cena:
    def __init__(self, audio):
        self.audio = audio
        self.emissores = {lado: Emissor() for lado in LADOS}
        self.emissor_fusao = Emissor()

    def atualizar_e_desenhar(self, frame, jogo, dt: float):
        h, w = frame.shape[:2]

        estilos = {}
        # Um efeito por mão, colado na palma e proporcional à abertura dela
        for canal, lado in enumerate(LADOS):
            est, emissor = jogo.estados[lado], self.emissores[lado]
            mostrando = est.exibindo
            origem, escala = None, 1.0
            if mostrando:
                emissor.trocar_estilo(est.elemento.estilo)
                cx, cy = gestos.centro_palma(est.mao_ref)
                origem = (cx * w, cy * h)
                escala = 0.6 + 1.0 * gestos.abertura(est.mao_ref)
            emissor.atualizar(dt, origem, escala, mostrando)
            emissor.desenhar(frame, escala)
            if mostrando:
                estilos[canal] = est.elemento.estilo

        # Elemento criado pela fusão: fica preso às mãos (no ponto médio) enquanto estiverem fechadas
        fusao_ativa = jogo.resultado is not None and jogo.segurando
        if fusao_ativa:
            self.emissor_fusao.trocar_estilo(jogo.resultado.estilo)
        pos = (jogo.fusao_pos[0] * w, jogo.fusao_pos[1] * h) if jogo.fusao_pos else None
        self.emissor_fusao.atualizar(dt, pos, 1.5, fusao_ativa)
        self.emissor_fusao.desenhar(frame, 1.5)
        # Sons: se as duas mãos mostram o mesmo elemento, toca um só (não dobra o mesmo som)
        compartilhado = len(estilos) == 2 and estilos[0] == estilos[1]
        if compartilhado:
            del estilos[1]
        for canal in (0, 1):
            self.audio.ambiente(canal, estilos.get(canal))
        # o elemento fundido também tem o seu som, enquanto o efeito dura
        self.audio.ambiente(2, jogo.resultado.estilo if fusao_ativa else None)
        self.audio.ajustar_mistura(len(estilos) + fusao_ativa, compartilhado)
