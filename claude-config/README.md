# Configuração Claude Code — Revisão de Minutas TCESP

Subagentes de revisão de minutas de editais/TR/contratos do TCESP, destilados da base
"Padrão de Revisão" do CLAUDE BRAIN (Notion): 889 registros lidos na íntegra
(2025-10-22 → 2026-07-16), consolidados em 77 checagens deduplicadas.

## Instalação (user-level, vale para todos os projetos)

Copie o conteúdo para o seu `~/.claude/`:

```bash
mkdir -p ~/.claude/agents ~/.claude/commands
cp claude-config/agents/*.md ~/.claude/agents/
cp claude-config/commands/revisar-minuta.md ~/.claude/commands/
cp claude-config/repertorio-revisao.md ~/.claude/
```

## Conteúdo

| arquivo | eixo |
|---|---|
| `agents/edital-repertorio.md` | apenas as 77 checagens do repertório destilado da base (ids obrigatórios, proibido inventar) |
| `agents/edital-legalidade.md` | conformidade com a Lei 14.133/2021 e regulamentação; dispositivos revogados |
| `agents/edital-coerencia.md` | numeração, remissões internas, anexos citados vs. existentes, prazos |
| `agents/edital-pendencias.md` | [PREENCHER], comentários internos visíveis, texto de modelo não adaptado |
| `agents/edital-adversarial.md` | vetores de impugnação e recurso: o que um licitante atacaria primeiro |
| `agents/edital-amarracao.md` | aderência TR ↔ edital ↔ minuta de contrato (objeto, prazo, pagamento, sanção) |
| `agents/edital-exequibilidade.md` | exequibilidade e alocação processual de requisitos técnicos de execução: necessidade sinalizada no TR (vínculo com fabricante, RMA, suporte avançado, certificações) que o edital não operacionaliza (LACUNA) ou aloca na fase errada (Súmula 15/TCESP) |
| `commands/revisar-minuta.md` | comando `/revisar-minuta <caminho-absoluto>.docx`: converte 1× com pandoc, dispara os 7 agentes em paralelo, consolida e deduplica |
| `repertorio-revisao.md` | repertório completo: id, tipo, checagem, frequência na base, revisores, exemplo literal ancorado |

Todos os agentes são read-only (Read, Grep, Glob), `model: inherit`, exigem caminho
absoluto no prompt de delegação e retornam tabela padronizada
(severidade | localização | achado | fundamento | correção proposta) encerrada por
`publicável` / `não publicável`.

## Requisitos

- `pandoc` instalado (para o `/revisar-minuta`).
- Skills referenciadas nos frontmatters (`padrao-de-revisao`, `revisao-edital-tcesp`,
  `adversarial-review`): se não existirem no seu ambiente, o campo `skills:` é
  ignorado sem quebrar os agentes.
