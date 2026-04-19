#!/usr/bin/env bash
set -euo pipefail

MODEL="${LOCALSCRIPT_MODEL:-qwen2.5-coder:1.5b}"
OLLAMA_HOST="${LOCALSCRIPT_OLLAMA_HOST:-http://127.0.0.1:11434}"
RUNTIME_DIR="${LOCALSCRIPT_RUNTIME_DIR:-.localscript}"
OLLAMA_LOG="${RUNTIME_DIR}/ollama-dev.log"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Required command not found: $1" >&2
    exit 1
  fi
}

ollama_ready() {
  OLLAMA_HOST="${OLLAMA_HOST}" ollama list >/dev/null 2>&1
}

start_ollama_if_needed() {
  if ollama_ready; then
    echo "Ollama is already running at ${OLLAMA_HOST}"
    return
  fi

  mkdir -p "${RUNTIME_DIR}"
  echo "Starting Ollama server for dev runtime..."
  nohup env \
    OLLAMA_HOST="${OLLAMA_HOST}" \
    OLLAMA_NUM_PARALLEL=1 \
    OLLAMA_MAX_LOADED_MODELS=1 \
    OLLAMA_CONTEXT_LENGTH=4096 \
    ollama serve >"${OLLAMA_LOG}" 2>&1 &

  for _ in $(seq 1 30); do
    if ollama_ready; then
      echo "Ollama is ready at ${OLLAMA_HOST}"
      return
    fi
    sleep 1
  done

  echo "Failed to start Ollama. Check ${OLLAMA_LOG}" >&2
  exit 1
}

require_command uv
require_command ollama

echo "Installing Python dependencies with uv..."
uv sync --dev

echo "Installing Lua Language Server toolchain..."
"$(dirname "$0")/install_lua_language_server.sh"

start_ollama_if_needed

echo "Pulling dev model ${MODEL}..."
OLLAMA_HOST="${OLLAMA_HOST}" ollama pull "${MODEL}"

echo "Dev installation complete."
echo "Next steps:"
echo "  scripts/run_dev.sh ui"
echo "  scripts/run_dev.sh serve"
