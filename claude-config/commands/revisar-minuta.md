---
description: Revisão completa de minuta de edital/TR/contrato do TCESP - converte o .docx uma única vez, extrai a camada Word, detecta o perfil do certame e dispara os nove subagentes de revisão em paralelo
argument-hint: <caminho-absoluto>.docx [--diff <versao-anterior.docx>] [--anterior <relatorio-anterior.md>]
---

Revise a minuta de licitação do TCESP em `$ARGUMENTS` executando o pipeline abaixo, na ordem, sem pular etapas.

## 0. Validação

- O primeiro argumento deve ser o caminho de um arquivo `.docx`. Se for caminho relativo, converta para absoluto com `realpath` ANTES de qualquer outra coisa — o comando pode ter sido invocado de qualquer diretório e nada abaixo pode depender do diretório de trabalho do projeto.
- Se o arquivo não existir, pare e reporte o erro. Não invente caminho.
- Argumentos opcionais: `--diff <versao-anterior.docx>` (modo diff, ver etapa 6) e `--anterior <relatorio-anterior.md>` (cruzamento com rodada anterior, ver etapa 7). NUNCA descubra a versão anterior sozinho pelo nome do arquivo — os sufixos reais de revisão ("rev oc lk cz", "(2)", "GDM Res11") tornam a seleção automática frágil; sem argumento explícito, os modos ficam desligados.

## 0.1 Bootstrap de dependências

- Verifique `pandoc` (`command -v pandoc`). Se ausente, tente instalar (`sudo apt-get install -y pandoc` ou equivalente do ambiente); só pare e reporte se a instalação falhar.
- Verifique `python3` (necessário para a etapa 1.5). Se ausente, registre que a extração da camada Word será pulada e siga.

## 1. Conversão (UMA única vez, com guarda de hash)

Converta o .docx para markdown em diretório determinístico derivado do documento:

```bash
SLUG=$(basename "<caminho-absoluto>.docx" .docx | tr -cs '[:alnum:]' '-' | cut -c1-60)
DIR_REV="${TMPDIR:-/tmp}/revisoes-tcesp/$SLUG"
mkdir -p "$DIR_REV"
sha256sum "<caminho-absoluto>.docx" > "$DIR_REV/docx.sha256.novo"
# Reuso permitido SOMENTE se o hash não mudou:
if [ -f "$DIR_REV/docx.sha256" ] && cmp -s "$DIR_REV/docx.sha256" "$DIR_REV/docx.sha256.novo" && [ -f "$DIR_REV/minuta.md" ]; then
  echo "reuso: conversão anterior válida"
else
  pandoc "<caminho-absoluto>.docx" -t gfm --wrap=none --markdown-headings=atx --track-changes=all -o "$DIR_REV/minuta.md"
  mv "$DIR_REV/docx.sha256.novo" "$DIR_REV/docx.sha256"
fi
TOTAL_LINHAS=$(wc -l < "$DIR_REV/minuta.md")
```

- `--wrap=none` preserva a numeração dos itens em linhas íntegras (crítico para as checagens de remissão).
- `--track-changes=all` faz os comentários do Word entrarem no markdown como spans `comment-start` com autor — insumo do edital-pendencias.
- Anote `$DIR_REV/minuta.md` (caminho absoluto) e `TOTAL_LINHAS`. É PROIBIDO converter novamente na mesma rodada: os nove subagentes leem o MESMO arquivo convertido.

## 1.5 Extração da camada Word (determinística)

O pandoc destrói realces por cor e metadados que os agentes precisam ver (medido: de 919 runs realçados, 12 sobrevivem no markdown). Rode o script versionado do repositório — procure em `<raiz-do-projeto>/.claude/scripts/extrai_camada_docx.py`, depois `<raiz-do-projeto>/claude-config/scripts/extrai_camada_docx.py`:

```bash
python3 <caminho-do-script>/extrai_camada_docx.py "<caminho-absoluto>.docx" "$DIR_REV/camada-oculta.md"
```

Gera comentários embutidos (autor/data/texto/âncora), realces por cor (FT-01 amarelo / FT-02 vermelho), track changes, fontes fora de Arial 12, células mescladas e hiperlinks. Se o script não for encontrado ou falhar, registre a limitação no veredicto final ("camada Word não extraída") e siga — não improvise extração ad hoc.

