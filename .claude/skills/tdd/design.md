# Design for Testability

Good design makes testing natural. This document covers two complementary principles:
interface design that enables straightforward tests, and deep modules that hide complexity
behind simple surfaces.

---

## Interface Design

### 1. Accept dependencies, don't create them

```python
# Testable — dependency is injected
class OptimizationService:
    def __init__(self, data_loader: BaseDataLoader, engine: Engine) -> None:
        self._data_loader = data_loader
        self._engine = engine

# Hard to test — dependency is created internally
class OptimizationService:
    def __init__(self) -> None:
        self._data_loader = FileRequestAdapter()
        self._engine = Engine()
```

### 2. Return results, don't produce side effects

```python
# Testable — returns a value you can assert on
def calculate_total_weight(cargo_requests: list[CargoRequest]) -> float:
    return sum(cr.weight_kg for cr in cargo_requests)

# Hard to test — mutates external state
def update_total_weight(aircraft: Aircraft, cargo_requests: list[CargoRequest]) -> None:
    aircraft.current_weight = sum(cr.weight_kg for cr in cargo_requests)
```

### 3. Small surface area

- Fewer methods = fewer tests needed
- Fewer parameters = simpler test setup
- One responsibility per class = one reason to change

---

## Deep Modules

From *A Philosophy of Software Design* (John Ousterhout):

**Deep module** = small interface + lots of implementation

```
┌─────────────────────┐
│   Small Interface   │  ← Few methods, simple params
├─────────────────────┤
│                     │
│                     │
│  Deep Implementation│  ← Complex logic hidden
│                     │
│                     │
└─────────────────────┘
```

**Shallow module** = large interface + little implementation (avoid)

```
┌─────────────────────────────────┐
│       Large Interface           │  ← Many methods, complex params
├─────────────────────────────────┤
│  Thin Implementation            │  ← Just passes through
└─────────────────────────────────┘
```

### Example in this project

The `Engine` class is a deep module: callers invoke a single `solve(request)` method, but
internally it selects a solver strategy, validates guards, and orchestrates preprocessing,
optimization, and postprocessing.

```python
# Deep: simple interface hides complex orchestration
class Engine:
    def solve(self, request: Request) -> Recommendation:
        ...  # strategy selection, guard validation, pipeline execution
```

### When designing, ask

- Can I reduce the number of methods?
- Can I simplify the parameters?
- Can I hide more complexity inside?
- Would a caller need to understand internals to use this correctly? (If yes, redesign.)
