"""MLX embedding FastAPI app for CLM's Qwen3-8B encoder slot."""

from wikiskill_eval.mlx_emb.server import MlxEmbSettings, app, create_app, run

__all__ = ["MlxEmbSettings", "app", "create_app", "run"]
