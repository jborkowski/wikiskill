"""OpenAI-compatible embeddings via MLX for CLM's Qwen3-8B encoder slot.

CLM heads are encoder-locked to **Qwen3-8B last-token pooling** (4096-d).
This is *not* Qwen3-Embedding-*; those models are incompatible with the
released CLM projection heads.

``clm.Embedder`` posts to ``/v1/embeddings`` (often with ``encoding_format=base64``)
and L2-normalizes client-side — so we return raw last-token hidden states.
"""

from __future__ import annotations

import base64
import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

DEFAULT_MODEL_ID = "qwen3-8b"
DEFAULT_HF_REPO = "mlx-community/Qwen3-8B-4bit"
DEFAULT_MAX_TOKENS = 2048


@dataclass(frozen=True)
class MlxEmbSettings:
    """Runtime settings for the MLX Qwen3-8B embedding application."""

    repo: str = DEFAULT_HF_REPO
    served_name: str = DEFAULT_MODEL_ID
    max_tokens: int = DEFAULT_MAX_TOKENS
    host: str = "127.0.0.1"
    port: int = 8090

    @classmethod
    def from_env(cls) -> MlxEmbSettings:
        return cls(
            repo=os.environ.get("WIKISKILL_MLX_REPO", DEFAULT_HF_REPO),
            served_name=os.environ.get("WIKISKILL_MLX_SERVED_NAME", DEFAULT_MODEL_ID),
            max_tokens=int(os.environ.get("WIKISKILL_MLX_MAX_TOKENS", str(DEFAULT_MAX_TOKENS))),
            host=os.environ.get("WIKISKILL_MLX_HOST", "127.0.0.1"),
            port=int(os.environ.get("WIKISKILL_MLX_PORT", "8090")),
        )


class EmbeddingRequest(BaseModel):
    model: str = DEFAULT_MODEL_ID
    input: str | list[str]
    encoding_format: Literal["float", "base64"] = "float"
    truncate_prompt_tokens: int | None = None


class EmbeddingData(BaseModel):
    object: Literal["embedding"] = "embedding"
    index: int
    embedding: list[float] | str


class EmbeddingUsage(BaseModel):
    prompt_tokens: int
    total_tokens: int


class EmbeddingResponse(BaseModel):
    object: Literal["list"] = "list"
    model: str
    data: list[EmbeddingData]
    usage: EmbeddingUsage


class ModelCard(BaseModel):
    id: str
    object: Literal["model"] = "model"
    owned_by: str = "wikiskill-mlx"


class ModelsResponse(BaseModel):
    object: Literal["list"] = "list"
    data: list[ModelCard]


class Encoder:
    """Lazy-loaded MLX Qwen3 causal LM used only for last-token hidden states."""

    def __init__(self, repo: str, max_tokens: int, served_name: str) -> None:
        self.repo = repo
        self.max_tokens = max_tokens
        self.served_name = served_name
        self._model: Any = None
        self._tokenizer: Any = None

    def load(self) -> None:
        import mlx.core as mx
        from mlx_lm import load

        self._model, self._tokenizer = load(self.repo)
        _ = self.embed(["ok"])
        mx.eval(mx.array(0))

    @property
    def ready(self) -> bool:
        return self._model is not None and self._tokenizer is not None

    def embed(self, texts: list[str], max_tokens: int | None = None) -> tuple[list[np.ndarray], int]:
        import mlx.core as mx

        if not self.ready:
            raise RuntimeError("encoder not loaded")
        assert self._model is not None and self._tokenizer is not None

        limit = max_tokens or self.max_tokens
        vectors: list[np.ndarray] = []
        prompt_tokens = 0

        for text in texts:
            encoded = self._tokenizer.encode(text)
            if not isinstance(encoded, list):
                encoded = list(encoded)
            if len(encoded) > limit:
                encoded = encoded[:limit]
            prompt_tokens += len(encoded)
            if not encoded:
                hidden_size = int(self._model.args.hidden_size)
                vectors.append(np.zeros(hidden_size, dtype=np.float32))
                continue

            ids = mx.array(encoded)[None, :]
            hidden = self._model.model(ids)
            last = hidden[:, -1, :]
            mx.eval(last)
            vectors.append(np.array(last[0], dtype=np.float32))

        return vectors, prompt_tokens


_encoder: Encoder | None = None


def get_encoder() -> Encoder:
    if _encoder is None:
        raise RuntimeError("encoder singleton not initialized")
    return _encoder


def create_app(settings: MlxEmbSettings | None = None) -> FastAPI:
    """Build the FastAPI app; call ``run(settings)`` to serve it."""
    cfg = settings or MlxEmbSettings.from_env()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        global _encoder
        _encoder = Encoder(
            repo=cfg.repo, max_tokens=cfg.max_tokens, served_name=cfg.served_name
        )
        print(
            f"[mlx-emb] loading {cfg.repo} as {cfg.served_name} "
            f"(max_tokens={cfg.max_tokens})…",
            flush=True,
        )
        t0 = time.perf_counter()
        _encoder.load()
        print(f"[mlx-emb] ready in {time.perf_counter() - t0:.1f}s", flush=True)
        yield
        _encoder = None

    application = FastAPI(title="wikiskill-mlx-emb", lifespan=lifespan)

    @application.get("/health")
    def health() -> dict[str, bool]:
        return {"ok": get_encoder().ready}

    @application.get("/v1/models", response_model=ModelsResponse)
    def models() -> ModelsResponse:
        enc = get_encoder()
        return ModelsResponse(data=[ModelCard(id=enc.served_name), ModelCard(id=enc.repo)])

    @application.post("/v1/embeddings", response_model=EmbeddingResponse)
    def embeddings(req: EmbeddingRequest) -> EmbeddingResponse:
        enc = get_encoder()
        texts = [req.input] if isinstance(req.input, str) else list(req.input)
        if not texts:
            raise HTTPException(status_code=400, detail="input must not be empty")
        try:
            vecs, tokens = enc.embed(texts, max_tokens=req.truncate_prompt_tokens)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=str(e)) from e

        data: list[EmbeddingData] = []
        for i, v in enumerate(vecs):
            if req.encoding_format == "base64":
                payload: list[float] | str = base64.b64encode(
                    v.astype(np.float32).tobytes()
                ).decode("ascii")
            else:
                payload = v.astype(np.float32).tolist()
            data.append(EmbeddingData(index=i, embedding=payload))

        return EmbeddingResponse(
            model=req.model or enc.served_name,
            data=data,
            usage=EmbeddingUsage(prompt_tokens=tokens, total_tokens=tokens),
        )

    return application


# Default ASGI app for process managers that import ``module:app``.
app = create_app()


def run(settings: MlxEmbSettings | None = None) -> None:
    """Serve the embedding app (programmatic; no argv parsing)."""
    import uvicorn

    cfg = settings or MlxEmbSettings.from_env()
    uvicorn.run(create_app(cfg), host=cfg.host, port=cfg.port, log_level="info")
