export const meta = {
  name: 'inserir-comentarios-notion',
  description: 'Insere as paginas classificadas no banco Padrao de Revisao (Notion) em lotes paralelos',
  phases: [{ title: 'Inserir', detail: 'um agente por lote; cada um chama notion-create-pages' }],
}

const N = (args && args.n) || 781
const STARTAT = (args && args.startAt) || 0
const BATCH = (args && args.batch) || 40
const DS = (args && args.dataSource) || '987aea7a-fbec-4942-930f-4d67ee091838'
const PAGES = '/home/user/somar/dashboard/notion_pages.json'

phase('Inserir')

const ranges = []
for (let s = STARTAT; s < N; s += BATCH) ranges.push([s, Math.min(s + BATCH, N)])

const SCHEMA = {
  type: 'object',
  additionalProperties: false,
  properties: {
    start: { type: 'number' },
    created: { type: 'number' },
    failedIdx: { type: 'array', items: { type: 'number' } },
    error: { type: 'string' },
  },
  required: ['start', 'created'],
}

const results = await parallel(ranges.map(([START, END]) => () =>
  agent(
    `Voce insere paginas no banco de dados Notion "Padrao de Revisao" (uma linha por comentario de revisao).

## Passos
1) Gere o payload EXATO do seu lote (objetos com idx em [${START}, ${END})):
   python3 -c "import json; d=json.load(open('${PAGES}')); b=[{'properties':x['properties']} for x in d if ${START}<=x['idx']<${END}]; open('/tmp/pages_${START}.json','w').write(json.dumps(b,ensure_ascii=False)); print(len(b))"
2) Leia /tmp/pages_${START}.json (um array de objetos {"properties": {...}}).
3) Carregue a ferramenta: ToolSearch query "select:mcp__Notion__notion-create-pages".
4) Chame mcp__Notion__notion-create-pages UMA vez com:
     parent = {"type":"data_source_id","data_source_id":"${DS}"}
     pages  = <o array lido do arquivo, na integra>
   As propriedades ja estao no formato correto (Comentario e o titulo; Tipo/Acionabilidade/
   Documento sao select; date:Data:start e a data; Trecho/Regra/Revisor/Arquivo sao texto).
   NAO altere os valores. NAO adicione a propriedade idx.
5) Trate erros com cuidado para NAO criar duplicatas:
   - Se a chamada retornar erro ANTES de criar (timeout imediato, 429 rate limit, 5xx), tente
     novamente ate 2 vezes (nenhuma pagina foi criada nesse caso).
   - Se a resposta indicar que ALGUMAS paginas foram criadas e outras nao, NAO reenvie o lote
     inteiro: reenvie apenas as paginas que faltaram.
   - Nunca reenvie um lote que ja retornou sucesso.
6) Confirme quantas paginas foram criadas com sucesso (conte os ids retornados).

Retorne {start:${START}, created:<n criadas>, failedIdx:[idx que falharam], error:"<msg se houve>"}.
Seja honesto: se nem todas foram criadas, liste os idx que falharam.`,
    { label: `insert ${START}-${END}`, phase: 'Inserir', schema: SCHEMA, agentType: 'general-purpose', effort: 'low' }
  )
))

const ok = results.filter(Boolean)
const created = ok.reduce((a, r) => a + (r.created || 0), 0)
const failed = ok.flatMap(r => r.failedIdx || [])
log(`lotes: ${ok.length}/${ranges.length} · criadas: ${created} · falhas: ${failed.length}`)
return { batches: ok.length, expected: ranges.length, created, failedIdx: failed }
