# WikiSkill paper summary

## Citation

Liyan Tang, Cyrus Rashtchian, Chun-Sung Ferng, Andrew Tomkins, Da-Cheng Juan, and Tu Vu, “WikiSkill: Compiling Agent Experience into Persistent Knowledge for Skill Evolution,” arXiv:2608.27454v1, dated 28 August 2026. The local PDF is `docs/paper.pdf` (28 pages).

## Central thesis

Agent experience becomes more useful when it is organized into a persistent knowledge base between raw execution traces and executable skills. WikiSkill keeps those three things separate: immutable traces preserve evidence, a wiki consolidates reusable patterns and evolution history, and skills encode the active procedures. A failed skill update can be rolled back while the wiki retains what was learned. The authors argue that this cumulative layer makes later skill updates better informed (Abstract; §§1, 3.1–3.2, pp. 1–6).

## Method

The system evolves a skill set over repeated training and validation rounds (§3.2, pp. 4–6; Algorithm 1, p. 19):

1. An inference agent solves training tasks using the currently active skills. Its complete interaction traces are stored as immutable raw records; the inference agent cannot read the wiki during these rollouts.
2. A wiki maintainer reviews a stratified sample of up to eight traces per iteration (up to five failures and three successes; each log capped at 15,000 characters). It creates or incrementally edits short pattern pages, updates an index, and appends an evolution log (§3.2.2, p. 5; Appendix C, p. 21).
3. A skill proposer reads the wiki index, past skill-impact records, and selected patterns and traces, then proposes one atomic skill creation or patch. The proposer uses a ReAct-style tool loop to inspect relevant evidence (§3.2.3, pp. 5–6).
4. The candidate skills are evaluated on a validation set. A proposal is accepted only if it improves the best validation score; otherwise the skill change is rolled back. The wiki is retained either way, and the system records the proposal diff, score, and accepted/rejected result (§3.2.4, p. 6).

The study uses five benchmarks (math, web search, spreadsheet manipulation, long-document QA, and embodied interaction), five models from Qwen, Gemma, and Gemini families, three independent full evolution runs per method, and paired bootstrap significance testing with 1,000 resamples (including macro-average resampling across benchmarks; §§4.1–4.2, pp. 7–8; Appendix C, p. 21). Inference skills are fully injected into prompts to isolate skill quality from skill retrieval or triggering (p. 5).

## Main findings

- **WikiSkill had the highest average test score for each of the five inference models in Table 1** and beat the strongest competing skill-evolution method by 3.3, 5.1, 10.0, 5.8, and 12.0 points, respectively, for Qwen-3.5-4B, Qwen-3.5-9B, Qwen-3.6-27B, Gemma-4-31B, and Gemini-3.5-Flash (§4.2.1, pp. 7–8; Table 1, p. 8). It improved over the no-skill baseline in most model/benchmark pairs, not all.
- **Skill gains grew with model scale within the Qwen family:** average accuracy rose from 26.2% to 38.5% for Qwen-3.5-4B (+12.3 percentage points), 29.9% to 47.4% for Qwen-3.5-9B (+17.5 points), and 39.4% to 63.3% for Qwen-3.6-27B (+23.9 points; Table 1, p. 8). Qwen-3.5-9B with WikiSkill (47.4%) also exceeded Qwen-3.6-27B without skills (39.4%; §4.2.1, p. 9).
- **Skills transferred across model families, sometimes outperforming a model’s own evolved skill.** On ALFWorld, Qwen-3.5-9B scored 70.2% using Qwen-3.6-27B’s skill versus 63.4% with its own; on SpreadsheetBench, the Qwen-3.6-27B skill raised Qwen-3.5-9B from 24.3% without a skill / 33.6% with its own skill to 50.5% (Table 2, p. 10; §4.2.2, pp. 9–10). Transfer could also hurt: Qwen-3.5-4B’s spreadsheet skill lowered Gemini-3.5-Flash from 50.5% to 18.1%, which the authors attribute to small-model-specific workarounds and redundant tool calls (§4.2.2, p. 10).
- **Persistent wiki access mattered in the ablation.** For Gemini-3.5-Flash, with wiki access withheld from the inference agent, giving the skill proposer persistent wiki access raised average performance from 48.7% to 63.7% (+15.0 points). When the proposer had wiki access, also giving the inference agent access during training lowered the average from 63.7% to 60.9% (§5.1, p. 11; Table 3, p. 11). The paper offers the explanation that wiki access can make training traces less informative about what the skill itself contributed.
- **Knowledge continued to accumulate as skills changed.** Across models, the system created an average of 6.3–8.9 wiki patterns; across benchmarks, it created 4.4 patterns for LiveMath and 9.8 for SpreadsheetBench. Accepted skill edits continued after the first rounds: 4–21% of model-group accepted updates happened in iterations 5–7, while benchmark-group late-stage shares ranged from 10% to 28% (SealQA was 28%) (§5.2, pp. 12–13; Tables 4–5, pp. 12, 20).

## Limitations and scope

The evaluation measures task accuracy with active skills injected directly; it does not test skill discovery, routing, or triggering from a growing library (§6, p. 14). Strictly accepting only validation-score improvements can reject neutral changes that might help later (§6, p. 14). The wiki grows without automated pruning, which may become a problem in long runs (§6, p. 14). The benchmarks do not cover tasks lasting hundreds of actions or hours, nor do they test online skill adaptation within one long execution (§6, p. 14). Validation splits are small and can make gating noisy; the authors mitigate this by averaging three independent evolution runs and report paired bootstrap tests (Appendix B, pp. 20–21; Appendix C, p. 21). The benchmark, model, and tool setup is controlled; results do not establish that the same gains will occur in a general-purpose personal skills library.

## Implications for a lightweight Go tool (inferences, not paper claims)

The paper’s most useful design lesson is to preserve evidence separately from its interpretation and from the current skill. A small local tool could represent the lifecycle with five linked records:

- **Skill:** stable name and description.
- **Skill version:** immutable content snapshot, version identifier, creation time, and optional parent version. Mark which version is currently active; rejected candidates remain inspectable.
- **Run:** task/context reference, model and tool/harness metadata, timestamp, and the exact skill version(s) used.
- **Transcript:** append-only interaction record for the run, including user/task input, assistant responses, tool calls/results, and final outcome. Keep this as source evidence; let a human or later agent derive summaries from it.
- **Evaluation:** run/version reference, evaluator or rubric, outcome/score, notes on whether the skill applied and helped, and decision such as accepted/rejected/uncertain. Keep the raw score and narrative judgment distinct.

A simple workflow follows: create a run with a pinned skill version; save its transcript; attach an evaluation; optionally write a concise reusable lesson linked back to the supporting runs; propose a new skill version that cites those lessons; evaluate it; then mark it active or rejected without deleting prior versions or evidence. This borrows WikiSkill’s separation and audit trail, while treating usability details like explicit skill-use ratings, local storage, and the five-record schema as recommendations for the user’s tool. The paper’s score-gated acceptance rule is one option, but a personal tool should preserve “uncertain” and neutral evaluations rather than assuming every useful change must immediately improve a benchmark score.
