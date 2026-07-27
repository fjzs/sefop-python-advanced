# CLAUDE.md

---

## Project overview

- Python starter reference implementation of the [SEFOP framework](https://github.com/fjzs/sefop) — a framework that brings software engineering techniques to 
  decision-support software.
- Use simply language and comment the code relentlessly according to .claude/skills/comment-code/SKILL.md so any data scientist without knowledge in software engineering 
  can understand this repository.
- The project should be designed in such a way that it is easy to fork and reuse.

## Coding rules

- Never compare floats with `==` or `!=`; use `math.isclose()` instead.
- All code must comply with `black` (formatting) and `mypy` (static type checking); run `black src tests` and `mypy` before considering any change done. Configuration for both lives in `pyproject.toml`.
