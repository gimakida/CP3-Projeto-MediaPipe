"""Efeitos visuais dos elementos.

Cada elemento é um `Estilo`. Um emissor de partículas simula o movimento e há três
formas de desenhar o resultado, para não parecerem "pontinhos":
  - "campo": as partículas viram um campo de densidade suavizado, que é colorido por
             uma paleta (como chama, água, lava, fumaça). Dá formas contínuas.
  - "pedra": pedaços irregulares com sombreamento (terra) sobre uma poeira leve.
  - "traco": riscos de vento seguindo o movimento (ar), sobre uma névoa leve.
  - "areia": milhares de grãos finos lançados em redemoinho, sobre uma névoa leve.
Além das partículas principais há tipos extras: gotas (água), fumaça e faíscas (fogo).
Para criar um novo elemento basta adicionar um Estilo.
"""
from dataclasses import dataclass, field

import cv2
import numpy as np

ESCALA_CAMPO = 0.5   # o campo é calculado em meia resolução (mais rápido e mais suave)


def _lut(paradas):
    """Paleta de 256 entradas. paradas = [(posição 0-1, (b, g, r), alfa), ...]."""
    xs = [p[0] * 255 for p in paradas]
    cores = np.stack([np.interp(np.arange(256), xs, [p[1][c] for p in paradas]) for c in range(3)], 1)
    alfa = np.interp(np.arange(256), xs, [p[2] for p in paradas])
    return cores.astype(np.float32), alfa.astype(np.float32)


@dataclass(frozen=True)
class Estilo:
    paleta: tuple                    # paradas de _lut
    modo: str = "campo"              # "campo" | "pedra" | "traco" | "areia"
    # emissão e movimento
    taxa: float = 200                # partículas por segundo (escala 1)
    vida: float = 0.9                # segundos
    velocidade: float = 200          # px/s para cima (negativo = para baixo)
    espalhamento: float = 40         # variação lateral da velocidade
    base: float = 20                 # largura da origem (px)
    gravidade: float = 0.0           # px/s² (positivo = cai)
    turbulencia: float = 60          # balanço lateral
    afunila: float = 0.0             # puxa para o eixo central (chama afina na ponta)
    arrasto: float = 0.0             # perda de velocidade (fumaça)
    giro: float = 0.0                # rotação ao redor da origem (ar, tempestade)
    # desenho
    blur: float = 14                 # suavização do campo (px, escala 1)
    peso: float = 1.0                # contribuição de cada partícula ao campo
    expoente: float = 1.0            # peso cai com a idade: (1 - t) ** expoente
    ganho: float = 1.0               # multiplica o campo antes da paleta
    ruido: float = 0.0               # textura que sobe e deforma o campo (nuvens, chamas)
    ruido_vel: float = 120           # px/s de subida da textura
    brilho_externo: float = 0.0      # halo de luz em volta (fogo, lava)
    borda: float = 0.0               # realce claro nas bordas (água, lava, lama)
    pedra_tamanho: float = 0.0       # raio das pedras (modo "pedra")
    pedra_cor: tuple = (60, 100, 140)
    traco_cor: tuple = (255, 255, 255)
    graos: int = 0                   # 1 a cada N partículas vira um grão/faísca
    grao_cor: tuple = (255, 255, 255)
    raios: bool = False              # relâmpagos (tempestade)
    gotas: float = 0.0               # gotas caindo (água): fração da taxa principal
    faiscas: float = 0.0             # faíscas (fogo): fração da taxa principal
    fumaca: float = 0.0              # fumaça escura (fogo): fração da taxa principal
    brasas: bool = False             # leito de brasas sob a chama (parece queimar algo)


