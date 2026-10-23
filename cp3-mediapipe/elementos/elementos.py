"""Elementos básicos e receitas de fusão."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Elemento:
    nome: str
    cor_bgr: tuple
    estilo: str = ""   # chave em efeitos.ESTILOS


# Nomes sem acento por enquanto: cv2.putText não desenha acentos.
# TODO: trocar por Pillow/fonte TTF e ícones em assets/imagens/.
FOGO = Elemento("Fogo", (40, 80, 255), "fogo")
AGUA = Elemento("Agua", (255, 160, 40), "agua")
TERRA = Elemento("Terra", (50, 110, 140), "terra")
AR = Elemento("Ar", (230, 230, 230), "ar")

BASICOS = [FOGO, AGUA, TERRA, AR]

VAPOR = Elemento("Vapor", (210, 200, 190), "vapor")
LAVA = Elemento("Lava", (0, 60, 200), "lava")
LAMA = Elemento("Lama", (60, 90, 100), "lama")
FUMACA = Elemento("Fumaca", (120, 120, 120), "fumaca")
TEMPESTADE = Elemento("Tempestade", (200, 170, 120), "tempestade")
POEIRA = Elemento("Poeira", (140, 170, 190), "poeira")

RECEITAS = {
    frozenset({FOGO, AGUA}): VAPOR,
    frozenset({FOGO, TERRA}): LAVA,
    frozenset({AGUA, TERRA}): LAMA,
    frozenset({FOGO, AR}): FUMACA,
    frozenset({AGUA, AR}): TEMPESTADE,
    frozenset({TERRA, AR}): POEIRA,
}


def fundir(a: Elemento, b: Elemento) -> Elemento | None:
    """Retorna o novo elemento ou None se a fusão for inválida."""
    return RECEITAS.get(frozenset({a, b}))
