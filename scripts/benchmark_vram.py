from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass

from localscript.core import Settings
from localscript.modes import build_lua_codegen_mode


@dataclass(slots=True)
class VramBenchmarkResult:
    peak_mb: int
    limit_mb: int
    passed: bool
    samples: list[int]


class NvidiaSmiMonitor:
    def __init__(self, *, gpu_index: int = 0, poll_interval_seconds: float = 0.2) -> None:
        self.gpu_index = gpu_index
        self.poll_interval_seconds = poll_interval_seconds
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self.samples: list[int] = []

    def start(self) -> None:
        _require_command("nvidia-smi")
        self._stop_event.clear()
        self.samples.clear()
        self._thread = threading.Thread(target=self._poll, daemon=True)
        self._thread.start()

    def stop(self) -> list[int]:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        return self.samples

    def _poll(self) -> None:
        while not self._stop_event.is_set():
            self.samples.append(query_nvidia_smi(self.gpu_index))
            time.sleep(self.poll_interval_seconds)


def query_nvidia_smi(gpu_index: int = 0) -> int:
    _require_command("nvidia-smi")
    output = subprocess.check_output(
        ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
        text=True,
    )
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if gpu_index >= len(lines):
        raise IndexError(f"GPU index {gpu_index} is out of range for nvidia-smi output.")
    return int(lines[gpu_index])


def _require_command(command: str) -> str:
    resolved = shutil.which(command)
    if not resolved:
        raise RuntimeError(f"Required command '{command}' is not installed or is not available in PATH.")
    return resolved


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure peak VRAM during one LocalScript generation")
    parser.add_argument("--prompt", required=True, help="Prompt to generate against")
    parser.add_argument("--gpu-index", type=int, default=0, help="GPU index to sample with nvidia-smi")
    parser.add_argument("--poll-interval", type=float, default=0.2, help="Sampling interval in seconds")
    parser.add_argument("--max-vram-mb", type=int, default=8000, help="Peak VRAM limit in MiB")
    args = parser.parse_args()

    settings = Settings.from_env()
    settings.validate_runtime()
    codegen_mode = build_lua_codegen_mode(settings)
    monitor = NvidiaSmiMonitor(gpu_index=args.gpu_index, poll_interval_seconds=args.poll_interval)
    monitor.start()
    generation_result = codegen_mode.generate_one_shot(args.prompt)
    samples = monitor.stop()
    if not samples:
        raise RuntimeError("No nvidia-smi samples were collected.")

    result = VramBenchmarkResult(
        peak_mb=max(samples),
        limit_mb=args.max_vram_mb,
        passed=max(samples) <= args.max_vram_mb,
        samples=samples,
    )
    payload = {
        "peak_mb": result.peak_mb,
        "limit_mb": result.limit_mb,
        "passed": result.passed,
        "sample_count": len(result.samples),
        "task_profile": generation_result.task_profile.summary(),
        "candidate_scores": [round(candidate.score, 2) for candidate in generation_result.candidates],
        "stage_metrics": [
            {
                "name": metric.name,
                "duration_ms": round(metric.duration_ms, 2),
                "gpu_memory_mb_before": metric.gpu_memory_mb_before,
                "gpu_memory_mb_after": metric.gpu_memory_mb_after,
                "details": metric.details,
            }
            for metric in generation_result.stage_metrics
        ],
        "session_id": generation_result.metadata.get("session_id"),
        "code": generation_result.final_code,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    if not result.passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
