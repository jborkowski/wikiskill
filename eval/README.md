# wikiskill-eval

Python library for rough skill-run evaluation with [CLM](https://huggingface.co/Contrastive-LM/CLM-v0.1-8B).
Pipeline code lives in `wikiskill_eval` — import and call it; no shell wrappers.

On Apple Silicon, `wikiskill_eval.mlx_emb` is a FastAPI app that serves **Qwen3-8B last-token**
embeddings (CLM encoder slot). Not Qwen3-Embedding-*. Official CLM pulls `vllm` for CUDA
pooling; this project excludes that transitive dep via uv and uses MLX instead.

## Install

From the **repository root** (not only `eval/`):

```bash
uv sync
uv run eval run
uv run eval commit-msg "feat(eval): add CLM commit-msg density check"
```

| Command | Purpose |
|---|---|
| `eval run` | Smoke: invoice System One → `department=billing` |
| `eval commit-msg` | **Hard gate:** CLM rejects slop / weak messages (`PASS`/`FAIL`, exit 1 on fail; fails closed if CLM down) |
| `eval score-sessions` | Pi session JSONL → `RunEvidence` / `EvaluationRecord` under `--out` (default `eval/.runs/`) |
| `eval next-stage` | Aggregate scored runs → next skill-stage evaluation brief (markdown + JSON) |

Both `run` / `commit-msg` start MLX emb + `clm-serve` as subprocesses, then tear down. `score-sessions` does the same unless `--evidence-only`. `next-stage` is offline over existing run dirs.

### Score Pi sessions (issue-tracker)

Pass the sessions directory at runtime — never commit raw transcripts or absolute home paths:

```bash
export WIKISKILL_SESSIONS_DIR="$HOME/.pi/agent/sessions/<project-key>/"
uv run eval score-sessions --skill issue-tracker --out eval/.runs/
# or:
uv run eval score-sessions --sessions-dir "$WIKISKILL_SESSIONS_DIR" --evidence-only
uv run eval score-sessions --skill to-spec --out eval/.runs/to-spec-v0.1.0
uv run eval next-stage --runs-dir eval/.runs/to-spec-v0.1.0 \
  --out docs/evaluations/to-spec-next-stage.md --baseline-version 0.1.0 --recommended-version 0.2.0
```

Outputs (gitignored under `eval/.runs/`):

- `evidence/<run_id>.json` — `RunEvidence`
- `evaluations/<run_id>.json` — `EvaluationRecord` (unless `--evidence-only`)
- `manifest.json` — counts and run ids (no sessions path)

Next-stage briefs (committed under `docs/evaluations/`) summarize behavioral gaps and propose the next skill version.

## Tooling (types + Zod-like schemas + format/lint)

| Tool | Role |
|---|---|
| **Pydantic v2** (`StrictModel`) | Zod-like runtime schemas (`extra=forbid`, `strict`, field bounds) |
| **pydantic-settings** | Typed `EvalConfig` / `MlxEmbSettings` from env |
| **basedpyright** | Static type checker (`typeCheckingMode = strict`) |
| **Ruff** | Formatter + linter |

```bash
uv run ruff format src
uv run ruff check src --fix
uv run basedpyright
```

## API

```python
from clm import CLMClient, Choice, Noul, Score

client = CLMClient()  # http://127.0.0.1:8700
r = client.system_one(
    state="Customer: my invoice was charged twice and nobody answers the phone!",
    questions={
        "urgency": Noul(instructions="Is this urgent?"),
        "department": Choice(
            instructions="Which team should handle this?",
            criteria={
                "billing": "Charges, invoices, refunds",
                "technical": "Bugs and outages",
            },
        ),
        "frustration": Score(
            instructions="How frustrated is the customer?",
            criteria=["Calm", "Frustrated", "Very angry"],
        ),
    },
)
print(r.answers["department"].choice)
print(r.answers["department"].probabilities)
```

Skill-run evaluation (persistable record — see `docs/evaluation-notes.md`):

```python
from wikiskill_eval import Evaluator, RunEvidence, SkillRef

evaluator = Evaluator()
record = evaluator.evaluate(
    RunEvidence(
        run_id="run-1",
        task="…",
        skill=SkillRef(name="my-skill", version="1.0.0"),
        actions_excerpt="…",
        observed_outcome="…",
        omitted_note="full transcript kept elsewhere",
        max_chars=8000,
    )
)
# record.scores.outcome / skill_helped / evidence_quality
```

Batch: `evaluator.evaluate_many([...])`. Extend `wikiskill_eval.pipeline.Evaluator` for storage and version aggregation.

## MLX encoder (Apple Silicon)

CLM heads expect OpenAI-compatible `POST /v1/embeddings` for Qwen3-8B last-token pooling (4096-d).

```python
from wikiskill_eval.mlx_emb.server import MlxEmbSettings, run

run(MlxEmbSettings(repo="mlx-community/Qwen3-8B-4bit", port=8090))
```

Point `clm-serve` at that URL (`--emb-url http://127.0.0.1:8090/v1/embeddings --emb-model qwen3-8b --device mps`).
Quantized MLX ≠ CUDA fp16; treat scores as experimental.

## Package map

| Module | Role |
|---|---|
| `types` | `RunEvidence`, `EvaluationRecord`, rubric result models |
| `rubric` | Fixed CLM `Noul` / `Choice` / `Score` questions |
| `client` | `EvalClient` over `clm.CLMClient` |
| `pipeline` | `Evaluator` — grow the full pipeline here |
| `ingest.pi` | Pi agent session JSONL loader |
| `excerpt` | Build actions/outcome excerpts for CLM |
| `tasks.issue_tracker` | In-scope filter + `RunEvidence` for issue-tracker |
| `tasks.to_spec` | In-scope filter + `RunEvidence` for to-spec |
| `score_sessions` | Batch score sessions → gitignored `.runs/` |
| `next_stage` | Aggregate scored runs → next skill-stage brief |
| `mlx_emb.server` | FastAPI embeddings app for Mac |
