# LocalScript

LocalScript is a local multi-agent system for generating Lua code on top of Ollama. The required `POST /generate` HTTP contract remains unchanged.

## Architecture

LocalScript uses these agent roles sequentially on one local model:

- `TranslatorAgent`: translates non-English user prompts and feedback into English for downstream agents while preserving code and workflow identifiers.
- `ClarifierAgent`: decides whether explicit user clarification is needed and proposes assumptions.
- `ContextAgent`: searches and synthesizes local knowledge from bundled docs, rules, examples, OpenAPI spec, and Lua/LowCode patterns.
- `CoderAgent`: produces one or more Lua drafts with different coding strategies.
- `ReviewerAgent`: critiques each draft against the task and local constraints.
- `RepairAgent`: revises code using reviewer findings, verifier findings, and user feedback.
- `LuaStaticValidator`: runs static Lua and workflow-specific rule checks.
- `LuaLspValidator`: runs LuaLS workspace diagnostics over generated code.
- `LuaValidator`: runs the composed Lua validation pipeline, combining static checks and mandatory LuaLS diagnostics.

The orchestration state is persisted in SQLite so every generation session has:

- user and assistant messages
- trace records per agent step
- latest code and summary
- session status such as `waiting_for_clarification` or `complete`

## What Is Indexed Locally

The local KB is built from files in `data/` and indexed into SQLite FTS:

- `data/public_localscript_dataset.md`
- `data/localscript_rules.md`
- `data/localscript-openapi.yaml`
- `data/lua_patterns.md`
- `data/regression_expectations.json`

This means retrieval does not depend only on the small public dataset. The dataset is just one of several local knowledge sources.

## Prompt Normalization

If a user prompt or refinement message is not in English, LocalScript translates it into English internally before
clarification, retrieval, generation, review, and repair. The original user text is preserved in session history, and
the translation step is recorded in trace records.

## Reference Runtime

- Model: `qwen3.5:9b-q4_K_M` (Qwen 3.5 9B, 4-bit quantization)
- `num_ctx=4096`
- `num_predict=256`
- `batch=1`
- `parallel=1`
- Peak VRAM target: `<= 8.0 GB`

LocalScript enforces the reference build constraints in code.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- [Ollama](https://ollama.com/)
- NVIDIA GPU with 8 GB VRAM
- `nvidia-smi`
- SQLite build with FTS5 enabled

## Install

Reference install:

```bash
scripts/install_reference.sh
```

Lightweight dev install for CPU testing on Mac with `qwen2.5-coder:1.5b`:

```bash
scripts/install_dev.sh
```

These install scripts:

- run `uv sync --dev`
- install the local LuaLS toolchain into `.localscript/bin`
- start `ollama serve` if it is not already running
- pull the required model

## Interface

The HTTP API is available through the launch wrappers:

```bash
scripts/run_reference.sh serve
scripts/run_dev.sh serve
```

### Required Contract

- `POST /generate`
- Request: `{"prompt": "..." }`
- Response: `{"code": "..." }`

Example:

```bash
curl -s http://127.0.0.1:8080/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Функция factorial(n) для n >= 0"}'
```

## UI Integration

The hackathon API stays limited to `POST /generate`. LocalScript UI integration uses a separate local ACP backend over `stdio`.

Launch the bundled UI directly:

```bash
uv run localscript ui .
```

Or launch the vendored UI and select the built-in `LocalScript` agent:

```bash
uv run localscript-ui .
```

Available UI modes:

- `general`: project-aware local agent with file/search/write/shell tools
- `lua_codegen`: the LocalScript multi-agent Lua generation pipeline

## Verification

Validation is not limited to prompt heuristics. The Lua validation pipeline combines:

- static Lua/LowCode validation
- task-aware checks
- mandatory semantic diagnostics through `lua-language-server --check`

Reviewer feedback and validation output are both fed into the repair agent before the final answer is accepted.

## Evaluate On The Bundled Dataset

```bash
uv run python scripts/evaluate_dataset.py --dataset data/public_localscript_dataset.md
```

The evaluator reports:

- validation status
- token-overlap ratio
- regression expectation pass/fail
- selected candidate scores
- generated code
- session id for the run

## Benchmark VRAM

```bash
uv run python scripts/benchmark_vram.py \
  --prompt "Convert wf.initVariables.recallTime to unix format in Lua" \
  --max-vram-mb 8000
```

The benchmark output includes:

- peak VRAM
- selected candidate scores
- stage-level timing
- final code
- session id

## Tests

Deterministic test suite:

```bash
uv run pytest
```

Optional live-model smoke test:

```bash
RUN_LOCAL_MODEL_TESTS=1 uv run pytest tests/test_live_smoke.py
```

## Project Layout

- `src/localscript/agents/`: one file per agent role
- `src/localscript/api/app.py`: API with the required `/generate` endpoint
- `src/localscript/api/schemas.py`: HTTP request and response models for `/generate`
- `src/localscript/cli/main.py`: `serve` entrypoint
- `src/localscript/modes/`: per-mode orchestration and session execution
- `src/localscript/ollama.py`: thin adapter over the official Ollama Python client
- `src/localscript/storage/sqlite.py`: session persistence and SQLite-backed KB index
- `src/localscript/validation/lua_lsp.py`: LuaLS-based semantic validation over generated code
- `src/localscript/validation/lua_static.py`: static Lua and workflow-specific validation rules
- `src/localscript/validation/lua_validator.py`: composed Lua validation with static checks and mandatory LuaLS
- `scripts/install_lua_language_server.sh`: local LuaLS bootstrap for supported macOS and Linux targets
- `scripts/install_reference.sh`: reference environment bootstrap and model pull
- `scripts/install_dev.sh`: lightweight dev environment bootstrap and model pull
- `scripts/run_reference.sh`: reference launch wrapper for the HTTP API
- `scripts/run_dev.sh`: lightweight dev launch wrapper for the HTTP API
- `scripts/evaluate_dataset.py`: dataset evaluation script
- `scripts/benchmark_vram.py`: VRAM benchmark script
- `data/lua_patterns.md`: local generic Lua and LowCode patterns
- `data/public_localscript_dataset.md`: public sample tasks
- `data/localscript-openapi.yaml`: required API contract

## Notes

- No external AI vendors or external APIs are used.
- All orchestration runs locally against Ollama.
- The same local model is reused across agent roles to stay within the 8 GB GPU envelope.