ESTILOS = {
    # Chama: quente (amarelo/branco) na base, vermelha e translúcida na ponta
    "fogo": Estilo(
        paleta=((0.0, (0, 0, 0), 0.0), (0.12, (0, 0, 90), 0.0), (0.25, (10, 30, 200), 0.55),
                (0.45, (0, 100, 255), 0.85), (0.72, (40, 200, 255), 0.95),
                (1.0, (190, 250, 255), 1.0)),
        taxa=300, vida=1.05, velocidade=320, espalhamento=45, base=34, turbulencia=130,
        afunila=2.2, blur=11, peso=0.5, expoente=1.0, ganho=0.85, ruido=0.55, ruido_vel=380,
        brilho_externo=0.35, graos=12, grao_cor=(120, 230, 255)),
    # Variante "queimando algo" (brasas, faíscas e fumaça). Para usar, troque o estilo de FOGO
    # em elementos.py para "fogo_brasas".
    "fogo_brasas": Estilo(
        paleta=((0.0, (0, 0, 0), 0.0), (0.12, (0, 0, 90), 0.0), (0.25, (10, 30, 200), 0.55),
                (0.45, (0, 100, 255), 0.85), (0.72, (40, 200, 255), 0.95),
                (1.0, (190, 250, 255), 1.0)),
        taxa=300, vida=1.05, velocidade=320, espalhamento=45, base=34, turbulencia=130,
        afunila=2.2, blur=11, peso=0.5, expoente=1.0, ganho=0.85, ruido=0.55, ruido_vel=380,
        brilho_externo=0.35, faiscas=0.10, fumaca=0.08, brasas=True),
    # Água: massa azul translúcida em jato que sobe e cai, com brilho nas bordas e gotas
    "agua": Estilo(
        paleta=((0.0, (0, 0, 0), 0.0), (0.22, (160, 80, 20), 0.0), (0.30, (210, 130, 40), 0.55),
                (0.55, (240, 180, 80), 0.72), (1.0, (255, 235, 190), 0.85)),
        taxa=260, vida=1.3, velocidade=520, espalhamento=120, base=26, gravidade=900,
        turbulencia=30, blur=7, peso=0.9, expoente=0.3, ganho=1.25, borda=1.2, gotas=0.30),
    # Terra: pedras angulosas que saltam e caem, mais poeira
    "terra": Estilo(
        paleta=((0.0, (0, 0, 0), 0.0), (0.25, (70, 100, 130), 0.0), (1.0, (95, 130, 155), 0.55)),
        modo="pedra", taxa=75, vida=1.3, velocidade=340, espalhamento=80, base=30,
        gravidade=800, turbulencia=10, blur=18, peso=0.6, expoente=0.8, ganho=1.0,
        ruido=0.5, ruido_vel=60, pedra_tamanho=17, pedra_cor=(55, 95, 135)),
    # Ar: riscos de vento girando em espiral
    "ar": Estilo(
        paleta=((0.0, (0, 0, 0), 0.0), (0.3, (255, 255, 255), 0.0), (1.0, (255, 250, 240), 0.25)),
        modo="traco", taxa=120, vida=1.3, velocidade=40, espalhamento=30, base=30,
        turbulencia=20, giro=4.2, blur=16, peso=0.3, expoente=0.5, ganho=0.9, ruido=0.6,
        ruido_vel=90, traco_cor=(255, 252, 245)),
    # --- elementos criados pela fusão ---
    "vapor": Estilo(
        paleta=((0.0, (0, 0, 0), 0.0), (0.12, (200, 200, 200), 0.0), (0.35, (225, 225, 225), 0.40),
                (1.0, (255, 255, 255), 0.75)),
        taxa=110, vida=1.7, velocidade=120, espalhamento=30, base=30, turbulencia=45,
        arrasto=0.3, blur=22, peso=0.8, expoente=0.8, ganho=1.0, ruido=0.9, ruido_vel=100),
    "lava": Estilo(
        paleta=((0.0, (0, 0, 0), 0.0), (0.18, (20, 20, 60), 0.0), (0.30, (20, 25, 80), 0.95),
                (0.50, (0, 40, 220), 1.0), (0.75, (0, 150, 255), 1.0), (1.0, (130, 245, 255), 1.0)),
        taxa=150, vida=1.4, velocidade=300, espalhamento=75, base=26, gravidade=560,
        turbulencia=25, blur=10, peso=0.9, expoente=0.4, ganho=1.1, brilho_externo=0.30,
        borda=0.6, graos=10, grao_cor=(80, 220, 255)),
    "lama": Estilo(
        paleta=((0.0, (0, 0, 0), 0.0), (0.22, (30, 45, 60), 0.0), (0.32, (35, 55, 75), 1.0),
                (0.7, (55, 85, 115), 1.0), (1.0, (85, 120, 150), 1.0)),
        taxa=150, vida=1.3, velocidade=360, espalhamento=90, base=28, gravidade=700,
        turbulencia=20, blur=9, peso=0.9, expoente=0.3, ganho=1.3, borda=0.8),
    "fumaca": Estilo(
        paleta=((0.0, (0, 0, 0), 0.0), (0.10, (40, 40, 40), 0.0), (0.35, (70, 70, 70), 0.55),
                (1.0, (130, 130, 130), 0.85)),
        taxa=120, vida=1.9, velocidade=150, espalhamento=35, base=28, turbulencia=70,
        arrasto=0.4, blur=20, peso=0.8, expoente=0.7, ganho=1.0, ruido=1.0, ruido_vel=140),
    "tempestade": Estilo(
        paleta=((0.0, (0, 0, 0), 0.0), (0.15, (55, 45, 40), 0.0), (0.35, (75, 60, 50), 0.75),
                (1.0, (125, 105, 90), 0.95)),
        taxa=190, vida=1.1, velocidade=30, espalhamento=85, base=38, turbulencia=60,
        giro=4.5, blur=24, peso=0.9, expoente=0.6, ganho=1.0, ruido=1.0, ruido_vel=60,
        raios=True),
    "poeira": Estilo(
        paleta=((0.0, (0, 0, 0), 0.0), (0.15, (110, 150, 180), 0.0), (0.5, (125, 170, 200), 0.22),
                (1.0, (150, 195, 220), 0.40)),
        modo="areia", taxa=300, vida=1.5, velocidade=260, espalhamento=130, base=36,
        gravidade=300, turbulencia=70, giro=3.2, arrasto=0.35, blur=18, peso=0.25,
        expoente=0.6, ganho=0.8, ruido=0.7, ruido_vel=60),
}
ESTILOS["fumaca_escura"] = Estilo(
    paleta=((0.0, (0, 0, 0), 0.0), (0.15, (22, 22, 24), 0.0), (0.40, (38, 38, 42), 0.40),
            (1.0, (70, 70, 76), 0.62)),
    taxa=0, vida=2.0, blur=20, peso=0.8, expoente=0.7, ganho=1.0, ruido=1.0, ruido_vel=150)
