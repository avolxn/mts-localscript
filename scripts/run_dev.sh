#!/usr/bin/env bash
set -euo pipefail

COMMAND="${1:-ui}"
if [[ $# -gt 0 ]]; then
  shift
fi

MODEL="${LOCALSCRIPT_MODEL:-qwen2.5-coder:1.5b}"
OLLAMA_HOST="${LOCALSCRIPT_OLLAMA_HOST:-http://127.0.0.1:11434}"
RUNTIME_DIR="${LOCALSCRIPT_RUNTIME_DIR:-.localscript}"
HOST="${LOCALSCRIPT_HOST:-127.0.0.1}"
PORT="${LOCALSCRIPT_PORT:-8080}"
CANDIDATE_COUNT="${LOCALSCRIPT_CANDIDATE_COUNT:-1}"

export PATH="${RUNTIME_DIR}/bin:${PATH}"
export LOCALSCRIPT_MODEL="${MODEL}"
export LOCALSCRIPT_OLLAMA_HOST="${OLLAMA_HOST}"
export LOCALSCRIPT_RUNTIME_DIR="${RUNTIME_DIR}"
export LOCALSCRIPT_HOST="${HOST}"
export LOCALSCRIPT_PORT="${PORT}"
export LOCALSCRIPT_CANDIDATE_COUNT="${CANDIDATE_COUNT}"
export LOCALSCRIPT_NUM_CTX="${LOCALSCRIPT_NUM_CTX:-4096}"
export LOCALSCRIPT_NUM_PREDICT="${LOCALSCRIPT_NUM_PREDICT:-256}"
export LOCALSCRIPT_BATCH="${LOCALSCRIPT_BATCH:-1}"
export LOCALSCRIPT_PARALLEL="${LOCALSCRIPT_PARALLEL:-1}"

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
    echo "Lua Language Server is not installed for LocalScript dev runtime." >&2
    echo "Run: scripts/install_dev.sh" >&2
    exit 1
  fi
}

preflight

wait_for_http() {
  local url="$1"
  local max_attempts="${2:-50}"
  local attempt=1
  while [[ "${attempt}" -le "${max_attempts}" ]]; do
    if curl -fsS "${url}" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.2
    attempt=$((attempt + 1))
  done
  return 1
}

COMMON_ARGS=(
  --model "${MODEL}"
  --ollama-host "${OLLAMA_HOST}"
  --num-ctx 4096
  --num-predict 256
  --batch 1
  --parallel 1
  --candidate-count "${CANDIDATE_COUNT}"
)

if [[ "${COMMAND}" == "ui" ]]; then
  exec uv run localscript "${COMMAND}" . "$@"
fi

if [[ "${COMMAND}" == "serve" ]]; then
  exec uv run localscript "${COMMAND}" \
    "${COMMON_ARGS[@]}" \
    --host "${HOST}" \
    --port "${PORT}" \
    "$@"
fi

if [[ "${COMMAND}" == "all" ]]; then
  require_command curl

  uv run localscript serve \
    "${COMMON_ARGS[@]}" \
    --host "${HOST}" \
    --port "${PORT}" \
    "$@" &
  API_PID=$!

  cleanup() {
    if kill -0 "${API_PID}" >/dev/null 2>&1; then
      kill "${API_PID}" >/dev/null 2>&1 || true
      wait "${API_PID}" 2>/dev/null || true
    fi
  }

  trap cleanup EXIT INT TERM

  echo "Starting LocalScript API on http://${HOST}:${PORT}"
  if ! wait_for_http "http://${HOST}:${PORT}/docs"; then
    echo "LocalScript API did not become ready in time." >&2
    exit 1
  fi

  echo "Opening LocalScript UI with bundled ACP backend"
  uv run localscript ui .
  exit 0
fi

exec uv run localscript "${COMMAND}" \
  "${COMMON_ARGS[@]}" \
  "$@"
