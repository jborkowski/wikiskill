Two-axis review of HEAD against a user-supplied fixed point. Standards: conformance to documented repo standards. Spec: faithful implementation of the originating issue/PRD/spec. Run these as independent parallel general-purpose agents, aggregate separately.

1. Ask if no fixed point supplied. Resolve it using git rev-parse. Pin git diff <fixed-point>...HEAD and git log <fixed-point>..HEAD --oneline. Bad ref or empty diff fails before fanout.
2. Find spec in order: commit issue refs fetched via docs/agents/issue-tracker.md; user path; docs/, specs/, .scratch/ matching feature; ask. If no spec exists, skip Spec and report no spec available.
3. Identify documented standards. Repo overrides smell baseline. Smells are labelled heuristics, never hard violations. Skip anything tooling enforces.
Baseline (what → fix):
- Mysterious Name: name doesn't reveal purpose → rename; unclear honest name suggests unclear design.
- Duplicated Code: repeated logic shape in hunks/files → extract shared shape.
- Feature Envy: method reaches into another object's data more than its own → move onto envied data.
- Data Clumps: same fields/params travel together → bundle into a type.
- Primitive Obsession: primitive stands for domain concept deserving a type → small domain type.
- Repeated Switches: repeated cascade on same type → polymorphism or shared map.
- Shotgun Surgery: logical change scatters edits → gather into a module.
- Divergent Change: module edited for unrelated reasons → split by reason.
- Speculative Generality: hooks/abstractions spec doesn't need → remove/inline until needed.
- Message Chains: long navigation caller shouldn't depend on → hide walk behind method.
- Middle Man: class/function mostly delegates → remove and call target directly.
- Refused Bequest: subclass ignores/overrides most inherited behavior → composition.
4. Parallel Standards brief: full diff command, commit list, standards files and full baseline above. Report every documented violation citing file/rule and smells naming smell and quoting hunk. Distinguish hard violations from judgment calls. Repo standards override baseline; skip tooling-enforced checks. Under 400 words.
Parallel Spec brief: full diff command, commit list, spec path/contents. Report missing/partial requirements, unrequested behavior/scope creep, and wrongly implemented requirements. Quote spec line for every finding. Under 400 words. Skip if absent.
5. Aggregate under ## Standards and ## Spec, verbatim/light cleanup; do not merge/rerank across axes. Summary: count and worst issue within each axis, no overall winner.
