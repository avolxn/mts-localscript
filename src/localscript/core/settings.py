from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MODEL = "qwen3.5:9b-q4_K_M"
DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"
DEFAULT_PORT = 8080
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RUNTIME_DIR = REPO_ROOT / ".localscript"


@dataclass(slots=True)
class Settings:
    model: str = DEFAULT_MODEL
    ollama_host: str = DEFAULT_OLLAMA_HOST
    timeout_seconds: float = 60.0
    num_ctx: int = 4096
    num_predict: int = 256
    batch: int = 1
    parallel: int = 1
    keep_alive: str = "10m"
    top_k_examples: int = 3
    candidate_count: int = 2
    max_revision_cycles: int = 1
    api_host: str = "0.0.0.0"
    api_port: int = DEFAULT_PORT
    max_vram_mb: int = 8000
    data_dir: Path = REPO_ROOT / "data"
    runtime_dir: Path = DEFAULT_RUNTIME_DIR
    database_path: Path = DEFAULT_RUNTIME_DIR / "localscript.db"
    workspace_root: Path = REPO_ROOT

    @classmethod
    def from_env(cls) -> Settings:
        runtime_dir = Path(os.getenv("LOCALSCRIPT_RUNTIME_DIR", str(DEFAULT_RUNTIME_DIR)))
        return cls(
            model=os.getenv("LOCALSCRIPT_MODEL", DEFAULT_MODEL),
            ollama_host=os.getenv("LOCALSCRIPT_OLLAMA_HOST", DEFAULT_OLLAMA_HOST),
            timeout_seconds=float(os.getenv("LOCALSCRIPT_TIMEOUT_SECONDS", "60")),
            num_ctx=int(os.getenv("LOCALSCRIPT_NUM_CTX", "4096")),
            num_predict=int(os.getenv("LOCALSCRIPT_NUM_PREDICT", "256")),
            batch=int(os.getenv("LOCALSCRIPT_BATCH", "1")),
            parallel=int(os.getenv("LOCALSCRIPT_PARALLEL", "1")),
            keep_alive=os.getenv("LOCALSCRIPT_KEEP_ALIVE", "10m"),
            top_k_examples=int(os.getenv("LOCALSCRIPT_TOP_K_EXAMPLES", "3")),
            candidate_count=int(os.getenv("LOCALSCRIPT_CANDIDATE_COUNT", "2")),
            max_revision_cycles=int(os.getenv("LOCALSCRIPT_MAX_REVISION_CYCLES", "1")),
            api_host=os.getenv("LOCALSCRIPT_HOST", "0.0.0.0"),
            api_port=int(os.getenv("LOCALSCRIPT_PORT", str(DEFAULT_PORT))),
            max_vram_mb=int(os.getenv("LOCALSCRIPT_MAX_VRAM_MB", "8000")),
            runtime_dir=runtime_dir,
            database_path=Path(os.getenv("LOCALSCRIPT_DATABASE_PATH", str(runtime_dir / "localscript.db"))),
            workspace_root=Path(os.getenv("LOCALSCRIPT_PROJECT_DIR", str(Path.cwd().resolve()))),
        )

    def validate_runtime(self) -> None:
        if self.num_ctx != 4096:
            raise ValueError("LocalScript requires num_ctx=4096 in the reference build.")
        if self.num_predict != 256:
            raise ValueError("LocalScript requires num_predict=256 in the reference build.")
        if self.batch != 1:
            raise ValueError("LocalScript requires batch=1 in the reference build.")
        if self.parallel != 1:
            raise ValueError("LocalScript requires parallel=1 in the reference build.")
        if not shutil.which("lua-language-server"):
            raise RuntimeError("LocalScript requires 'lua-language-server' to be installed and available in PATH.")
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.workspace_root.mkdir(parents=True, exist_ok=True)
