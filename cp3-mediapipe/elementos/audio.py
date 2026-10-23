"""Sons do jogo; falha silenciosa se não houver áudio.

Para usar seus próprios sons, coloque arquivos (.wav, .ogg ou .mp3) em assets/sons/:
  troca, fusao, erro            efeitos curtos
  ambiente_<estilo>             loop enquanto o elemento aparece (ex.: ambiente_fogo,
                                ambiente_agua, ambiente_vapor; estilos em efeitos.ESTILOS)
Os que faltarem continuam usando o som sintético abaixo.
"""
import numpy as np

from . import config

try:
    import pygame
except ImportError:  # pragma: no cover
    pygame = None

TAXA = 22050
EXTENSOES = (".wav", ".ogg", ".mp3")


def _arquivo(nome: str):
    if not config.PASTA_SONS.is_dir():
        return None
    for f in config.PASTA_SONS.iterdir():
        if f.stem.lower() == nome and f.suffix.lower() in EXTENSOES:
            return f
    return None


def _tom(freqs, dur=0.15, vol=0.4):
    sons = []
    for f in freqs:
        t = np.linspace(0, dur, int(TAXA * dur), False)
        onda = np.sin(2 * np.pi * f * t) * np.linspace(1, 0, t.size)
        sons.append(onda)
    onda = np.concatenate(sons) * vol
    return (onda * 32767).astype(np.int16)


def _ruido(dur=2.0, suavizar=1, vol=0.3, pulso=0.0, seed=0):
    """Ruído filtrado em loop. `suavizar` maior = som mais grave; `pulso` > 0 dá estalos."""
    rng = np.random.default_rng(seed)
    n = int(TAXA * dur)
    x = rng.normal(0, 1, n)
    if suavizar > 1:
        x = np.convolve(x, np.ones(suavizar) / suavizar, mode="same")
    if pulso:
        x *= 0.4 + (rng.random(n) < pulso) * 2.0
    x = x / (np.abs(x).max() + 1e-6) * vol
    fade = np.linspace(0, 1, 400)
    x[:400] *= fade; x[-400:] *= fade[::-1]
    return (x * 32767).astype(np.int16)


# (suavizar, volume, pulso): fogo estala, água/ar são chiados, terra é grave
AMBIENTES = {
    "fogo": (2, 0.35, 0.004), "agua": (4, 0.3, 0.0), "terra": (40, 0.5, 0.0),
    "ar": (8, 0.25, 0.0), "vapor": (6, 0.25, 0.0), "lava": (20, 0.4, 0.002),
    "lama": (25, 0.35, 0.001), "fumaca": (12, 0.2, 0.0),
    "tempestade": (3, 0.35, 0.0), "poeira": (10, 0.2, 0.0),
}


class Audio:
    def __init__(self):
        self.ativo = False
        if pygame is None:
            print("Áudio desativado: pygame não está instalado. Rode: pip install pygame-ce")
            return
        try:
            pygame.mixer.init(frequency=TAXA, size=-16, channels=2)  # estéreo: cada mão sai mais por um lado
            pygame.mixer.set_reserved(3)  # canais 0 e 1: ambiente de cada mão; 2: elemento fundido
            self._sons = {
                "troca": self._carregar("troca", _tom([523, 659], 0.1)),
                "fusao": self._carregar("fusao", _tom([392, 523, 659, 784], 0.14)),
                "erro": self._carregar("erro", _tom([180, 140], 0.25, 0.5)),
            }
            self._sons["troca"].set_volume(0.6)  # discreto, para não encobrir o ambiente
            self._ambientes = {
                k: self._carregar(f"ambiente_{k}", _ruido(suavizar=s, vol=v, pulso=p))
                for k, (s, v, p) in AMBIENTES.items()}
            self._tocando = {0: None, 1: None, 2: None}
            self._ganho = 1.0
            self.ativo = True
            self._relatar_arquivos()
            print("Áudio ativo:", pygame.mixer.get_init())
        except Exception as e:  # sem dispositivo de áudio
            print("Áudio desativado:", e)

    def _relatar_arquivos(self):
        """Diagnóstico: mostra quais arquivos de assets/sons/ foram usados e quais não bateram com nenhum nome."""
        esperados = ["troca", "fusao", "erro"] + [f"ambiente_{k}" for k in AMBIENTES]
        usados = [n for n in esperados if _arquivo(n)]
        print(f"Sons de arquivo em {config.PASTA_SONS}: {', '.join(usados) or 'nenhum'}")
        if config.PASTA_SONS.is_dir():
            ignorados = [f.name for f in config.PASTA_SONS.iterdir()
                         if f.suffix.lower() in EXTENSOES and f.stem.lower() not in esperados]
            if ignorados:
                print("Arquivos ignorados (nome não reconhecido):", ", ".join(ignorados))

    @staticmethod
    def _carregar(nome, padrao):
        """Usa o arquivo em assets/sons/ se existir; senão, o som sintético."""
        caminho = _arquivo(nome)
        if caminho is not None:
            return pygame.mixer.Sound(str(caminho))
        return pygame.mixer.Sound(buffer=np.repeat(padrao, 2).tobytes())  # mono -> estéreo

    def tocar(self, nome: str):
        """Efeitos curtos (troca, fusao, erro)."""
        if config.DEBUG_SOM:
            print("[som]", nome, "" if self.ativo else "(áudio desativado)")
        if self.ativo:
            self._sons[nome].play()

    def ambiente(self, canal: int, estilo: str | None):
        """Som em loop do elemento exibido por uma mão (canal 0 ou 1); None para o som."""
        if not self.ativo or self._tocando[canal] == estilo:
            return
        self._tocando[canal] = estilo
        if config.DEBUG_SOM:
            print(f"[som] ambiente mão {canal}:", estilo or "parou")
        c = pygame.mixer.Channel(canal)
        if estilo is None:
            c.fadeout(200)
        else:
            c.play(self._ambientes[estilo], loops=-1, fade_ms=150)
            self._aplicar_volume(canal)

    # (esquerdo, direito) de cada canal: mão esquerda mais à esquerda, direita mais à direita
    _PAN = {0: (1.0, 0.35), 1: (0.35, 1.0), 2: (1.0, 1.0)}

    def _aplicar_volume(self, canal: int):
        e, d = self._PAN[canal]
        pygame.mixer.Channel(canal).set_volume(e * self._ganho, d * self._ganho)

    def ajustar_mistura(self, n_sons_ambiente: int):
        """Diminui o volume dos ambientes quando vários tocam juntos, para não se encobrirem."""
        if not self.ativo:
            return
        ganho = config.GANHO_AMBIENTE_JUNTOS.get(n_sons_ambiente, 1.0)
        if ganho != self._ganho:
            self._ganho = ganho
            for canal in self._PAN:
                self._aplicar_volume(canal)
