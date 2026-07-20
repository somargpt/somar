#!/usr/bin/env bash
# Sincroniza a FONTE ÚNICA claude-config/ -> .claude/ (a cópia que o Claude Code carrega).
# Direção: sempre claude-config -> .claude. Nunca edite .claude/ diretamente.
#
# Uso:
#   scripts/sync-claude.sh          sincroniza (idempotente) e imprime a versão
#   scripts/sync-claude.sh --check  apenas verifica drift; exit 1 se divergir (para CI/hook)
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SRC="$REPO_DIR/claude-config"
DST="$REPO_DIR/.claude"

if [[ "${1:-}" == "--check" ]]; then
  drift=0
  diff -rq "$SRC/agents" "$DST/agents" || drift=1
  diff -q "$SRC/commands/revisar-minuta.md" "$DST/commands/revisar-minuta.md" || drift=1
  diff -rq "$SRC/scripts" "$DST/scripts" || drift=1
  if [[ $drift -ne 0 ]]; then
    echo "DRIFT detectado entre claude-config/ e .claude/ — rode scripts/sync-claude.sh" >&2
    exit 1
  fi
  echo "OK: claude-config/ e .claude/ sincronizados."
  exit 0
fi

mkdir -p "$DST/agents" "$DST/commands" "$DST/scripts"
cp "$SRC"/agents/*.md "$DST/agents/"
cp "$SRC/commands/revisar-minuta.md" "$DST/commands/"
cp "$SRC"/scripts/extrai_camada_docx.py "$DST/scripts/"
cp "$SRC/scripts/sync-claude.sh" "$DST/scripts/"

versao=$(grep -m1 '^versao:' "$SRC/agents/edital-repertorio.md" | awk '{print $2}')
echo "Sincronizado claude-config/ -> .claude/ (versão ${versao:-desconhecida})."