## 1.75 Perfil do certame

Detecte e registre o perfil ANTES do disparo:

- **Modalidade**: infira do prefixo do nome do arquivo (`pre_eletronico` / `Leilão` / `Chamamento` / `Concurso`) e CONFIRME por grep no `minuta.md` (`PREGÃO ELETRÔNICO`, `LEILÃO`, `CHAMAMENTO PÚBLICO`, `CONCURSO`). Se nome e texto divergirem, pergunte ao usuário. Se o texto não declarar a modalidade inequivocamente, NÃO detecte por palpite: perfil = "não determinado".
- **Regime** (grep no minuta.md, conservador): ARP × contrato (`ATA DE REGISTRO DE PREÇOS`), com/sem garantia contratual, com/sem mão de obra (terceirização/CCT).
- Regra de uso: o perfil injetado nos prompts é PRESUNÇÃO, não ordem — os agentes reportam checagens suprimidas na linha `não aplicadas por perfil` e o texto do documento sempre prevalece sobre o perfil. Perfil "não determinado" → NÃO suprima nada; os agentes aplicam tudo.

## 2. Disparo dos nove subagentes (em paralelo, em background)

Dispare os nove subagentes abaixo em background, todos na mesma rodada (uma única mensagem com as nove invocações). Cada prompt de delegação DEVE conter, literalmente: (a) o caminho absoluto de `$DIR_REV/minuta.md`; (b) `Total de linhas: <TOTAL_LINHAS> — leia 100% com Read paginado`; (c) `Modalidade: <X> | Regime: <Y>` (ou `Perfil: não determinado — aplique todas as checagens`). Os agentes exigem o caminho absoluto e falham sem ele.

1. @edital-repertorio — "Revise o arquivo <caminho> aplicando o repertório da base Padrão de Revisão. <perfil> <linhas>"
2. @edital-legalidade — "Revise o arquivo <caminho> quanto à conformidade com a Lei 14.133/2021 e dispositivos revogados. <perfil> <linhas>"
3. @edital-coerencia — "Audite numeração, remissões internas, anexos e prazos do arquivo <caminho>. <perfil> <linhas>"
4. @edital-pendencias — "Varra o arquivo <caminho> em busca de placeholders, comentários internos e texto de modelo não adaptado. Extrato da camada Word: <caminho de $DIR_REV/camada-oculta.md, se gerado>. <perfil> <linhas>"
5. @edital-adversarial — "Ataque o arquivo <caminho> como um licitante que busca vetores de impugnação e recurso. <perfil> <linhas>"
6. @edital-amarracao — "Verifique a amarração TR ↔ edital ↔ minuta de contrato no arquivo <caminho>. <perfil> <linhas>"
7. @edital-exequibilidade — "Audite a exequibilidade e a alocação processual dos requisitos técnicos de execução do arquivo <caminho>: toda necessidade técnica declarada no TR foi operacionalizada com critério objetivo na fase certa? <perfil> <linhas>"
8. @edital-portugues — "Revise a língua portuguesa do arquivo <caminho>: concordância, ortografia, pontuação, ambiguidade, termos faltantes, grafia oficial. <perfil> <linhas>"
9. @edital-aritmetica — "Recalcule todos os números do arquivo <caminho>: produtos, somas, totais, percentuais e identidade de valores repetidos. <perfil> <linhas>"

Aguarde os nove retornos antes de consolidar. Tratamento de falhas:
- Retorno `ERRO: ...`: reenvie a delegação corrigida uma única vez.
- Retorno sem a tabela no formato OU sem linha final `publicável`/`não publicável`/`amarração não verificável`: reenvie uma única vez citando o formato exigido; persistindo, registre o eixo como **FALHOU**, trate-o como não publicável por precaução e declare a falha no veredicto. NUNCA invente achados para eixo que falhou.
- Retorno com `cobertura de leitura` inferior a 100%: reenvie uma única vez exigindo leitura integral; persistindo, trate como FALHOU.

## 3. Consolidação

Monte UMA tabela única com todos os achados dos nove eixos:

| severidade | localização | trecho literal | achado | fundamento | correção proposta | eixo(s) |