_LUTS = {nome: _lut(e.paleta) for nome, e in ESTILOS.items()}

def _textura(tam=256, sigma=9, semente=7):
    """Ruído suave e repetível (0-1) usado para dar forma de chama/nuvem ao campo."""
    r = np.random.default_rng(semente).random((tam, tam)).astype(np.float32)
    pad = cv2.copyMakeBorder(r, tam, tam, tam, tam, cv2.BORDER_WRAP)
    pad = cv2.GaussianBlur(pad, (0, 0), sigma)[tam:-tam, tam:-tam]
    return (pad - pad.min()) / (pad.max() - pad.min())


_TEXTURA = _textura()

# colunas da matriz de partículas
# tipo: 0 principal, 1 gota, 2 fumaça, 3 faísca
X, Y, VX, VY, IDADE, VIDA, FASE, ROT, TIPO = range(9)
NCOL = 9


class Emissor:
    """Simula as partículas de um elemento ancoradas num ponto (a palma) e as desenha."""

    MAX = 900

    def __init__(self):
        self.estilo = None
        self._nome = None
        self.p = np.zeros((0, NCOL), np.float32)
        self._resto = {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0}
        self._origem = None
        self._raio = None
        self._tempo = 0.0
        self._rng = np.random.default_rng()

    def trocar_estilo(self, nome: str):
        if nome != self._nome:
            self._nome, self.estilo = nome, ESTILOS[nome]
            self.p = self.p[:0]
            self._raio = None

    # ---------------------------------------------------------------- simulação
    def atualizar(self, dt: float, origem, escala: float, ativo: bool):
        e = self.estilo
        if e is None:
            return
        self._tempo += dt
        if origem is not None:
            self._origem = origem
        if ativo and origem is not None:
            taxas = {0: e.taxa, 1: e.taxa * e.gotas, 2: e.taxa * e.fumaca, 3: e.taxa * e.faiscas}
            for tipo, taxa in taxas.items():
                self._resto[tipo] += taxa * escala * dt
                n = min(int(self._resto[tipo]), self.MAX - len(self.p))
                self._resto[tipo] -= int(self._resto[tipo])
                if n > 0:
                    self.p = np.vstack([self.p, self._novas(n, origem, escala, tipo)])
        if not len(self.p):
            return
        p = self.p
        tipo = p[:, TIPO].astype(int)
        p[:, IDADE] += dt
        p[:, VY] += e.gravidade * np.array([1.0, 1.35, 0.0, 0.0])[tipo] * dt
        p[:, VX] += np.sin(p[:, IDADE] * 9 + p[:, FASE]) * e.turbulencia * dt * 6
        if self._origem is not None:
            ox, oy = self._origem
            if e.afunila:
                p[:, VX] += (ox - p[:, X]) * e.afunila * np.array([1.0, 0.0, 0.3, 0.2])[tipo] * dt
            if e.giro:
                dx, dy = p[:, X] - ox, p[:, Y] - oy
                g = (tipo == 0) * e.giro * dt * 3
                p[:, VX] += -dy * g
                p[:, VY] += dx * g
        arrasto = np.array([e.arrasto, 0.0, max(e.arrasto, 0.5), 0.0])[tipo]
        p[:, VX] *= np.maximum(0.0, 1 - arrasto * dt)
        p[:, VY] *= np.maximum(0.0, 1 - arrasto * dt)
        p[:, X] += p[:, VX] * dt
        p[:, Y] += p[:, VY] * dt
        self.p = p[p[:, IDADE] < p[:, VIDA]]

    def _novas(self, n, origem, escala, tipo=0):
        e, r = self.estilo, self._rng
        novas = np.zeros((n, NCOL), np.float32)
        novas[:, TIPO] = tipo
        novas[:, FASE] = r.uniform(0, 6.28, n)
        novas[:, ROT] = r.uniform(-6, 6, n)
        novas[:, X] = origem[0] + r.normal(0, e.base * escala / 2, n)
        novas[:, Y] = origem[1] + r.normal(0, e.base * escala / 6, n)
        if tipo == 0:
            novas[:, VX] = r.normal(0, e.espalhamento, n)
            novas[:, VY] = -e.velocidade * escala * r.uniform(0.6, 1.15, n)
            novas[:, VIDA] = e.vida * r.uniform(0.7, 1.2, n)
        elif tipo == 1:    # gota: metade nasce no jato, metade cai de cima (chuva)
            novas[:, VX] = r.normal(0, e.espalhamento * 1.1, n)
            novas[:, VY] = -e.velocidade * escala * r.uniform(0.3, 0.8, n)
            chuva = r.random(n) < 0.5
            novas[chuva, X] += r.normal(0, 40 * escala, chuva.sum())
            novas[chuva, Y] -= r.uniform(60, 220, chuva.sum()) * escala
            novas[chuva, VY] = r.uniform(0, 120, chuva.sum()) * escala
            novas[:, VIDA] = e.vida * r.uniform(0.9, 1.5, n)
        elif tipo == 2:    # fumaça: sobe devagar acima da chama
            novas[:, X] += r.normal(0, 14 * escala, n)
            novas[:, Y] -= 110 * escala
            novas[:, VX] = r.normal(0, 25, n)
            novas[:, VY] = -90 * escala * r.uniform(0.6, 1.2, n)
            novas[:, VIDA] = 2.0 * r.uniform(0.8, 1.2, n)
        else:              # faísca: sobe rápido e some
            novas[:, VX] = r.normal(0, 95, n)
            novas[:, VY] = -e.velocidade * escala * r.uniform(0.7, 1.4, n)
            novas[:, VIDA] = r.uniform(0.5, 1.0, n)
        return novas

    # ------------------------------------------------------------------ desenho
    def desenhar(self, frame, escala: float):
        e = self.estilo
        if e is None or not len(self.p):
            return
        tipo = self.p[:, TIPO].astype(int)
        if (tipo == 2).any():
            self._campo(frame, escala, self.p[tipo == 2], "fumaca_escura")
        if e.brasas:
            self._brasas(frame, escala, int((tipo == 0).sum()))
        principais = self.p[tipo == 0]
        if len(principais):
            self._campo(frame, escala, principais, self._nome)
            if e.modo == "pedra":
                self._pedras(frame, escala, principais)
            elif e.modo == "traco":
                self._tracos(frame, principais)
            elif e.modo == "areia":
                self._areia(frame, principais)
        if (tipo == 1).any():
            self._gotas(frame, escala, self.p[tipo == 1])
        if (tipo == 3).any():
            self._faiscas(frame, self.p[tipo == 3])
        if e.graos and len(principais):
            self._graos(frame, escala, principais)
        if e.raios and len(principais):
            self._relampago(frame, escala, principais)

    def _campo(self, frame, escala, p, nome):
        e = ESTILOS[nome]
        h, w = frame.shape[:2]
        s = ESCALA_CAMPO
        t = p[:, IDADE] / p[:, VIDA]
        peso = e.peso * (1 - t) ** e.expoente
        sigma = max(1.0, e.blur * escala * s)
        m = int(3 * sigma) + 2
        # caixa em volta da maior parte das partículas (ignora as muito afastadas)
        lo, hi = np.percentile(p[:, X:Y + 1], (2, 98), axis=0)
        x0, y0 = int(lo[0] * s) - m, int(lo[1] * s) - m
        x1, y1 = int(hi[0] * s) + m, int(hi[1] * s) + m
        x0, y0 = max(x0, int(-m)), max(y0, int(-m))
        x1, y1 = min(x1, int(w * s) + m), min(y1, int(h * s) + m)
        if x1 <= x0 or y1 <= y0:
            return
        ix, iy = (p[:, X] * s).astype(int) - x0, (p[:, Y] * s).astype(int) - y0
        ok = (ix >= 0) & (iy >= 0) & (ix < x1 - x0) & (iy < y1 - y0)
        campo = np.zeros((y1 - y0, x1 - x0), np.float32)
        np.add.at(campo, (iy[ok], ix[ok]), peso[ok])
        campo = cv2.GaussianBlur(campo, (0, 0), sigma) * (e.ganho * 2 * np.pi * sigma ** 2 * 0.12)

        if e.ruido:   # textura em coordenadas do mundo, subindo com o tempo
            lin = ((np.arange(campo.shape[0]) + y0) / s + self._tempo * e.ruido_vel).astype(int) % 256
            col = ((np.arange(campo.shape[1]) + x0) / s).astype(int) % 256
            campo = campo * (1 + e.ruido * (_TEXTURA[lin[:, None], col[None, :]] - 0.5) * 2)

        cores, alfa_lut = _LUTS[nome]
        idx = np.clip(campo * 255, 0, 255).astype(np.uint8)
        cor, alfa = cores[idx], alfa_lut[idx]
        if e.borda:   # realce claro onde o campo muda rápido: aspecto de líquido
            brilho = np.clip((campo - cv2.GaussianBlur(campo, (0, 0), 1.6)) * 9 * e.borda, 0, 1)
            cor = cor + (brilho * alfa)[..., None] * 160
        halo = None
        if e.brilho_externo:
            halo = cv2.GaussianBlur(alfa, (0, 0), 7 * max(escala, 0.6)) * e.brilho_externo * 0.8

        # sobe para a resolução da tela e mistura com o frame
        fx0, fy0 = int(x0 / s), int(y0 / s)
        tam = (int((x1 - x0) / s), int((y1 - y0) / s))
        cor = cv2.resize(cor, tam, interpolation=cv2.INTER_LINEAR)
        alfa = cv2.resize(alfa, tam, interpolation=cv2.INTER_LINEAR)
        ax0, ay0 = max(0, fx0), max(0, fy0)
        ax1, ay1 = min(w, fx0 + tam[0]), min(h, fy0 + tam[1])
        if ax1 <= ax0 or ay1 <= ay0:
            return
        recorte = (slice(ay0 - fy0, ay1 - fy0), slice(ax0 - fx0, ax1 - fx0))
        cor, alfa = cor[recorte], alfa[recorte][..., None]
        roi = frame[ay0:ay1, ax0:ax1].astype(np.float32)
        saida = roi + (cor - roi) * alfa
        if halo is not None:
            halo = cv2.resize(halo, tam, interpolation=cv2.INTER_LINEAR)[recorte][..., None]
            saida += cores[-1] * halo
        frame[ay0:ay1, ax0:ax1] = np.clip(saida, 0, 255).astype(np.uint8)

    def _pedras(self, frame, escala, p):
        """Pedras poligonais com tom variado, desenhadas em poucos grupos (rápido)."""
        e = self.estilo
        base = np.array(e.pedra_cor, np.float32)
        fase = p[:, FASE]
        ang = fase + p[:, ROT] * p[:, IDADE]
        r = e.pedra_tamanho * escala * (0.6 + 0.6 * np.abs(np.sin(fase * 3)))
        k = np.arange(6)
        raios = r[:, None] * (0.75 + 0.35 * np.sin(fase[:, None] * 7 + k * 2.1))
        angs = ang[:, None] + k * (np.pi / 3)
        pts = np.stack([p[:, X, None] + raios * np.cos(angs),
                        p[:, Y, None] + raios * np.sin(angs)], 2).astype(np.int32)
        grupo = ((np.sin(fase * 5) * 0.5 + 0.5) * 3.99).astype(int)     # 4 tons
        for g in range(4):
            sel = pts[grupo == g]
            if not len(sel):
                continue
            tom = 0.7 + 0.4 * g / 3
            cv2.fillPoly(frame, list(sel), tuple(int(v) for v in np.clip(base * tom, 0, 255)), cv2.LINE_AA)
            cv2.polylines(frame, list(sel), True, tuple(int(v) for v in base * 0.3), 1, cv2.LINE_AA)
            luz = (sel[:, :3] * 0.7 + sel.mean(axis=1, keepdims=True) * 0.3).astype(np.int32)
            cv2.polylines(frame, list(luz), False, tuple(int(v) for v in np.clip(base * (tom + 0.5), 0, 255)),
                          1, cv2.LINE_AA)

    def _regiao(self, frame, p, margem=40):
        """Caixa (y0, y1, x0, x1) em volta das partículas, para não processar a tela toda."""
        h, w = frame.shape[:2]
        x0 = max(0, int(p[:, X].min()) - margem); x1 = min(w, int(p[:, X].max()) + margem)
        y0 = max(0, int(p[:, Y].min()) - margem); y1 = min(h, int(p[:, Y].max()) + margem)
        return y0, y1, x0, x1

    def _tracos(self, frame, p):
        e = self.estilo
        y0, y1, x0, x1 = self._regiao(frame, p)
        if y1 <= y0 or x1 <= x0:
            return
        tela = np.zeros((y1 - y0, x1 - x0, 3), np.uint8)
        t = p[:, IDADE] / p[:, VIDA]
        a = (1 - t) * np.minimum(1.0, t * 6)                          # surge e some suavemente
        comp = 0.09 + 0.05 * np.sin(p[:, FASE] * 4)
        ini = np.stack([p[:, X] - p[:, VX] * comp - x0, p[:, Y] - p[:, VY] * comp - y0], 1).astype(np.int32)
        fim = np.stack([p[:, X] - x0, p[:, Y] - y0], 1).astype(np.int32)
        brilho = np.minimum((a * 4).astype(int), 3)                    # 4 níveis de brilho
        for b in range(4):
            sel = brilho == b
            if sel.any():
                cor = tuple(int(c * (b + 1) / 4) for c in e.traco_cor)
                segs = np.stack([ini[sel], fim[sel]], 1)
                cv2.polylines(tela, list(segs), False, cor, 1, cv2.LINE_AA)
        tela = cv2.GaussianBlur(tela, (0, 0), 0.8)
        roi = frame[y0:y1, x0:x1]
        cv2.add(roi, tela, dst=roi)

    def _graos(self, frame, escala, p):
        e = self.estilo
        for x, y, t in zip(p[::e.graos, X], p[::e.graos, Y], p[::e.graos, IDADE] / p[::e.graos, VIDA]):
            cv2.circle(frame, (int(x), int(y)), max(1, int(2.2 * escala * (1 - t))), e.grao_cor, -1, cv2.LINE_AA)

    def _gotas(self, frame, escala, p):
        """Gotas em formato de lágrima alongada no sentido da queda, com brilho."""
        for x, y, vx, vy, t in zip(p[:, X], p[:, Y], p[:, VX], p[:, VY], p[:, IDADE] / p[:, VIDA]):
            if t > 0.92:
                continue
            comp = (4.5 + min(5.0, abs(vy) * 0.012)) * escala * (1 - 0.3 * t)
            larg = 3.0 * escala * (1 - 0.3 * t)
            ang = np.degrees(np.arctan2(vy, vx))
            centro = (int(x), int(y))
            cv2.ellipse(frame, centro, (max(2, int(comp)), max(1, int(larg))), ang, 0, 360,
                        (235, 175, 80), -1, cv2.LINE_AA)
            cv2.ellipse(frame, centro, (max(2, int(comp)), max(1, int(larg))), ang, 0, 360,
                        (190, 110, 30), 1, cv2.LINE_AA)
            cv2.circle(frame, (int(x - comp * 0.25), int(y - larg * 0.4)), 1, (255, 255, 255), -1, cv2.LINE_AA)

    def _faiscas(self, frame, p):
        """Faíscas: riscos curtos amarelos que esfriam para laranja."""
        for x, y, vx, vy, t in zip(p[:, X], p[:, Y], p[:, VX], p[:, VY], p[:, IDADE] / p[:, VIDA]):
            cor = (int(60 + 40 * t), int(220 - 120 * t), 255)
            cv2.line(frame, (int(x - vx * 0.05), int(y - vy * 0.05)), (int(x), int(y)), cor,
                     1 if t > 0.5 else 2, cv2.LINE_AA)

    def _brasas(self, frame, escala, n_chama: int):
        """Leito de brasas sob a chama: pedaços escuros de carvão com rachaduras incandescentes."""
        if self._origem is None:
            return
        forca = min(1.0, n_chama / 70)
        if forca < 0.1:
            return
        ox, oy = self._origem
        h, w = frame.shape[:2]
        brilho = 0.75 + 0.25 * np.sin(self._tempo * 11)
        # luz alaranjada no chão
        x0, x1 = max(0, int(ox - 80 * escala)), min(w, int(ox + 80 * escala))
        y0, y1 = max(0, int(oy - 20 * escala)), min(h, int(oy + 45 * escala))
        if x1 > x0 and y1 > y0:
            luz = np.zeros((y1 - y0, x1 - x0, 3), np.uint8)
            cv2.ellipse(luz, (int(ox - x0), int(oy + 12 * escala - y0)), (int(60 * escala), int(16 * escala)),
                        0, 0, 360, (0, int(90 * brilho * forca), int(230 * forca)), -1)
            luz = cv2.GaussianBlur(luz, (0, 0), 9 * max(escala, 0.6))
            roi = frame[y0:y1, x0:x1]
            cv2.add(roi, luz, dst=roi)
        k = np.arange(7)
        for i in k:
            cx = ox + (i - 3) * 16 * escala + 3 * np.sin(i * 5.1)
            cy = oy + 12 * escala + 5 * escala * (i % 2) + 2 * np.cos(i * 2.3)
            r = (11 + 4 * np.sin(i * 3.7)) * escala
            angs = i + np.arange(6) * (np.pi / 3)
            rr = r * (0.8 + 0.3 * np.sin(i * 2 + np.arange(6) * 2.2))
            pts = np.stack([cx + rr * np.cos(angs), cy + 0.6 * rr * np.sin(angs)], 1).astype(np.int32)
            cv2.fillConvexPoly(frame, pts, (22, 24, 34), cv2.LINE_AA)
            quente = (0, int((70 + 90 * brilho) * forca), int(230 * forca))
            cv2.polylines(frame, [pts], True, quente, 1, cv2.LINE_AA)
            cv2.line(frame, tuple(pts[0]), tuple(pts[3]), quente, 1, cv2.LINE_AA)   # rachadura brilhante

    def _areia(self, frame, p):
        """Grãos de areia: pixels soltos com 3 tons, alguns maiores, que somem com a idade."""
        h, w = frame.shape[:2]
        ix, iy = p[:, X].astype(int), p[:, Y].astype(int)
        ok = (ix >= 0) & (iy >= 0) & (ix < w - 1) & (iy < h - 1)
        if not ok.any():
            return
        q, ix, iy = p[ok], ix[ok], iy[ok]
        t = q[:, IDADE] / q[:, VIDA]
        a = (np.clip(1 - t, 0, 1) ** 0.3 * np.clip(t * 10, 0, 1))[:, None]
        tons = np.array([(120, 175, 205), (95, 150, 185), (150, 200, 225)], np.float32)  # BGR de areia
        cor = tons[((np.sin(q[:, FASE] * 13) * 0.5 + 0.5) * 2.99).astype(int)]
        grande = np.sin(q[:, FASE] * 5) > 0.2
        for dx, dy, so_grande in ((0, 0, False), (1, 0, True), (0, 1, True), (1, 1, True)):
            sel = grande if so_grande else np.ones(len(q), bool)
            if not sel.any():
                continue
            yy, xx = iy[sel] + dy, ix[sel] + dx
            frame[yy, xx] = (frame[yy, xx] * (1 - a[sel]) + cor[sel] * a[sel]).astype(np.uint8)

    def _relampago(self, frame, escala, p):
        """Relâmpago ramificado que cai da nuvem, com clarão que ilumina a nuvem."""
        if self._raio is None and self._rng.random() < 0.12:
            r = self._rng
            x, y = float(p[:, X].mean()) + r.uniform(-30, 30) * escala, float(np.percentile(p[:, Y], 20))
            pts = [(x, y)]
            for _ in range(11):
                x += r.uniform(-30, 30) * escala
                y += r.uniform(22, 38) * escala
                pts.append((x, y))
            ramos = []
            for k in r.choice(range(2, 9), 2, replace=False):
                bx, by = pts[k]
                ramo = [(bx, by)]
                for _ in range(4):
                    bx += r.choice([-1, 1]) * r.uniform(15, 30) * escala
                    by += r.uniform(15, 30) * escala
                    ramo.append((bx, by))
                ramos.append(np.array(ramo, np.int32))
            self._raio = [np.array(pts, np.int32), ramos, 5]
        if self._raio is None:
            return
        tronco, ramos, restam = self._raio
        h, w = frame.shape[:2]
        todos = np.vstack([tronco] + ramos)
        x0, x1 = max(0, int(todos[:, 0].min()) - 80), min(w, int(todos[:, 0].max()) + 80)
        y0, y1 = max(0, int(p[:, Y].min()) - 60), min(h, int(todos[:, 1].max()) + 40)
        pisca = restam % 2 == 1 or restam >= 4
        if pisca:
            self._clarao(frame, escala, p)
        if pisca and x1 > x0 and y1 > y0:
            local = lambda a: a - np.array([x0, y0], np.int32)
            tela = np.zeros((y1 - y0, x1 - x0, 3), np.uint8)
            cv2.polylines(tela, [local(tronco)], False, (255, 215, 170), 5, cv2.LINE_AA)
            for ramo in ramos:
                cv2.polylines(tela, [local(ramo)], False, (255, 215, 170), 3, cv2.LINE_AA)
            brilho = cv2.GaussianBlur(tela, (0, 0), 9)
            cv2.polylines(tela, [local(tronco)], False, (255, 255, 255), 2, cv2.LINE_AA)
            for ramo in ramos:
                cv2.polylines(tela, [local(ramo)], False, (255, 255, 255), 1, cv2.LINE_AA)
            roi = frame[y0:y1, x0:x1]
            cv2.add(roi, cv2.add(tela, brilho), dst=roi)
        self._raio[2] -= 1
        if self._raio[2] <= 0:
            self._raio = None

    def _clarao(self, frame, escala, p):
        """Clarão suave que ilumina a nuvem (elipse borrada, sem bordas retas)."""
        h, w = frame.shape[:2]
        cx, cy = int(p[:, X].mean()), int(np.percentile(p[:, Y], 50))
        m = int(260 * escala)
        x0, x1, y0, y1 = max(0, cx - m), min(w, cx + m), max(0, cy - m), min(h, cy + m)
        if x1 <= x0 or y1 <= y0:
            return
        k = 0.25   # máscara em baixa resolução (é só um brilho difuso) e depois ampliada
        mascara = np.zeros((max(1, int((y1 - y0) * k)), max(1, int((x1 - x0) * k))), np.float32)
        cv2.ellipse(mascara, (int((cx - x0) * k), int((cy - y0) * k)),
                    (int(90 * escala * k), int(70 * escala * k)), 0, 0, 360, 1.0, -1)
        mascara = cv2.GaussianBlur(mascara, (0, 0), 35 * escala * k)
        mascara = cv2.resize(mascara, (x1 - x0, y1 - y0), interpolation=cv2.INTER_LINEAR)[..., None]
        roi = frame[y0:y1, x0:x1]
        roi[:] = np.clip(roi + mascara * np.array((70, 58, 46), np.float32), 0, 255).astype(np.uint8)
