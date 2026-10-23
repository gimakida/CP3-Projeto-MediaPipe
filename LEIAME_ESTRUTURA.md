# Estrutura inicial

```
main.py                  loop de câmera + janela
requirements.txt
scripts/baixar_modelo.py baixa hand_landmarker.task
elementos/
  config.py              parâmetros ajustáveis
  hand_tracker.py        MediaPipe HandLandmarker (+ desenho dos pontos)
  gestos.py              palma p/ cima, mão aberta/fechada, palmas
  elementos.py           elementos e receitas de fusão
  jogo.py                estado por mão (elemento de cada mão), fusão
  audio.py               sons (arquivos em assets/sons/ ou sintéticos como reserva)
  efeitos.py             partículas por elemento (ESTILOS) – fogo, água, terra, ar e fundidos
  cena.py                liga jogo -> efeito na palma, efeito da fusão e som ambiente
  interface.py           barra do topo e mensagens
assets/modelos/          modelo .task (não versionado)
```

Como rodar: `pip install -r requirements.txt && python scripts/baixar_modelo.py && python main.py`

Fluxo: cada mão tem o seu elemento. Palma aberta voltada p/ câmera mostra o efeito e o nome perto da mão → abrir e fechar a mão troca o elemento daquela mão (a outra não muda) → palmas funde o elemento da mão esquerda com o da direita; receita inexistente (ou elementos iguais) toca o som de erro.

Efeitos: o mesmo emissor de partículas serve a todos os elementos; cada um tem um `Estilo` em `efeitos.py` (cores, direção, gravidade, giro). O tamanho acompanha a abertura da mão, o fundo fica em cinza e há um som ambiente por elemento (sintético por enquanto).