Régua de severidade (a mesma dos agentes): **bloqueante** = impede a publicação; **crítico** = exigiria errata/republicação ou sustentaria impugnação com alta chance; **médio** = desvio sem risco imediato de invalidação; **nit** = aperfeiçoamento.

Regras de consolidação:
- **Deduplicação por âncora**: funda duas linhas em uma SOMENTE quando a localização normalizada coincide (normalize antes: "item 5.2", "5.2", "subitem 5.2" são o mesmo; "item 5.2 do edital × 4.2.1 do TR" casa com achado no 5.2 do edital) E os trechos literais se sobrepõem. Valide por Grep no minuta.md qualquer achado suspeito antes de fundir. Mantenha a MAIOR severidade e liste todos os eixos na coluna eixo(s); a probabilidade do adversarial entra no texto do achado.
- **Arbitragem de enunciado** (para ids emitidos por múltiplos eixos, qual linha fornece o texto canônico): CT-10 → divergência numérica de prazos: amarracao; faceta normativa arts. 106/107: legalidade; coerência interna de prazos: coerencia. CT-31/CT-02 → dentro do mesmo instrumento: coerencia; entre instrumentos: amarracao; conta que não fecha: aritmetica; leitura simples: repertorio. CT-04 → anexo inexistente: coerencia; resquício íntegro de template: pendencias. PD-12 → cláusula fora do modelo: pendencias; dimensão legal (ME/EPP > R$ 4,8 mi): legalidade. PD-14 → amarracao. PT-* → portugues (repertorio é rede de segurança). Vistoria → TR obrigatória × declaração facultativa: amarracao; substituição por declaração (art. 63): legalidade.
- **Ordenação**: por severidade (bloqueante → crítico → médio → nit); dentro da mesma severidade, achados apontados por mais eixos primeiro. Nunca ordene pela ordem do documento.
- Preserve o fundamento de cada achado; ao fundir, concatene os fundamentos distintos.

## 4. Veredito

Após a tabela, apresente:
- Contagem de achados por severidade e por eixo (inclusive quantos foram fundidos na deduplicação) e eixos FALHOU, se houver.
- Cobertura: confirme que os nove eixos declararam leitura de 100% das linhas.
- Agregado das linhas `não aplicadas por perfil` dos agentes (auditabilidade da supressão por modalidade).
- **Checagens estruturalmente não cobertas pela revisão automatizada** (permanecem com o revisor humano): conferência de valores contra o processo/planilha GDM (CT-02 externo), CCT vigente no site do sindicato (CT-19), dotação com a DCF (CT-14), precedentes e impugnações anteriores (CT-26), formatação visual além do extrato da camada Word (FT-03, FT-05, FT-06).
- Linha final única: `publicável` ou `não publicável` + motivo — **não publicável** se qualquer eixo tiver retornado "não publicável", se algum eixo FALHOU, ou se restar qualquer achado bloqueante.
- Os caminhos de `$DIR_REV/minuta.md` e `$DIR_REV/camada-oculta.md`, para reuso em nova rodada (o reuso é condicionado ao hash do .docx — etapa 1).

## 5. Persistência do relatório

Grave a tabela consolidada + veredito em `$DIR_REV/relatorio-<AAAA-MM-DD>.md` e informe o caminho ao usuário — é o insumo do modo `--anterior` da próxima rodada.

## 6. Modo `--diff <versao-anterior.docx>` (opcional)

1. Converta a versão anterior com as MESMAS flags do passo 1 (em subdiretório próprio de `$DIR_REV`).
2. Normalize os dois markdowns antes do diff (remova spans de highlight/comentário gerados pelo pandoc, ex.: `sed 's/<[^>]*>//g'` em cópias temporárias).
3. `git diff --no-index --word-diff` entre as duas versões normalizadas; grave em `$DIR_REV/delta.md`.
4. Acrescente a CADA prompt de delegação: "Há um diff da versão anterior em <caminho de delta.md>: priorize os trechos alterados e verifique, no seu eixo, remissões quebradas por renumeração, alterações não replicadas em trechos correlatos e regressões de correções anteriores."

## 7. Modo `--anterior <relatorio-anterior.md>` (opcional)

Após consolidar, cruze a tabela nova com a do relatório anterior usando o trecho literal como chave: marque cada achado antigo como **resolvido** ou **persistente** e destaque os persistentes no topo do veredito.
