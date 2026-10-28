"""Estado do jogo: cada mão escolhe o seu elemento; palmas funde os dois."""
import time
from collections import deque
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
    calib: int = 0                    # quadros seguidos mostrando a palma aberta (calibração)
    ultima: object = None             # última leitura da mão (usada durante a tolerância)
    sumiu: int = 0                    # quadros seguidos sem detectar esta mão
    graca: int = 0                    # quadros restantes de tolerância para continuar exibindo

    @property
    def elemento(self):
        return elementos.BASICOS[self.indice]

    @property
    def exibindo(self) -> bool:
        """O efeito do elemento deve aparecer: palma aberta, ou pouco depois de perdê-la
        (a detecção falha de vez em quando, principalmente quando as mãos se aproximam)."""
        return self.graca > 0 and self.mao_ref is not None

    @property
    def mao_ref(self):
        return self.mao if self.mao is not None else self.ultima


class Jogo:
    def __init__(self, audio: Audio):
        self.audio = audio
        # cada mão começa com um elemento diferente
        self.estados = {"Left": EstadoMao(indice=0), "Right": EstadoMao(indice=1)}
        self.resultado = None           # último elemento criado pela fusão
        self.mensagem = ""
        self.fusao_pos = None           # (x, y) normalizado: onde o elemento fundido está
        self.segurando = False          # elemento fundido preso às mãos
        self._sem_maos = 0
        self._soltando = 0
        self._uma_mao = 0
        self._deslocamento = {}         # por mão: onde está o ponto médio em relação a ela
        self._quadro = 0
        self._duas = None               # última vez em que as duas mãos foram vistas
        self._dist_hist = deque(maxlen=3)
        self._mensagem_ate = 0.0
        self._ultima_palma = 0.0
        self._est_palmas = gestos.Estabilizador(config.FRAMES_PALMAS)

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
        self._quadro += 1
        por_lado = self._atribuir_lados(maos)
        for lado, est in self.estados.items():
            est.mao = por_lado.get(lado)
            if est.mao is not None:
                est.ultima, est.sumiu = est.mao, 0
            else:
                est.sumiu += 1

        # Elemento fundido nas mãos: acompanha as mãos até elas se abrirem e separarem
        if self.segurando:
            self._atualizar_segurando(maos, por_lado)
            return

        # Palmas: funde os elementos das duas mãos
        pos = self._detectar_palmas(maos)
        if pos is not None:
            for est in self.estados.values():
                est.aberta = est.estava_aberta = False
                est.graca = 0
            if agora - self._ultima_palma > config.COOLDOWN_PALMAS_S:
                self._ultima_palma = agora
                self.fusao_pos = pos
                self._fundir()
            return

        for est in self.estados.values():
            if est.mao is None:
                # mão sumiu: continua exibindo por alguns quadros (tolerância) e depois zera
                est.graca = max(0, est.graca - 1)
                if est.sumiu > config.FRAMES_GRACA:
                    est.aberta = est.estava_aberta = False
                    est.est_aberta.cont = est.est_fechada.cont = 0
                    est.calib = 0
                continue
            if not gestos.calibrado(est.mao.lado):
                est.graca = 0
                self._calibrar(est)
                continue
            est.aberta = est.est_aberta.atualizar(gestos.palma_para_cima(est.mao))
            fechada = est.est_fechada.atualizar(gestos.mao_fechada(est.mao))
            if est.aberta:
                est.graca = config.FRAMES_GRACA
            else:
                est.graca = max(0, est.graca - 1)
            if fechada and est.estava_aberta:
                # abrir e fechar a mão troca o elemento desta mão
                est.indice = (est.indice + 1) % len(elementos.BASICOS)
                est.estava_aberta = False
                est.graca = 0
                self.audio.tocar("troca")
            if est.aberta:
                est.estava_aberta = True

    def _detectar_palmas(self, maos):
        """Retorna a posição (x, y normalizado) das palmas, ou None se não houve palmas.

        Quando as mãos se juntam, o MediaPipe costuma perder uma delas (a outra a cobre).
        Por isso, se as duas estavam se aproximando e uma some logo em seguida, também conta."""
        if len(maos) >= 2:
            d = gestos.distancia_palmas(maos)
            ca, cb = gestos.centro_palma(maos[0]), gestos.centro_palma(maos[1])
            meio = ((ca[0] + cb[0]) / 2, (ca[1] + cb[1]) / 2)
            self._duas = {"quadro": self._quadro, "dist": d, "pos": meio, "usado": False}
            self._dist_hist.append(d)
            return meio if self._est_palmas.atualizar(d < config.LIMIAR_PALMAS) else None
        self._est_palmas.atualizar(False)
        u = self._duas
        if u and not u["usado"] and self._quadro - u["quadro"] <= config.FRAMES_OCLUSAO:
            hist = list(self._dist_hist)
            aproximando = len(hist) >= 2 and hist[-1] <= hist[-2] + 0.02
            if u["dist"] < config.LIMIAR_PRE_PALMAS and aproximando:
                u["usado"] = True
                return u["pos"]
        return None

    def _fundir(self):
        a, b = (self.estados[l].elemento for l in LADOS)
        novo = elementos.fundir(a, b)
        self._duas = None
        if novo is None:
            self.audio.tocar("erro")
            self._aviso(f"{a.nome} + {b.nome}: fusao impossivel!")
        else:
            self.resultado = novo
            self.segurando = True
            self._sem_maos = self._soltando = self._uma_mao = 0
            self._deslocamento = {}
            self.audio.tocar("fusao")
            self._aviso(f"{a.nome} + {b.nome} = {novo.nome}", 3.0)

    def _atualizar_segurando(self, maos, por_lado):
        """O elemento criado segue o ponto médio das mãos. Se a detecção perder uma mão
        (comum com as mãos juntas), ele continua seguindo a outra, mantendo a distância
        que havia. Só é solto com as duas mãos abertas e afastadas, ou sem mãos por muito tempo."""
        for est in self.estados.values():
            est.aberta = est.estava_aberta = False
            est.graca = 0
        if not maos:
            self._sem_maos += 1
            if self._sem_maos > config.FRAMES_SEM_MAOS:
                self._soltar()
            return          # mantém a última posição
        self._sem_maos = 0
        centros = {lado: gestos.centro_palma(m) for lado, m in por_lado.items()}
        if len(centros) >= 2:
            alvo = (sum(c[0] for c in centros.values()) / len(centros),
                    sum(c[1] for c in centros.values()) / len(centros))
            self._deslocamento = {l: (alvo[0] - c[0], alvo[1] - c[1]) for l, c in centros.items()}
        else:
            lado, c = next(iter(centros.items()))
            dx, dy = self._deslocamento.get(lado, (0.0, 0.0))
            alvo = (c[0] + dx, c[1] + dy)
        suave = config.SUAVIZACAO_SEGUIR   # média móvel para o efeito não tremer
        self.fusao_pos = (self.fusao_pos[0] + (alvo[0] - self.fusao_pos[0]) * suave,
                          self.fusao_pos[1] + (alvo[1] - self.fusao_pos[1]) * suave)

        if len(maos) >= 2:
            self._uma_mao = 0
            fechada = any(gestos.mao_fechada(m) for m in maos)
            if fechada or gestos.distancia_palmas(maos) < config.LIMIAR_SOLTAR:
                self._soltando = 0
            else:
                self._soltando += 1
                if self._soltando >= config.FRAMES_SOLTAR:
                    self._soltar()
        else:
            self._uma_mao += 1          # a outra mão deve estar coberta: continua segurando
            if self._uma_mao > config.FRAMES_UMA_MAO:
                self._soltar()

    def _soltar(self):
        self.segurando = False
        self._est_palmas.cont = 0
        self._duas = None
        self._ultima_palma = time.time()
        self._aviso(f"{self.resultado.nome} solto!", 1.5)

    def precisa_calibrar(self, est) -> bool:
        return est.mao is not None and not gestos.calibrado(est.mao.lado)

    def _calibrar(self, est):
        """Primeira vez com esta mão: pede para mostrar a PALMA aberta e aprende com isso."""
        est.aberta = est.estava_aberta = False
        est.calib = est.calib + 1 if gestos.mao_aberta(est.mao) else 0
        if est.calib >= config.FRAMES_CALIBRACAO:
            gestos.definir_palma(est.mao)
            est.calib = 0
            nome = NOMES_LADO[est.mao.lado].lower()
            self._aviso(f"Mao {nome} calibrada!", 2.5)
