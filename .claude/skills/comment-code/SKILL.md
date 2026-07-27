---
name: comment-code
description: Commenting code conventions for this project. Use when writing or reviewing any Python code in this repo.
---

# Commenting Code Guide

Comments explain **why**, not what. If a comment restates the name of the thing it's attached to, delete it.

## Rules

1. **Why, not what.** Explain the reasoning, constraint, or rejected alternative — not what the code visibly does.
2. **Abstraction vs. implementation — never mix them.** Docstrings (module/class/function signatures) document the *interface*: the contract a caller relies on — responsibility, inputs, outputs, constraints. Inline comments (function bodies) document the *implementation*: why the body does what it does internally. A docstring that leaks internal logic, or an inline comment that repeats the contract, is misplaced — move it to the right layer instead of writing it twice.
3. **Proximity.** Comment on the line above (or same line) as the code it describes. Never separated by blank lines.
4. **Keep in sync.** Update or remove a comment in the same commit that changes the logic it describes. Stale > absent is false — delete stale comments.
5. **No commented-out code.** Delete it; git history remembers.
6. **No redundant comments.** If the comment says exactly what the code/name already says, remove it.
7. **`TODO:`/`FIXME:`** with a one-line explanation of what's incomplete or broken.
8. **Prefer self-documenting code first.** Before commenting, try a better name, an extracted function, or a type hint — comment only what naming can't express.

```python
# Bad: restates the code / name
total = price * quantity  # multiply price by quantity
def get_total_price(items): """Gets the total price."""

# Good: adds non-obvious info
total = price * quantity  # gross total before tax; tax applied at checkout
```

## Docstrings — the interface layer (rule 2)

- **Module** (public API / significant module): first statement in the file. State the module's responsibility and how it fits the system, in 1-2 sentences. No author/date/version.
- **Class**: strategic overview only — responsibility, role in the design, non-obvious constraints. Use `Attributes:` for public fields. If overriding a base class, state only what *this* implementation adds — don't repeat the base contract.
- **Function/method**: document the contract — `Args:`, `Returns:`, `Raises:` (Google style). Required for public functions; optional for private (`_`-prefixed) helpers with clear names/types.
- **Type hints** are documentation: annotate every parameter and return type, use `X | Y` (not `Optional`/`Union`). They cover *type*; docstrings cover *behavior and preconditions* — use both, don't duplicate.

## Inline comments — the implementation layer (rule 2)

Use them only for what the docstring's contract doesn't cover: units, boundary conditions (inclusive/exclusive), or why a seemingly-wrong choice is correct internally. One line above the code, or short end-of-line.

## Constants

Document unit, valid range, and the business rule encoded, directly above the constant. `UPPER_CASE` names. Dataclass fields go in the class docstring's `Attributes:`, not individual inline comments.

```python
# Maximum look-ahead window in hours; events beyond this horizon are excluded.
# Source: config property "look_ahead_threshold_hours".
LOOK_AHEAD_THRESHOLD_HOURS = 72
```

## SEFOP templates: teach the pattern

SEFOP template code must be readable by a data scientist who knows optimization but not software engineering. This adds one obligation on top of the rules above: **name and explain the software engineering pattern**, not just the code's job.

- **Module docstring** states its `ROLE:` from the table below, `WHY THIS EXISTS`, and where sibling implementations live.

  | Role | Directory | Purpose |
  |------|-----------|---------|
  | `Entity` | `src/domain/` | Pure data model, no dependencies, no solver imports. |
  | `Value Object` | `src/domain/`, `src/use_cases/` (response DTOs) | Immutable, self-validating descriptor of a quantity/concept, or of a use case's outcome. |
  | `Abstract Base Class` | `src/use_cases/ports/`, `src/use_cases/solving/optimization/solution_provider.py` | Abstract interface that use cases or the solving pipeline depend on. |
  | `Orchestrator` | `src/use_cases/solving/orchestrator.py` | Sequences one user-facing operation end-to-end, no business logic of its own. |
  | `Implementation` | `src/adapters/`, `src/use_cases/solving/optimization/<technology>/` | Concrete implementation of a port or a `SolutionProvider`, for one specific technology. |

- **Class docstrings** for ABC / Dependency Injection / frozen dataclass: one short paragraph naming and explaining the pattern (e.g., "this is a contract pattern — like a power socket shape"), then one paragraph on what *this* class does with it. State each pattern once per file; don't re-explain it in every method.
- **Inline comments** explain the engineering choice's consequence (e.g., *why* a solver is injected rather than constructed: "so tests can pass a mock without a real HiGHS install — this is Dependency Injection").
- **Math in the optimization layer**: state the formula in a comment next to the model-building expression so a reader can map math ↔ code.

  ```python
  # Constraint: ∑ price_i · x_i ≤ budget — total cost must not exceed max_budget_usd.
  model.add_linear_constraint(
      sum(product.price_usd * variables[name] for product, name in ...) <= request.max_budget_usd,
      name="budget_limit",
  )
  ```

- **Don't over-explain**: no comments on well-named code, no Python-syntax explanations, no re-deriving the architecture in every file. Test: would a reader who just finished a Python tutorial need this? If only someone who's never seen a for-loop would, skip it.