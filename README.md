# SEFOP - Python Advanced: Decision-Support System as a Web Application

**Reference implementation of [SEFOP](https://github.com/sefop) for Python in a simplified manner**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue)](https://www.python.org/)
[![CI — Unit Tests](https://github.com/sefop/sefop-python/actions/workflows/ci-unit-tests.yml/badge.svg)](https://github.com/sefop/sefop-python/actions/workflows/ci-unit-tests.yml)
[![CI — Integration Tests](https://github.com/sefop/sefop-python/actions/workflows/ci-integration-tests.yml/badge.svg)](https://github.com/sefop/sefop-python/actions/workflows/ci-integration-tests.yml)
[![CI — Docker Build](https://github.com/sefop/sefop-python/actions/workflows/ci-docker-build.yml/badge.svg)](https://github.com/sefop/sefop-python/actions/workflows/ci-docker-build.yml)

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

This project follows **[Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)**'s four canonical rings —
Entities (`domain/`), Use Cases (`use_cases/`), Interface Adapters (`adapters/`), and Frameworks & Drivers
(`frameworks_and_drivers/`) — with full manual [Dependency Injection](https://www.geeksforgeeks.org/system-design/dependency-injectiondi-design-pattern/), and
a single composition root (`startup.py`) that wires everything together. Two independent delivery mechanisms
sit in the outermost ring: a CLI and a web app (FastAPI backend + a minimal static frontend), both calling
into the same `use_cases/` and `startup.py` underneath.

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
├── startup.py                # config (Settings/WebSettings) + composition root — the
│                              # only place concrete adapters and use cases get constructed
├── domain/                    # pure entities — Product, Request, Recommendation
├── use_cases/                 # application rules (see below)
├── adapters/                  # I/O implementations (see below), including adapters/web/
└── frameworks_and_drivers/    # delivery mechanisms (see below): cli.py and web/
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
├── json_solution_loader.py
└── web/                       # adapters specific to the web delivery mechanism
    ├── in_memory_data_loader.py    # BaseDataLoader backed by memory, not a file —
    │                                # the HTTP request body already *is* the data
    ├── controller.py               # raw payload -> domain Request -> use case call
    └── presenter.py                # OptimizationResponse -> plain response data
```

Dependencies only point inward: `adapters/` imports from `use_cases/`, never the
reverse; `use_cases/solving/` internals (`SolutionProvider` and its three
implementations) are separate from the public ports in `use_cases/ports/` —
they are pluggable providers used only within the solving pipeline itself,
not something `adapters/` or `startup.py` implement directly (`startup.py`
only decides *which* MIP technology's `SolutionProvider` to construct).

**`frameworks_and_drivers/`** in more detail:

```
frameworks_and_drivers/
├── cli.py                     # argparse subparsers + dispatch only — no wiring
└── web/
    ├── main.py                # the FastAPI app instance (what Uvicorn points at)
    ├── routes.py               # POST /solve, GET /health — thin, no domain/use_cases imports
    ├── schemas.py               # Pydantic request/response models (input validation, OpenAPI docs)
    └── static/                  # the minimal frontend: index.html, style.css, app.js
```

This is the outermost ring: it's the only place that knows about argparse, FastAPI,
or Pydantic. Both delivery mechanisms are thin — they parse input, call into
`startup.py` to assemble what they need, and dispatch. Neither constructs a
concrete adapter or use case itself.

### `tests/`

Mirrors `src/`'s structure — see the [Testing](#testing) section below.

### `data/`

Sample problem instances (input JSON), used as `python -m frameworks_and_drivers.cli solve <n>` where `<n>` is a `data/` subfolder.

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

**What breaks if you skip this step?** `pytest` still works, since `pyproject.toml` adds `src` to the path just for pytest. But `python -m frameworks_and_drivers.cli solve 1` will fail with an import error — `cli.py` imports `domain`, `use_cases`, etc. as top-level packages, and without the editable install Python has no way to find them under `src/` outside of pytest.

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

The web app has its own integration tests, `tests/frameworks_and_drivers/web/test_routes.py`, driving the real HTTP surface end-to-end via FastAPI's `TestClient` — no browser, no real network socket, but the same in-process request handling FastAPI uses in production. `tests/adapters/web/` covers the controller, presenter, and in-memory data loader as fast, non-integration unit tests.


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

## Usage — CLI

### Solve a single knapsack optimization request
```bash
python -m frameworks_and_drivers.cli solve 1  # solve request from data/1/data.json
python -m frameworks_and_drivers.cli solve 2  # solve request from data/2/data.json
python -m frameworks_and_drivers.cli solve 1 --format json  # write the result as JSON instead of CSV
```

### Solve every request in a folder
```bash
python -m frameworks_and_drivers.cli solve-batch data  # solve every request subfolder under data/
```

### Check whether a candidate solution is feasible for a request
```bash
python -m frameworks_and_drivers.cli evaluate 1 candidate_solution.json
```
where `candidate_solution.json` maps product name to candidate quantity:
```json
{ "apple": 4, "chocolate": 0 }
```

---

## Usage — Web app

The web app exposes the same `SolveSingleRequest` use case the CLI's `solve` command
uses, behind a single `POST /solve` endpoint and a minimal static frontend — a form to
configure a request (budget, weight limit, and a product table you can add/remove rows
to) and a Solve button. `solve-batch` and `evaluate` aren't exposed over HTTP; use the
CLI for those.

### Run locally
```bash
uvicorn frameworks_and_drivers.web.main:app --reload
```
Then open `http://localhost:8000` in a browser. `GET /health` is a plain liveness check;
`POST /solve` accepts a JSON body shaped like:
```json
{
  "maxWeightKg": 2.0,
  "maxBudgetUsd": 10.0,
  "products": [
    { "name": "Apple", "priceUsd": 1.00, "weightKg": 0.50, "calories": 100 }
  ]
}
```
and returns `{"status": "SUCCESS" | "FAILURE", "message": ..., "recommendation": ...}` —
malformed input (e.g. a negative budget) gets FastAPI's standard `422` response;
input that's well-formed but violates a domain rule (e.g. duplicate product names)
comes back as a normal `200` with `status: "FAILURE"`, the same shape an unsolvable
request already uses. The solver technology can be picked with the `SOLVER_NAME`
environment variable (`highs` or `google_scip`, same options as the CLI's `Settings.solver_name`;
defaults to `google_scip`).

### Run via Docker
```bash
docker build -t sefop-web .
docker run -p 8000:8000 sefop-web
```
Then open `http://localhost:8000` the same way. `Dockerfile` is a single-stage build on
`python:3.12-slim`; see its comments for why (no multi-stage split, single Uvicorn
process, no Gunicorn).

---

## How it works

This project follows **Clean Architecture**'s four rings with full dependency
inversion — every collaborator is constructor-injected, and `startup.py` is
the single place concrete objects get wired together:

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
3. **`adapters/`** — All I/O: concrete implementations of the `use_cases/ports/` interfaces (`JsonDataLoader`, `CsvResultWriter`/`JsonResultWriter`, `DirectoryRequestDiscovery`, `JsonSolutionLoader`), plus `adapters/web/` for the web delivery mechanism:
   - **`web/in_memory_data_loader.py`** — `BaseDataLoader` backed by an in-process dict instead of a file. The web flow has no file to read — the HTTP request body already *is* the data — so the controller stores the just-built `Request` here under a synthetic id and `SolveSingleRequest` loads it back exactly like it would from `JsonDataLoader`, unmodified.
   - **`web/controller.py`** — Translates a raw (already-validated) payload dict into a domain `Request`, stores it via the injected `InMemoryDataLoader`, and calls `SolveSingleRequest.solve()`. Catches `ValueError` from `Request`/`Product` construction (a domain invariant Pydantic's field-level validation can't express, e.g. "no duplicate product names") and turns it into a normal `FAILURE` response instead of letting it propagate as an unhandled exception.
   - **`web/presenter.py`** — Reshapes an `OptimizationResponse` into plain data (dict/list/str/float/int) the web framework can serialize — `Recommendation.quantities` is a `dict[Product, int]`, and `Product` isn't JSON-serializable on its own.

   Both `controller.py` and `presenter.py` take no dependency on Pydantic or FastAPI — those belong to `frameworks_and_drivers/web/`, one ring further out. This keeps Clean Architecture's dependency rule intact: outer rings may depend on inner ones, never the reverse.
4. **`startup.py`** — Configuration (`Settings` for the CLI, `WebSettings` for the web app) plus the composition root: factory functions that assemble the full object graph for either delivery mechanism, including resolving `solver_name` to a concrete solver.
5. **`frameworks_and_drivers/`** — The outermost ring; both delivery mechanisms call into `startup.py` and dispatch, never constructing a concrete adapter or use case themselves:
   - **`cli.py`** — Parses arguments (argparse) and dispatches.
   - **`web/main.py`** — The FastAPI app instance; what `uvicorn` points at.
   - **`web/routes.py`** — `POST /solve` and `GET /health`. `solve` is a plain `def`, not `async def`, so Starlette runs the CPU-bound solver call in a worker thread instead of blocking the event loop that serves every other connection (including the static frontend).
   - **`web/schemas.py`** — Pydantic request/response models. Field constraints (`gt=0`, `min_length=1`) reject malformed input with a standard `422` before the controller ever runs; JSON keys are camelCase (`maxWeightKg`, `priceUsd`, ...) via Pydantic aliases, matching the camelCase-in/snake_case-domain convention `adapters/json_data_loader.py` already established.
   - **`web/static/`** — The frontend: plain HTML/CSS/vanilla JS, no templating engine, no build step. `app.js` builds the product-row table, POSTs to `/solve`, and renders the response.

---
