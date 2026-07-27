# SEFOP - Python Starter

**Reference implementation of [SEFOP](https://github.com/sefop) for Python in a simplified manner**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue)](https://www.python.org/)
[![CI — Unit Tests](https://github.com/sefop/sefop-python/actions/workflows/ci-unit-tests.yml/badge.svg)](https://github.com/sefop/sefop-python/actions/workflows/ci-unit-tests.yml)
[![CI — Integration Tests](https://github.com/sefop/sefop-python/actions/workflows/ci-integration-tests.yml/badge.svg)](https://github.com/sefop/sefop-python/actions/workflows/ci-integration-tests.yml)

---

## Problem description

This repo solves a knapsack problem. Given a **budget** and a **weight limit**, pick the combination of products that **maximizes total calories**.

### Mathematical formulation

**Sets**
- $I$: set of candidate products, indexed by $i \in I$

**Parameters**
- $\text{price}_i$, $\text{weight}_i$, $\text{calories}_i$: unit price (USD), unit weight (kg), and nutritional value of product $i \in I$
- $B$: budget, in USD (`max_budget_usd`)
- $W$: weight limit, in kg (`max_weight_kg`)

**Decision variable**
- $x_i \in \mathbb{Z}_{\ge 0}$ for each $i \in I$: number of units of product $i$ selected

**Objective** — maximize total calories:

$$\max \sum_{i \in I} \text{calories}_i \cdot x_i$$

**Constraints**

$$\sum_{i \in I} \text{price}_i \cdot x_i \le B \qquad \text{(budget)}$$

$$\sum_{i \in I} \text{weight}_i \cdot x_i \le W \qquad \text{(weight limit)}$$

$$x_i \in \mathbb{Z} {\ge 0} \quad \forall i \in I \qquad \text{(non-negativity and integrality)}$$

Because $x_i$ has no upper bound, this is an **unbounded knapsack problem**: any number of units of a product may be chosen, which is why integrality must be enforced explicitly rather than relying on a 0/1 selection variable.

### Example — Data from [`data/2/data.json`](data/2/data.json)

| Product   | Price  | Weight  | Calories |
|-----------|--------|---------|----------|
| Apple     | $1.00  | 0.50 kg | 100      |
| Chocolate | $5.00  | 1.00 kg | 50       |

**Constraints:** budget $10.00 and weight limit 2.00 kg

**Optimal solution:**

| Product   | Units | Cost   | Weight  | Calories |
|-----------|-------|--------|---------|----------|
| Apple     | 4     | $4.00  | 2.00 kg | 400      |
| Chocolate | 0     | $0.00  | 0.00 kg | 0        |

| Total calories | Total cost / Budget | Total weight / Max weight |
|-----------------|----------------------|----------------------------|
| 400             | $4.00 / $10.00       | 2.00 kg / 2.00 kg          |

The solver picks 4 apples — chocolate costs 10× more per calorie, so it never appears in the optimal solution.

---

## Repository structure

This project follows a simplified **[Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)**: three layers
(`domain/`, `use_cases/`, `adapters/`), full manual [Dependency Injection](https://www.geeksforgeeks.org/system-design/dependency-injectiondi-design-pattern/), and
a single composition root (`startup.py`) that wires everything together.

At the top level, the repo has three folders:

```
src/
tests/
data/
```

### `src/`

`src/`'s immediate contents are:

```
src/
├── cli.py          # argparse subparsers + dispatch only — no wiring
├── startup.py       # config (Settings) + composition root — the only place
│                     # concrete adapters and use cases get constructed
├── domain/          # pure entities — Product, Request, Recommendation
├── use_cases/       # application rules (see below)
└── adapters/        # I/O implementations (see below)
```

**`use_cases/`** in more detail:

```
use_cases/
├── ports/                          # abstract interfaces (ABCs) the use cases depend on
│   ├── base_data_loader.py
│   ├── base_result_writer.py       # also defines TIMESTAMP_FORMAT
│   ├── base_request_discovery.py
│   └── base_solution_loader.py
├── optimization_response.py        # result of the two "solve" use cases
├── evaluation_response.py          # result of the "evaluate" use case
├── use_case_solve_single_request.py         # solve one request
├── use_case_solve_multiple_requests.py      # solve every request in a folder
├── use_case_evaluate_solution_for_request.py # feasibility-check a candidate solution
└── solving/                        # internal implementation detail of the
    │                                # solve use cases — not a top-level layer
    ├── orchestrator.py             # pipeline coordinator: pre → provider → post
    ├── preprocessing/              # filter infeasible products before solving
    ├── postprocessing/             # sort and refine the recommendation
    └── optimization/               # SolutionProvider + 4 implementations:
                                     # enumeration (brute force), MIP (HiGHS),
                                     # MIP (Google MathOpt/SCIP), heuristic
```

**`adapters/`** in more detail:

```
adapters/
├── json_data_loader.py
├── csv_result_writer.py
├── json_result_writer.py
├── directory_request_discovery.py
└── json_solution_loader.py
```

Dependencies only point inward: `adapters/` imports from `use_cases/`, never the
reverse; `use_cases/solving/` internals (`SolutionProvider` and its three
implementations) are separate from the public ports in `use_cases/ports/` —
they are pluggable providers used only within the solving pipeline itself,
not something `adapters/` or `startup.py` implement directly (`startup.py`
only decides *which* MIP technology's `SolutionProvider` to construct).

### `tests/`

Mirrors `src/`'s structure — see the [Testing](#testing) section below.

### `data/`

Sample problem instances (input JSON), used as `python -m cli solve <n>` where `<n>` is a `data/` subfolder.

---

## Installation

### 1. Clone the repository
```bash
git clone https://github.com/sefop/sefop-python-starter.git
cd sefop-python-starter
```

### 2. Create a virtual environment using Python 3.12
```bash
py -3.12 -m venv .venv
.venv\Scripts\activate  # On Windows
# source .venv/bin/activate  # On macOS/Linux
```

### 3. Install dependencies and the package
```bash
pip install -r requirements.txt
pip install -e .
```

The `-e` flag installs the package in **editable mode**, making your source code directly importable. This is the standard Python development practice — no need to set `PYTHONPATH` or reinstall when you edit code.

**What breaks if you skip this step?** `pytest` still works, since `pyproject.toml` adds `src` to the path just for pytest. But `python -m cli solve 1` will fail with an import error — `cli.py` imports `domain`, `use_cases`, etc. as top-level packages, and without the editable install Python has no way to find them under `src/` outside of pytest.

---

## Testing

### Run all tests
```bash
pytest
```

### Run unit tests only
```bash
pytest -m "not integration"
```

### Run integration tests only
```bash
pytest -m integration
```
Each integration test drives the real CLI end-to-end against a pre-built "situation" (`tests/resources/<situation>/`) and checks situation-specific conditions on the observable outcome only — e.g. the expected optimal calories, that an infeasible request exits non-zero and writes no solution, that tied optimal solutions still report the shared optimal total, or that a large instance correctly routes to the heuristic instead of the exact solvers. Formulation correctness (is the MIP model built right?) is checked separately and only at the unit level, by comparing `MipHighsSolutionProvider`'s output against `EnumerationSolutionProvider`'s brute-force ground truth — see `tests/use_cases/solving/optimization/test_providers_agree_with_enumeration.py` — not by diffing a generated `model.lp` against a golden file.


---

## Code quality

CI runs two checks before the test suite; both are fast, so run them locally before pushing to avoid a red PR.

### Format check (black)
```bash
black --check src tests   # verify formatting only, no changes written
black src tests           # reformat in place
```
Configuration (line length, target Python version) lives in `pyproject.toml`'s `[tool.black]` section, so the local command and CI always agree.

### Type check (mypy)
```bash
mypy
```
Configuration lives in `pyproject.toml`'s `[tool.mypy]` section.

---

## Usage

### Solve a single knapsack optimization request
```bash
python -m cli solve 1  # solve request from data/1/data.json
python -m cli solve 2  # solve request from data/2/data.json
python -m cli solve 1 --format json  # write the result as JSON instead of CSV
```

### Solve every request in a folder
```bash
python -m cli solve-batch data  # solve every request subfolder under data/
```

### Check whether a candidate solution is feasible for a request
```bash
python -m cli evaluate 1 candidate_solution.json
```
where `candidate_solution.json` maps product name to candidate quantity:
```json
{ "apple": 4, "chocolate": 0 }
```

---

## How it works

This project follows a simplified **Clean Architecture** with three layers and
full dependency inversion — every collaborator is constructor-injected, and
`startup.py` is the single place concrete objects get wired together:

1. **`domain/`** — Pure business logic (Product, Request, Recommendation) with no external dependencies.
2. **`use_cases/`** — Application rules, expressed as three independent use case classes (no shared base — their signatures genuinely differ):
   - **`SolveSingleRequest`** — load one request and run it through the solving pipeline.
   - **`SolveMultipleRequests`** — discover every request in a folder (via `BaseRequestDiscovery`) and solve each one with a composed `SolveSingleRequest`.
   - **`EvaluateSolutionForRequest`** — check whether a user-supplied candidate quantity dict is feasible for a request, with no solver involved: it builds a `Recommendation` and lets its existing budget/weight validation do the feasibility check.

   Abstract ports the use cases depend on (`BaseDataLoader`, `BaseResultWriter`, `BaseRequestDiscovery`, `BaseSolutionLoader`) live in `use_cases/ports/`.

   The solving pipeline itself lives in **`use_cases/solving/`** — an internal implementation detail of `SolveSingleRequest`, not a top-level architecture layer:
   - **`solving/orchestrator.py`** — Pipeline coordinator: runs preprocessing → picks a `SolutionProvider` → runs postprocessing. Picks based on problem size: a small enough combinatorial search space routes to brute-force enumeration; otherwise a small enough product count routes to the exact MIP solver; anything larger falls back to the fast heuristic.
   - **`solving/preprocessing/`** — Filters out products that can never be selected (individually infeasible).
   - **`solving/optimization/`** — `SolutionProvider` (the shared ABC: `solve(data, output_dir) -> Recommendation | None`) and four implementations:
     - **`enumeration/enumeration_solution_provider.py`** — Brute-force exact solver: tries every feasible product-quantity combination and keeps the best. Used both as a real, fast solving path for small requests and as the ground-truth oracle other providers' tests are checked against.
     - **`mip_highs/mip_highs_solution_provider.py`** — Exact MIP solver, `MipHighsSolutionProvider`. Builds variables/constraints/objective directly against `highspy` and solves — no intermediate solver-agnostic model. This is deliberately self-contained per solver technology (rather than sharing a formulation layer across technologies) so each solver technology can be added as its own independent `SolutionProvider` implementation without touching the others.
     - **`mip_google/mip_google_scip_solution_provider.py`** — A second exact MIP solver, `MipGoogleScipSolutionProvider`, built against Google OR-Tools' [MathOpt](https://developers.google.com/optimization/math_opt) API configured for the GSCIP (SCIP) backend. Same formulation as `MipHighsSolutionProvider`, expressed with MathOpt's expression-based model-building API instead of HiGHS's index/matrix-based one. MathOpt's Python API has no LP/MPS exporter, so its `output_dir` debug artifact is `model.pbtxt` (the model dumped as protobuf text) rather than `model.lp`.
     - **`heuristic/heuristic_solution_provider.py`** — Fast, approximate greedy solution for large problems.

     `SolutionProvider` is an internal solving-pipeline contract, separate from the public ports in `use_cases/ports/` — `startup.py` decides which concrete `SolutionProvider` to use for the MIP slot (via `Settings.solver_name`), but `Orchestrator` itself only ever depends on the abstract type.
   - **`solving/postprocessing/`** — Refines the recommendation (e.g., sorts products by quantity).
3. **`adapters/`** — All I/O: concrete implementations of the `use_cases/ports/` interfaces (`JsonDataLoader`, `CsvResultWriter`/`JsonResultWriter`, `DirectoryRequestDiscovery`, `JsonSolutionLoader`).
4. **`startup.py`** — Configuration (`Settings`) plus the composition root: factory functions that assemble the full object graph, including resolving `Settings.solver_name` to a concrete solver.
5. **`cli.py`** — Parses arguments and dispatches to `startup.py`; it never constructs a concrete adapter or use case itself.

---
