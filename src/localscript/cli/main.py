from __future__ import annotations

import argparse
import sys
from pathlib import Path

import uvicorn

from localscript.acp import build_agent_definition
from localscript.api import create_app
from localscript.core import Settings
from localscript.logs import configure_logging, get_logger

logger = get_logger(__name__)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if not getattr(args, "command", None):
        parser.print_help()
        return

    try:
        settings = _settings_from_args(args)
        configure_logging(settings.runtime_dir)
        args.func(args, settings)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
    except Exception as exc:
        if "settings" in locals():
            logger.exception("LocalScript CLI failed.")
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="LocalScript: local Lua codegen system on top of Ollama"
    )
    subparsers = parser.add_subparsers(dest="command")

    serve = subparsers.add_parser("serve", help="Run the LocalScript HTTP API")
    _add_runtime_arguments(serve, include_server=True)
    serve.set_defaults(func=run_serve)

    acp = subparsers.add_parser("acp", help="Run the LocalScript ACP backend over stdio")
    _add_runtime_arguments(acp)
    acp.set_defaults(func=run_acp)

    ui = subparsers.add_parser("ui", help="Run LocalScript UI with the bundled ACP backend")
    ui.add_argument("project_dir", nargs="?", default=".")
    ui.set_defaults(func=run_ui)

    return parser


def _add_runtime_arguments(
    parser: argparse.ArgumentParser,
    *,
    include_server: bool = False,
) -> None:
    env = Settings.from_env()
    parser.add_argument("--model", default=env.model)
    parser.add_argument("--ollama-host", default=env.ollama_host)
    parser.add_argument("--timeout-seconds", type=float, default=env.timeout_seconds)
    parser.add_argument("--num-ctx", type=int, default=4096)
    parser.add_argument("--num-predict", type=int, default=256)
    parser.add_argument("--batch", type=int, default=1)
    parser.add_argument("--parallel", type=int, default=1)
    parser.add_argument("--candidate-count", type=int, default=env.candidate_count)
    parser.add_argument("--project-dir", default=str(env.workspace_root))
    if include_server:
        parser.add_argument("--host", default=env.api_host)
        parser.add_argument("--port", type=int, default=env.api_port)


def _settings_from_args(args: argparse.Namespace) -> Settings:
    env = Settings.from_env()
    return Settings(
        model=getattr(args, "model", env.model),
        ollama_host=getattr(args, "ollama_host", env.ollama_host),
        timeout_seconds=getattr(args, "timeout_seconds", env.timeout_seconds),
        num_ctx=getattr(args, "num_ctx", env.num_ctx),
        num_predict=getattr(args, "num_predict", env.num_predict),
        batch=getattr(args, "batch", env.batch),
        parallel=getattr(args, "parallel", env.parallel),
        keep_alive=env.keep_alive,
        top_k_examples=env.top_k_examples,
        candidate_count=getattr(args, "candidate_count", env.candidate_count),
        max_revision_cycles=env.max_revision_cycles,
        api_host=getattr(args, "host", env.api_host),
        api_port=getattr(args, "port", env.api_port),
        max_vram_mb=env.max_vram_mb,
        data_dir=env.data_dir,
        runtime_dir=env.runtime_dir,
        database_path=env.database_path,
        workspace_root=Path(getattr(args, "project_dir", env.workspace_root)).resolve(),
    )


def run_serve(_args: argparse.Namespace, settings: Settings) -> None:
    settings.validate_runtime()
    app = create_app(settings)
    uvicorn.run(app, host=settings.api_host, port=settings.api_port, workers=1)


def run_acp(_args: argparse.Namespace, settings: Settings) -> None:
    import asyncio

    from localscript.acp import LocalScriptACPBackend

    asyncio.run(LocalScriptACPBackend(settings).serve_forever())


def run_ui(args: argparse.Namespace, settings: Settings) -> None:
    from localscript_ui.app import ToadApp

    _ = settings
    project_dir = str(Path(args.project_dir).resolve())
    app = ToadApp(
        agent_data=build_agent_definition(),
        project_dir=project_dir,
    )
    app.run()
    app.run_on_exit()
