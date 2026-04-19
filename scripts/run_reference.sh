#!/usr/bin/env bash
set -euo pipefail

COMMAND="${1:-serve}"
if [[ $# -gt 0 ]]; then
  shift
fi

MODEL="${LOCALSCRIPT_MODEL:-qwen3.5:9b-q4_K_M}"
OLLAMA_HOST="${LOCALSCRIPT_OLLAMA_HOST:-http://127.0.0.1:11434}"
RUNTIME_DIR="${LOCALSCRIPT_RUNTIME_DIR:-.localscript}"
HOST="${LOCALSCRIPT_HOST:-0.0.0.0}"
PORT="${LOCALSCRIPT_PORT:-8080}"
CANDIDATE_COUNT="${LOCALSCRIPT_CANDIDATE_COUNT:-2}"

export PATH="${RUNTIME_DIR}/bin:${PATH}"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Required command not found: $1" >&2
    exit 1
  fi
}

preflight() {
  require_command uv
  require_command ollama
  if ! command -v lua-language-server >/dev/null 2>&1; then
    echo "Lua Language Server is not installed for LocalScript reference runtime." >&2
    echo "Run: scripts/install_reference.sh" >&2
    exit 1
  fi
}

preflight

COMMON_ARGS=(
  --model "${MODEL}"
  --ollama-host "${OLLAMA_HOST}"
  --num-ctx 4096
  --num-predict 256
  --batch 1
  --parallel 1
  --candidate-count "${CANDIDATE_COUNT}"
)

if [[ "${COMMAND}" == "serve" ]]; then
  exec uv run localscript "${COMMAND}" \
    "${COMMON_ARGS[@]}" \
    --host "${HOST}" \
    --port "${PORT}" \
    "$@"
fi

exec uv run localscript "${COMMAND}" \
  "${COMMON_ARGS[@]}" \
  "$@"
