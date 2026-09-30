# Standards-axis smell baseline

These Fowler-style smells are heuristics, not violations. A documented repo rule overrides them. Skip conventions enforced by tooling. Report only as **possible <smell>** with diff evidence, concrete maintenance cost, and a proportionate remedy. Absence of smells is a valid result; the suggested remedy is not automatically the right design.

| Smell | What to look for | Possible remedy |
| --- | --- | --- |
| Mysterious Name | Name hides purpose or content | Rename; if no honest name fits, clarify the design |
| Duplicated Code | Same logic shape repeated across changed hunks/files | Extract a genuinely shared shape |
| Feature Envy | Method depends on another object's data more than its own | Move behavior to that data's owner |
| Data Clumps | Same fields or parameters repeatedly travel together | Bundle a cohesive concept into a type |
| Primitive Obsession | Primitive obscures a domain concept and its invariants | Introduce a small domain type where justified |
| Repeated Switches | Same type-dependent dispatch repeated across changed code | Share a dispatch map or use polymorphism |
| Shotgun Surgery | One logical change requires scattered edits | Gather code that changes together |
| Divergent Change | One module changes for unrelated reasons | Split by cohesive responsibility |
| Speculative Generality | Hooks or abstractions serve no demonstrated requirement | Remove or inline unused generality |
| Message Chains | Caller relies on long internal-object navigation | Hide unstable navigation behind a suitable boundary |
| Middle Man | Layer delegates without a useful boundary or policy | Remove needless delegation, preserving meaningful boundaries |
| Refused Bequest | Subclass rejects most inherited behavior/contracts | Prefer composition when it better expresses the relationship |

A primitive at a boundary, two branches, a delegating adapter, or edits across multiple files are not sufficient evidence alone. Consider repository conventions, contract ownership, and actual change pressure before recommending a refactor.
