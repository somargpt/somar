export const meta = {
  name: 'classificar-comentarios-edital',
  description: 'Classifica 781 comentarios de revisao de minutas (Tipo, Acionabilidade, Regra) em lotes paralelos',
  phases: [{ title: 'Classificar', detail: 'um agente por lote de ~40 comentarios' }],
}

const N = (args && args.n) || 781
const BATCH = (args && args.batch) || 40
const CATALOG = '/home/user/somar/dashboard/comments_catalog.json'
const OUTDIR = '/home/user/somar/dashboard/cls'

const GUIA = `
Voce classifica comentarios de revisao juridica de minutas de EDITAL de licitacao do TCESP
(Tribunal de Contas do Estado de Sao Paulo), sob a Lei 14.133/2021. Cada comentario foi feito
por um revisor num arquivo .docx, ancorado a um "Trecho" do documento. Para cada comentario
voce define TRES campos.

## Tipo (escolha exatamente um)
- portugues  : correcao gramatical/ortografica/redacional. Concordancia, acento, verbo faltando,
               singular/plural, pontuacao, palavra trocada, clareza da frase.
- formatacao : forma/layout. Espacamento, alinhamento, margem, fonte, negrito, realce/grifo,
               pagina ou folha em branco, cabecalho, quebra, disposicao de tabela.
- padronizacao: alinhar ao padrao. Nomenclatura padrao, numeracao de itens, remissoes internas,
               seguir modelo institucional / minutas recentes, excluir ou incluir item para
               manter o padrao formal das minutas.
- duvida     : o revisor esta em duvida ou questiona sem afirmar. "sera que", "fiquei na duvida",
               "nao seria", pergunta aberta sobre o que fazer.
- conteudo   : merito substantivo juridico/tecnico/economico. Valores, prazos, quantidades,
               clausulas, base legal (art./Lei/inciso/Resolucao), exigencias de habilitacao/
               qualificacao, vedacoes, escopo tecnico, exequibilidade.
Regra de desempate: se ha duvida explicita do revisor, use "duvida". Se e so forma, "formatacao".
Se e so lingua, "portugues". Se invoca padrao/modelo/numeracao, "padronizacao". Caso contrario,
se toca o merito, "conteudo".

## Acionabilidade (escolha exatamente um)
- erro          : algo objetivamente incorreto que precisa ser corrigido (remissao errada, numeracao,
                  nomenclatura fora do padrao, item que deve ser excluido/incluido por regra).
- sugestao      : melhoria opcional proposta pelo revisor ("sugiro", "o que acha", "eu deixaria",
                  "sugeriria", "poderia").
- escalonamento : depende de terceiro ou de decisao fora do alcance do revisor: consultar/confirmar
                  com area tecnica, DCP, DM, GDM, DT, GTP, autoridade; diligencia; definir posicao
                  quando processo/precedente e silente.

## Regra (texto livre curto)
Uma GENERALIZACAO normativa e reutilizavel por tras do comentario — NAO reescreva o comentario.
Convencao do banco: minusculas, SEM ACENTOS (ASCII), sem ponto final, imperativa/normativa.
Exemplos reais do banco:
- comentario "7.8.1" (remissao)            -> "remissoes internas a itens devem apontar para o numero correto"
- comentario "Centralizar alinhamento"     -> "tabelas devem ter alinhamento centralizado"
- comentario "Tecnico-Operacional"         -> "usar a nomenclatura padrao qualificacao tecnico-operacional"
- comentario "Excluir" (clausula fora do modelo) -> "remover clausulas ausentes do modelo institucional vigente"
- comentario duvida sobre subcontratacao   -> "definir posicao sobre subcontratacao quando o processo e os precedentes forem silentes"
- comentario sobre firmware ETP vs TR      -> "verificar consistencia de escopo entre ETP e TR"
- comentario "Sugeriria incluir espacamento" -> "manter espacamento consistente entre clausulas e secoes"
A Regra deve ser especifica o suficiente para ser util, mas geral o suficiente para reaproveitar
em outra minuta. Quando o comentario for trivial/local demais para gerar regra util (ex.: "idem",
"e", um numero solto sem contexto), escreva uma regra minima honesta (ex.: "revisar concordancia
verbal no trecho" ou "conferir valor/numero informado no trecho").
`.trim()

phase('Classificar')

const ranges = []
for (let s = 0; s < N; s += BATCH) ranges.push([s, Math.min(s + BATCH, N)])

const SCHEMA = {
  type: 'object',
  additionalProperties: false,
  properties: {
    start: { type: 'number' },
    end: { type: 'number' },
    count: { type: 'number' },
    file: { type: 'string' },
  },
  required: ['start', 'count', 'file'],
}

const results = await parallel(ranges.map(([START, END]) => () =>
  agent(
    `${GUIA}

## Sua tarefa
Classifique os comentarios cujo campo idx esta em [${START}, ${END}).

1) Rode este comando para obter EXATAMENTE o seu lote (idx, Comentario, Trecho, sei, Revisor):
   python3 -c "import json; d=json.load(open('${CATALOG}')); b=[{k:x.get(k) for k in ('idx','Comentario','Trecho','sei','Revisor')} for x in d if ${START}<=x['idx']<${END}]; open('/tmp/batch_${START}.json','w').write(json.dumps(b,ensure_ascii=False,indent=1)); print(len(b))"
2) Leia /tmp/batch_${START}.json e classifique CADA item lendo Comentario junto com o Trecho ancorado.
3) Escreva o resultado em ${OUTDIR}/cls_${START}.json — um array JSON com um objeto por comentario:
   {"idx": <int>, "tipo": "<um dos 5>", "acionabilidade": "<um dos 3>", "regra": "<texto>"}
   Inclua TODOS os idx do lote, na ordem. tipo e acionabilidade DEVEM usar exatamente os valores
   permitidos. Use aspas duplas e JSON valido (garanta com python json.dumps).
4) Confira que o arquivo tem o mesmo numero de itens que o lote.

Retorne {start:${START}, end:${END}, count:<itens escritos>, file:"${OUTDIR}/cls_${START}.json"}.`,
    { label: `cls ${START}-${END}`, phase: 'Classificar', schema: SCHEMA, agentType: 'general-purpose', effort: 'medium' }
  )
))

const ok = results.filter(Boolean)
log(`lotes concluidos: ${ok.length}/${ranges.length} · total classificado: ${ok.reduce((a, r) => a + (r.count || 0), 0)}`)
return { batches: ok.length, expected: ranges.length, classified: ok.reduce((a, r) => a + (r.count || 0), 0) }
