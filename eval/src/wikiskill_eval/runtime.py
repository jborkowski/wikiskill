"""Process runtime: MLX embeddings + clm-serve as child processes."""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import IO

import httpx

from wikiskill_eval.mlx_emb.server import MlxEmbSettings


@dataclass(frozen=True)
class RuntimePorts:
    emb: int = 8090
    clm: int = 8700


class EvalRuntime:
    """Start encoder + clm-serve, wait until healthy, tear down on exit."""

    def __init__(
        self,
        ports: RuntimePorts | None = None,
        *,
        emb_settings: MlxEmbSettings | None = None,
        clm_device: str = "mps",
        ready_timeout_s: float = 900.0,
    ) -> None:
        self.ports = ports or RuntimePorts()
        self.emb_settings = emb_settings or MlxEmbSettings(
            host="127.0.0.1",
            port=self.ports.emb,
        )
        self.clm_device = clm_device
        self.ready_timeout_s = ready_timeout_s
        self._procs: list[subprocess.Popen[str]] = []
        self._log_handles: list[IO[str]] = []

    @property
    def emb_url(self) -> str:
        return f"http://127.0.0.1:{self.ports.emb}/v1/embeddings"

    @property
    def clm_base_url(self) -> str:
        return f"http://127.0.0.1:{self.ports.clm}"

    def __enter__(self) -> EvalRuntime:
        self.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.stop()

    def start(self) -> None:
        default_log = Path(tempfile.gettempdir()) / "wikiskill-eval"
        log_dir = Path(os.environ.get("WIKISKILL_EVAL_LOG_DIR", str(default_log)))
        log_dir.mkdir(parents=True, exist_ok=True)

        emb_log = (log_dir / "mlx-emb.log").open("w", encoding="utf-8")
        clm_log = (log_dir / "clm-serve.log").open("w", encoding="utf-8")
        self._log_handles.extend([emb_log, clm_log])

        emb_env = os.environ.copy()
        emb_env["WIKISKILL_MLX_REPO"] = self.emb_settings.repo
        emb_env["WIKISKILL_MLX_SERVED_NAME"] = self.emb_settings.served_name
        emb_env["WIKISKILL_MLX_MAX_TOKENS"] = str(self.emb_settings.max_tokens)
        emb_env["WIKISKILL_MLX_HOST"] = "127.0.0.1"
        emb_env["WIKISKILL_MLX_PORT"] = str(self.ports.emb)

        emb_proc = subprocess.Popen(
            [
                sys.executable,
                "-c",
                "from wikiskill_eval.mlx_emb.server import MlxEmbSettings, run; "
                "run(MlxEmbSettings.from_env())",
            ],
            env=emb_env,
            stdout=emb_log,
            stderr=subprocess.STDOUT,
            text=True,
        )
        self._procs.append(emb_proc)

        self._wait_http(
            f"http://127.0.0.1:{self.ports.emb}/health",
            label="mlx-emb",
            proc=emb_proc,
            log_path=log_dir / "mlx-emb.log",
        )

        clm_bin = shutil.which("clm-serve")
        if clm_bin is None:
            self.stop()
            raise RuntimeError("clm-serve not on PATH (run via `uv run` so the venv is active)")

        clm_env = os.environ.copy()
        clm_env["CLM_EMB_URL"] = self.emb_url
        clm_env["CLM_EMB_MODEL"] = self.emb_settings.served_name
        clm_env["CLM_DEVICE"] = self.clm_device

        clm_proc = subprocess.Popen(
            [
                clm_bin,
                "--port",
                str(self.ports.clm),
                "--emb-url",
                self.emb_url,
                "--emb-model",
                self.emb_settings.served_name,
                "--device",
                self.clm_device,
                "--no-ui",
            ],
            env=clm_env,
            stdout=clm_log,
            stderr=subprocess.STDOUT,
            text=True,
        )
        self._procs.append(clm_proc)

        self._wait_http(
            f"{self.clm_base_url}/health",
            label="clm-serve",
            proc=clm_proc,
            log_path=log_dir / "clm-serve.log",
        )

    def stop(self) -> None:
        for proc in reversed(self._procs):
            self._terminate(proc)
        self._procs.clear()
        for handle in self._log_handles:
            handle.close()
        self._log_handles.clear()

    def _wait_http(
        self,
        url: str,
        *,
        label: str,
        proc: subprocess.Popen[str],
        log_path: Path,
    ) -> None:
        deadline = time.monotonic() + self.ready_timeout_s
        last_err = ""
        with httpx.Client(timeout=2.0) as client:
            while time.monotonic() < deadline:
                if proc.poll() is not None:
                    tail = _tail(log_path)
                    raise RuntimeError(
                        f"{label} exited early (code={proc.returncode}). log tail:\n{tail}"
                    )
                try:
                    r = client.get(url)
                    if r.status_code == 200:
                        body = r.json()
                        if body.get("ok", True):
                            return
                except (httpx.HTTPError, ValueError) as e:
                    last_err = str(e)
                time.sleep(0.5)
        raise TimeoutError(
            f"{label} not ready within {self.ready_timeout_s:.0f}s ({url}). "
            f"last_error={last_err!r}. log: {log_path}"
        )

    @staticmethod
    def _terminate(proc: subprocess.Popen[str]) -> None:
        if proc.poll() is not None:
            return
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


def _tail(path: Path, n: int = 40) -> str:
    if not path.exists():
        return "(no log)"
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[-n:])
