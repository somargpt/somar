# Dashboard — Fluxo de Revisão das Minutas de Edital

Dashboard estático (HTML único, sem dependências externas) com estatísticas do
fluxo de revisão das minutas de edital do repositório: tempos por rodada, tempo
até a versão vigente, comentários por revisão e por revisor, linha do tempo de
cada processo e visão global do conjunto.

## Como visualizar

Abra `dashboard/index.html` em qualquer navegador (duplo clique basta — os
dados já estão embutidos no arquivo). Tema claro/escuro segue a preferência do
sistema. Cada gráfico tem um botão **Tabela** com os dados correspondentes.

## Como atualizar após adicionar/alterar minutas

```bash
python3 dashboard/extract_stats.py     # lê os .docx e gera dashboard/data.json
python3 dashboard/build_dashboard.py   # agrega e injeta o dataset em index.html
```

Requer apenas Python 3 (biblioteca padrão).

## O que é medido

| Conceito | Definição |
|---|---|
| Versão | Um arquivo `.docx` salvo (snapshot da minuta) |
| Rodada observada | Transição entre duas versões consecutivas do mesmo processo; duração = diferença entre as datas de salvamento; atribuída a quem salvou a versão resultante |
| Etapas nominais | Tokens da cadeia de revisão no nome do arquivo mais recente (revisores + marcos institucionais GDM, DM, TR, DT, DCP, GTP, Res. 11) |
| Comentário único | (processo, autor, data, tamanho) — o mesmo comentário persiste em várias versões e é contado uma vez |
| Tempo até a versão vigente | Intervalo entre o salvamento da primeira e da última versão arquivada do processo |

Iniciais dos revisores (cruzadas com os autores dos comentários e o campo
"último modificador" dos arquivos): `oc` Olívia Carvalho · `lk` Leonardo Kim ·
`cz` Caroline Zentner · `rpf` Renan Peron Fineto · `lrs`/`lr` Lucas Ramos da
Silva · `pr` Paulo Rocha.

## Arquivos

- `extract_stats.py` — extrai metadados dos `.docx` (propriedades, comentários do Word, cadeia de revisão do nome do arquivo) para `data.json`
- `build_dashboard.py` — agrega `data.json` (rodadas, tempos, comentários únicos) e injeta o dataset em `index.html`
- `data.json` — metadados brutos por arquivo (gerado)
- `index.html` — o dashboard (autocontido, com dataset embutido)
