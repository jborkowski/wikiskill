# Rough skill evaluation with CLM

User preference: explore `Contrastive-LM/CLM-v0.1-8B` as a rough evaluator for skill runs. This is a proposed integration, not an implemented or validated evaluator.

## Verified model behavior

The [model card](https://huggingface.co/Contrastive-LM/CLM-v0.1-8B) describes candidate ranking and typed classification/scoring using a frozen Qwen3-8B encoder with learned projection heads. It generates no explanations; probabilities depend on the candidate set. The advertised agentic verifier results require fine-tuned heads and do not establish zero-shot skill-evaluation accuracy. The documented deployment runs an embedding server and `clm-serve`, which offers a local API.

## Suggested use in this repository

Evaluate evidence from a run: task, relevant skill version, actions/tool results, and observed outcome. Rating skill text alone would measure a different thing from whether using it helped complete a task.

Start with a fixed rubric and fixed candidate labels such as `succeeded`, `partially succeeded`, `failed`, and `insufficient evidence`. Treat these as experimental judgments to check against human labels and objective task checks. A successful run alone does not prove the skill caused success; compare old/new versions or a no-skill baseline on the same tasks when assessing improvement.

Keep storage and orchestration separate from the model process. The first implementation lives in Python under `eval/`: typed `CLMClient` usage, a fixed skill-run rubric, and (on Apple Silicon) an MLX Qwen3-8B last-token embeddings server in place of vLLM. Preserve each evaluation's run ID, exact skill versions, evaluator model/checkpoint, rubric version, full candidate set, exact input or its stored reference, preprocessing/truncation settings, raw returned scores, and human/task-check outcomes. Do not interpret a relative candidate probability as a calibrated probability that a skill is good.

Keep full transcripts even if the evaluator uses selected excerpts. Explicitly record omitted content and check the serving context limit before scoring long runs. Aggregate evaluations across comparable tasks to compare versions; leave activation decisions reviewable until the evaluator has been checked against labeled examples.

## Relationship to WikiSkill

[The paper summary](paper-summary.md) explains the separation between raw traces, accumulated lessons, and versioned skills. CLM would be an additional evaluation signal in that lifecycle. It does not replace the persistent lesson store or independently establish that a proposed skill update improves task performance.
