# CP3-Projeto-MediaPipe

Checkpoint 03 da matéria Visão Computacional do 4SIZ


# Participantes
Anny Pereira            RM553793

Giovanna Makida         RM552852

Katharine Fernandes     RM552673





# Jogo dos Elementos com MediaPipe

Um jogo controlado só pelas mãos, usando a webcam. Você mostra a palma da mão e um **elemento da natureza** (fogo, água, terra ou ar) aparece sobre ela. Abrindo e fechando a mão você troca de elemento, e juntando as mãos num **"palmas"** os elementos das duas mãos se **fundem** em um elemento novo. Se a combinação não existir, o jogo toca um som de erro.



# Diagrama de Funcionamento
<img width="2346" height="9122" alt="Sem título-2026-10-15-2225" src="https://github.com/user-attachments/assets/494cfbf5-c814-409d-a60e-b22ccb1f8267" />


## 1\. Como executar

### Requisitos

* Python 3.10 ou mais novo (testado com 3.13 e 3.14)
* Webcam
* Conexão com a internet na primeira vez (para baixar as bibliotecas e o modelo de mãos)

### Passo a passo (Windows / PowerShell)

```powershell
# 1. entre na pasta do projeto (a que contém main.py)
cd caminho\\para\\cp3-mediapipe

# 2. instale as dependências
pip install -r requirements.txt

# 3. baixe o modelo de detecção de mãos do MediaPipe (uma vez só)
python scripts/baixar\_modelo.py

# 4. rode o jogo
python main.py
```

Em Linux/macOS os comandos são os mesmos; só muda a ativação do ambiente virtual (`source venv/bin/activate`).

Para fechar, clique na janela do jogo e aperte **`q`**.

> Se o PowerShell bloquear a ativação do ambiente virtual, rode
> `Set-ExecutionPolicy -Scope Process Bypass` e tente de novo. Se preferir, pule o passo 2.

### Dependências (`requirements.txt`)

|Pacote|Para quê|
|-|-|
|`mediapipe`|detecção dos 21 pontos de cada mão|
|`opencv-python`|câmera, janela e desenho|
|`numpy`|cálculos e partículas|
|`pygame-ce`|tocar os sons (se já tiver o `pygame`, rode `pip uninstall pygame` antes)|



## 2\. Como jogar

Fique de frente para a câmera, com as mãos visíveis. A imagem é espelhada: sua mão esquerda aparece do lado esquerdo da tela.

|Gesto|O que acontece|
|-|-|
|**Palma aberta virada para a câmera**|O elemento daquela mão aparece sobre a palma, com o **nome** acima da mão. Quanto mais aberta a mão, maior o efeito.|
|**Abrir e fechar a mão** (fechar o punho depois de abrir)|Troca o elemento **só daquela mão**, na ordem Fogo → Água → Terra → Ar.|
|**"Palmas"** (juntar as duas mãos)|Funde o elemento da mão esquerda com o da direita.|
|**`q`**|Sai do jogo.|

Cada mão começa com um elemento diferente: a esquerda com **Fogo** e a direita com **Água**. A barra preta no topo mostra o elemento escolhido em cada mão e a **última criação**. Mensagens (por exemplo, "Fogo + Agua = Vapor") aparecem embaixo.

**Exemplo:** mostre a mão esquerda com Fogo e a direita com Água → junte as mãos → surge **Vapor** no ponto onde as mãos se encontraram, por 4 segundos, com o som do vapor.



## 3\. Tabela de fusões

A ordem não importa (Fogo + Água = Água + Fogo).

|Elemento 1|Elemento 2|Resultado|
|-|-|-|
|Fogo|Água|Vapor|
|Fogo|Terra|Lava|
|Fogo|Ar|Fumaça|
|Água|Terra|Lama|
|Água|Ar|Tempestade|
|Terra|Ar|Poeira|

Dois elementos iguais (Fogo + Fogo) não formam nada e tocam o som de erro. As receitas ficam no dicionário `RECEITAS` em `elementos/elementos.py`.



## 4\. Como funciona

A cada quadro da câmera o programa faz este caminho:

```
Câmera (OpenCV) → espelha → MediaPipe detecta as mãos → gestos → estado do jogo
                                                                       │
              tela final ← interface (nomes, barra) ← efeitos + sons ←─┘
```



## 5\. Sons

Coloque arquivos `.mp3` em `assets/sons/` com estes nomes:

|Arquivo|Quando toca|
|-|-|
|`troca`|ao trocar o elemento de uma mão|
|`fusao`|quando a fusão dá certo|
|`erro`|fusão impossível|
|`ambiente\_fogo`, `ambiente\_agua`, `ambiente\_terra`, `ambiente\_ar`|em loop enquanto o elemento aparece na mão|
|`ambiente\_vapor`, `ambiente\_lava`, `ambiente\_lama`, `ambiente\_fumaca`, `ambiente\_tempestade`, `ambiente\_poeira`|em loop enquanto o elemento criado aparece|

Os que faltarem usam um som sintético. Ao abrir o jogo, o terminal lista os sons carregados e avisa sobre arquivos com nome não reconhecido.



