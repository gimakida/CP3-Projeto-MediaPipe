"""Estado do jogo: cada mão escolhe o seu elemento; palmas funde os dois."""
import time
from dataclasses import dataclass, field

from . import config, elementos, gestos
from .audio import Audio

LADOS = ("Left", "Right")
NOMES_LADO = {"Left": "Esquerda", "Right": "Direita"}


@dataclass
class EstadoMao:
    indice: int                       # elemento atual desta mão (índice em BASICOS)
    mao: object = None                # landmarks atuais (None se a mão sumiu)
    aberta: bool = False              # palma aberta confirmada: elemento visível
    estava_aberta: bool = False
    est_aberta: gestos.Estabilizador = field(default_factory=gestos.Estabilizador)
    est_fechada: gestos.Estabilizador = field(default_factory=gestos.Estabilizador)

    @property
    def elemento(self):
        return elementos.BASICOS[self.indice]


class Jogo:
    def __init__(self, audio: Audio):
        self.audio = audio
        # cada mão começa com um elemento diferente
        self.estados = {"Left": EstadoMao(indice=0), "Right": EstadoMao(indice=1)}
        self.resultado = None           # último elemento criado pela fusão
        self.mensagem = ""
        self.fusao_pos = None           # (x, y) normalizado do efeito da fusão
        self.fusao_ate = 0.0
        self._mensagem_ate = 0.0
        self._ultima_palma = 0.0
        self._est_palmas = gestos.Estabilizador()

    def _aviso(self, texto, seg=2.0):
        self.mensagem, self._mensagem_ate = texto, time.time() + seg

    @staticmethod
    def _atribuir_lados(maos) -> dict:
        """Associa cada mão a 'Left'/'Right'. Se o MediaPipe rotular as duas igual,
        desempata pela posição na imagem."""
        if len(maos) == 2 and maos[0].lado == maos[1].lado:
            a, b = sorted(maos, key=lambda m: gestos.centro_palma(m)[0])
            esq, dir_ = (a, b) if config.ESPELHAR else (b, a)
            return {"Left": esq, "Right": dir_}
        return {m.lado: m for m in maos}

    def atualizar(self, maos):
        agora = time.time()
        if agora > self._mensagem_ate:
            self.mensagem = ""
        por_lado = self._atribuir_lados(maos)
        for lado, est in self.estados.items():
            est.mao = por_lado.get(lado)

        # Palmas: funde os elementos das duas mãos
        if self._est_palmas.atualizar(gestos.palmas(maos)):
            for est in self.estados.values():
                est.aberta = est.estava_aberta = False
            if agora - self._ultima_palma > config.COOLDOWN_PALMAS_S:
                self._ultima_palma = agora
                ca, cb = gestos.centro_palma(maos[0]), gestos.centro_palma(maos[1])
                self.fusao_pos = ((ca[0] + cb[0]) / 2, (ca[1] + cb[1]) / 2)
                self._fundir()
            return

        for est in self.estados.values():
            if est.mao is None:
                est.aberta = est.estava_aberta = False
                est.est_aberta.cont = est.est_fechada.cont = 0
                continue
            est.aberta = est.est_aberta.atualizar(gestos.palma_para_cima(est.mao))
            fechada = est.est_fechada.atualizar(gestos.mao_fechada(est.mao))
            if fechada and est.estava_aberta:
                # abrir e fechar a mão troca o elemento desta mão
                est.indice = (est.indice + 1) % len(elementos.BASICOS)
                est.estava_aberta = False
                self.audio.tocar("troca")
            if est.aberta:
                est.estava_aberta = True

    def _fundir(self):
        a, b = (self.estados[l].elemento for l in LADOS)
        novo = elementos.fundir(a, b)
        if novo is None:
            self.audio.tocar("erro")
            self._aviso(f"{a.nome} + {b.nome}: fusao impossivel!")
        else:
            self.resultado = novo
            self.fusao_ate = time.time() + config.DURACAO_EFEITO_FUSAO_S
            self.audio.tocar("fusao")
            self._aviso(f"{a.nome} + {b.nome} = {novo.nome}", 3.0)
