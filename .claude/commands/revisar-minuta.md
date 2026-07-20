---
description: Revisão completa de minuta de edital/TR/contrato do TCESP - converte o .docx uma única vez e dispara os seis subagentes de revisão em paralelo
argument-hint: <caminho-absoluto-do-arquivo.docx>
---

Revise a minuta de licitação do TCESP em `$ARGUMENTS` executando o pipeline abaixo, na ordem, sem pular etapas.

## 0. Validação

- O argumento deve ser o caminho de um arquivo `.docx`. Se for caminho relativo, converta para absoluto com `realpath` ANTES de qualquer outra coisa — o comando pode ter sido invocado de qualquer diretório e nada abaixo pode depender do diretório de trabalho do projeto.
- Se o arquivo não existir, pare e reporte o erro. Não invente caminho.

## 1. Conversão (UMA única vez)

Converta o .docx para markdown exatamente uma vez e grave em diretório temporário:

```bash
TMPDIR_REV=$(mktemp -d)
pandoc "<caminho-absoluto>.docx" -t gfm --wrap=none --markdown-headings=atx -o "$TMPDIR_REV/minuta.md"
```

- `--wrap=none` preserva a numeração dos itens em linhas íntegras (crítico para as checagens de remissão).
- Se o pandoc não estiver instalado, pare e reporte — não tente outro conversor silenciosamente.
- Anote o caminho absoluto resultante (`$TMPDIR_REV/minuta.md`). É PROIBIDO converter novamente: os seis subagentes leem o MESMO arquivo convertido.

## 2. Disparo dos seis subagentes (em paralelo, em background)

Dispare os seis subagentes abaixo em background, todos na mesma rodada (uma única mensagem com as seis invocações), cada um recebendo no prompt de delegação o caminho absoluto do arquivo convertido. Os agentes exigem o caminho absoluto e falham sem ele — inclua-o literalmente em cada prompt.

1. @edital-repertorio — "Revise o arquivo <caminho absoluto de $TMPDIR_REV/minuta.md> aplicando o repertório da base Padrão de Revisão."
2. @edital-legalidade — "Revise o arquivo <caminho absoluto de $TMPDIR_REV/minuta.md> quanto à conformidade com a Lei 14.133/2021 e dispositivos revogados."
3. @edital-coerencia — "Audite numeração, remissões internas, anexos e prazos do arquivo <caminho absoluto de $TMPDIR_REV/minuta.md>."
4. @edital-pendencias — "Varra o arquivo <caminho absoluto de $TMPDIR_REV/minuta.md> em busca de placeholders, comentários internos e texto de modelo não adaptado."
5. @edital-adversarial — "Ataque o arquivo <caminho absoluto de $TMPDIR_REV/minuta.md> como um licitante que busca vetores de impugnação e recurso."
6. @edital-amarracao — "Verifique a amarração TR ↔ edital ↔ minuta de contrato no arquivo <caminho absoluto de $TMPDIR_REV/minuta.md>."

Aguarde os seis retornos antes de consolidar. Se algum agente retornar `ERRO: caminho absoluto...`, reenvie a delegação corrigida uma única vez.

## 3. Consolidação

Monte UMA tabela única com todos os achados dos seis eixos:

| severidade | localização | achado | fundamento | correção proposta | eixo(s) |

Regras de consolidação:
- **Deduplicação entre eixos**: achados que apontam o mesmo problema no mesmo local são fundidos em uma linha — mantenha a MAIOR severidade atribuída e liste na coluna eixo(s) todos os eixos que o apontaram.
- **Ordenação**: por severidade (bloqueante → crítico → médio → nit); dentro da mesma severidade, achados apontados por mais eixos primeiro. Nunca ordene pela ordem do documento.
- Preserve o fundamento de cada achado (dispositivo legal, id de checagem como PD-01, ou "inferência"); ao fundir, concatene os fundamentos distintos.

## 4. Veredito

Após a tabela, apresente:
- Contagem de achados por severidade e por eixo (inclusive quantos foram fundidos na deduplicação).
- Linha final única: `publicável` ou `não publicável` + motivo — **não publicável** se qualquer um dos seis eixos tiver retornado "não publicável" ou se restar qualquer achado bloqueante.
- O caminho do arquivo convertido ($TMPDIR_REV/minuta.md), para reuso em nova rodada sem reconversão.
