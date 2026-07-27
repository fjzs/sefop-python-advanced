---
name: find-inconsistencies
description: Audit a repo for inconsistencies — stale docs, naming drift, structural asymmetry, test drift — and produce a tiered report, then grill the user on what to fix. Use when the user wants an inconsistency/consistency audit, asks to find contradictions or drift in a codebase, or wants confusing docs/code mismatches surfaced.
---

- Investigate in parallel (spawn research/Explore-type agents, not manual reads, unless the repo is tiny) across three angles: docs-vs-code contradictions (READMEs, 
convention docs, docstrings describing behavior the code no longer has), code structure/naming/style drift (parallel implementations that should look alike but don't, 
inconsistent error handling, inconsistent type hints), and test-suite drift (test/src mirroring, naming conventions, stale imports, mislabeled test types).
Do not fix anything during this pass.

- Verify any surprising or checkable claim (e.g. git history, a file's existence) against the real repo state before reporting it as fact.

- Compile one tiered report: highest-confusion findings first (doc actively contradicts code), then structural drift, then cosmetic. Each finding: file path(s), 
one-line summary, why it's confusing. No filler.

- Print the report to the user as plain text, not a file. Then run a `/grill-me` session, feeding it the report, scoped to deciding per finding: fix, defer, or leave — 
and for anything to fix, the exact resulting convention.

- Stop after the grill-me session. Do not implement fixes unless the user explicitly asks afterward.
