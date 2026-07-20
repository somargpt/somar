# Configuração Claude Code — Revisão de Minutas TCESP

Subagentes de revisão de minutas de editais/TR/contratos do TCESP, destilados da base
"Padrão de Revisão" do CLAUDE BRAIN (Notion): 889 registros lidos na íntegra
(2025-10-22 → 2026-07-16), consolidados em 78 checagens deduplicadas (CT/PD/DV/PT/FT)
+ eixo EXQ extra-base com origem documentada.

## Fonte única e sincronização

**`claude-config/` é a fonte única.** A cópia carregada pelo Claude Code no projeto é
`.claude/`, gerada por sincronização — NUNCA edite `.claude/` diretamente.

```bash
claude-config/scripts/sync-claude.sh          # sincroniza claude-config/ -> .claude/
claude-config/scripts/sync-claude.sh --check  # verifica drift (exit 1 se divergir; use em CI/hook)
```

Regra de PR: toda alteração de agente/comando/script toca os DOIS diretórios no mesmo
commit (rode o sync antes de commitar). Cada agente carrega `versao:` no frontmatter.

## Conteúdo

| arquivo | eixo |
|---|---|
| `agents/edital-repertorio.md` | as 78 checagens do repertório destilado da base (ids obrigatórios, proibido inventar); rede de segurança dos demais eixos |
| `agents/edital-legalidade.md` | conformidade com a Lei 14.133/2021 e regulamentação; dispositivos revogados; tetos legais |
| `agents/edital-coerencia.md` | numeração, remissões internas, anexos citados vs. existentes, prazos/valores repetidos DENTRO de cada instrumento |
| `agents/edital-pendencias.md` | [PREENCHER], comentários internos (inclusive via extrato da camada Word), realces remanescentes, texto de modelo não adaptado |
| `agents/edital-adversarial.md` | vetores de impugnação e recurso (com coluna de probabilidade); inexequibilidade de preços (art. 59) |
| `agents/edital-amarracao.md` | aderência TR ↔ edital ↔ minuta de contrato (objeto, prazo, pagamento, sanção, valor da capa) |
| `agents/edital-exequibilidade.md` | exequibilidade e alocação processual de requisitos técnicos de execução (LACUNA / MAL ALOCADA — Súmula 15/TCESP); checagens EXQ registradas como apêndice do repertório |
| `agents/edital-portugues.md` | revisão linguística ativa PT-01..PT-07 (122 registros na base; PT-01 é a checagem mais frequente de toda a base) |
| `agents/edital-aritmetica.md` | verificação computacional: produtos × totais, somas, percentuais, identidade de valores (único agente com Bash, restrito a cálculo) |
| `commands/revisar-minuta.md` | comando `/revisar-minuta <caminho-absoluto>.docx [--diff ...] [--anterior ...]`: bootstrap de pandoc, conversão 1× com guarda de hash, extração da camada Word, detecção de perfil do certame, disparo dos 9 agentes em paralelo, consolidação com deduplicação por âncora e arbitragem por id, veredito com cobertura |
| `scripts/extrai_camada_docx.py` | extrai do .docx original o que o pandoc destrói: comentários (autor/âncora), realces por cor, track changes, fontes fora de Arial 12, células mescladas, hiperlinks |
| `scripts/sync-claude.sh` | sincronização claude-config → .claude + verificação de drift |
| `repertorio-revisao.md` | repertório completo: id, tipo, checagem, frequência na base, revisores, exemplo literal ancorado; notas de leitura; apêndice EXQ extra-base |

Invariantes dos nove agentes:
- somente-leitura (Read, Grep, Glob; o edital-aritmetica tem Bash restrito a cálculo);
- exigem caminho absoluto de arquivo JÁ CONVERTIDO para markdown no prompt de delegação;
- leitura integral paginada obrigatória (Read trunca em ~2.000 linhas; minutas reais passam de 22.000) com declaração de cobertura no retorno;
- régua de severidade comum (bloqueante/crítico/médio/nit) definida identicamente em todos;
- tabela padronizada com coluna de **trecho literal** (âncora verificável por Grep, chave de deduplicação), encerrada por `publicável` / `não publicável`;
- perfil do certame (modalidade/regime) injetado pelo comando como presunção auditável — supressões sempre declaradas, texto do documento prevalece.

## Instalação em outros projetos (opcional)

O projeto EDITAIS já carrega `.claude/` sozinho — NÃO instale em `~/.claude/` para usá-lo aqui:
uma cópia user-level compete com a de projeto e o resultado passa a depender de qual
`/revisar-minuta` é invocado. Para usar em OUTRO projeto, copie `claude-config/` para lá e
rode o sync, conferindo o `versao:` dos frontmatters após atualizar.

## Requisitos

- `pandoc` — o `/revisar-minuta` tenta instalar automaticamente se ausente.
- `python3` — para a extração da camada Word (etapa 1.5).
