# Unit Testing Guide — Python 3.11

---

## 1. Anatomy of a unit test

Always follow the **ARRANGE / ACT / ASSERT** (AAA) pattern:

```python
def test__purchase__given_inventory_10_customer_buys_5__final_inventory_is_5():
    # ARRANGE
    store = Store()
    store.add_inventory(Product.SHAMPOO, 10)
    customer = Customer()

    # ACT
    result = customer.purchase(store, Product.SHAMPOO, 5)

    # ASSERT
    assert result is True
    assert store.get_inventory(Product.SHAMPOO) == 5
```

Rules:

- One section each. Never interleave arrange and assert.
- One `# ACT` call per test. If you need two, you are testing two behaviors.
- Keep `# ARRANGE` concise — use fixtures or factory functions if setup is complex.

---

## 2. Naming tests

Test names have three sections: unit being tested, scenario, and expected outcome. Separate
sections with double underscores (`__`) to improve readability. Pytest discovers any function
starting with `test`; the double underscore after `test` visually separates the prefix from the
unit of behavior.

```python
# Good — describes behavior and conditions
def test__purchase__when_not_enough_inventory__fails():
    ...
```

Pattern: `test__[unit of behavior]__[scenario]__[expected outcome]`

---

## 3. Test file organization

Maintain a **1:1 mapping** between production modules and test modules. Each production file gets its
own test file with a matching name prefixed by `test_`.

```
src/                          tests/
├── domain/                   ├── domain/
│   ├── product.py            │   ├── test_product.py
│   ├── request.py            │   ├── test_request.py
│   └── recommendation.py     │   └── test_recommendation.py
├── services/                 ├── services/
│   ├── engine.py             │   ├── test_engine.py
│   └── json_data_loader.py   │   └── test_json_data_loader.py
└── optimization/             └── optimization/
    └── strategy/                 └── strategy/
        └── mip/                      └── mip/
            └── mip_strategy.py           └── test_mip_strategy.py
```

Rules:

- One test file per production file — never combine tests for multiple modules into a single file.
- Mirror the production directory structure under `tests/`.
- **Do not group tests inside classes.** Write every test as a standalone top-level function.
  Pytest discovers functions directly; classes add indirection without any benefit for pure unit
  tests. Use fixtures (see section 7) instead of `setUp`/`tearDown` methods.

```python
# Bad — unnecessary class wrapper
class TestProduct:
    def test__product__given_valid_inputs__creates_successfully(self):
        product = Product(name="banana", price_usd=0.5, weight_kg=0.12, calories=89)
        assert product.name == "banana"

# Good — flat standalone function
def test__product__given_valid_inputs__creates_successfully():
    product = Product(name="banana", price_usd=0.5, weight_kg=0.12, calories=89)
    assert product.name == "banana"
```

---

## 4. What to test: public behavior, not implementation

Test **observable behavior** — what the system does from the caller's perspective, not how it does it.

```python
# Bad — tests internal state (implementation detail)
def test__constructor__given_input__normalizes_email_internally():
    user = User("USER@EXAMPLE.COM")
    assert user._is_email_normalized  # internal flag — fragile!

# Good — tests observable outcome
def test__constructor__given_input__normalizes_email_attribute():
    user = User("USER@EXAMPLE.COM")
    assert user.email == "user@example.com"
```

If a refactor breaks this test without changing behavior, the test was testing the wrong thing.

---

## 5. Humble Object pattern

When code is hard to test (e.g., file I/O, message consumers, database access), split it:

- **Humble Object**: thin shell with no logic, hard to test, skip unit tests.
- **Extracted logic**: pure logic with no I/O, easy to test.

```python
# Hard to test — logic tangled with I/O
class ReportController:
    def generate(self, report_id: int) -> None:
        data = self.database.fetch(report_id)                # I/O
        active = [row for row in data if row.is_active]      # logic mixed in
        total = sum(row.amount for row in active)             # logic mixed in
        self.email_service.send(f"Total: {total}")           # I/O

# After Humble Object split:
class ReportCalculator:  # pure logic — easy to unit test
    def calculate(self, rows: list[Row]) -> int:
        return sum(row.amount for row in rows if row.is_active)

class ReportController:  # humble object — just orchestration
    def generate(self, report_id: int) -> None:
        data = self.database.fetch(report_id)
        total = ReportCalculator().calculate(data)
        self.email_service.send(f"Total: {total}")
```

Test `ReportCalculator` with pure unit tests. Test `ReportController` with integration tests or
not at all.

---

## 6. Avoid test-induced design damage

Do not change production design just to make testing easier. Signs you are doing this:

- Making private methods public to test them directly.
- Adding constructor parameters only for injecting mocks.
- Exposing internal state via properties used only in tests.

```python
# Bad — exposing internals for test convenience
class Order:
    def __init__(self) -> None:
        self._items: list[Item] = []

    @property
    def items(self) -> list[Item]:
        """Added only for tests — leaks internals."""
        return list(self._items)

# Good — test observable behavior
def test__total__when_items_are_added__reflects_quantity_and_price():
    order = Order()
    order.add(Product("Widget", 10), quantity=3)

    assert order.total() == 30  # test behavior, not the internal item list
```

---

## 7. Test isolation: every test must own its data

Each test must be fully independent — it must not share mutable state with any other test. Two
mechanisms achieve this. Choose the one that keeps the test most readable.

### Option 1 — local construction inside the test (preferred for simple cases)

Declare and construct the system under test as a local variable directly inside the test function.
This is the simplest form of isolation and makes the test entirely self-contained.

```python
# Good — no shared state; the instance exists only for this test
def test__do_something__scenario__outcome():
    # ARRANGE
    foo = Foo()

    # ACT
    result = foo.do_something()

    # ASSERT
    assert result == expected
```

### Option 2 — pytest fixtures for shared, non-trivial setup

When multiple tests require identical setup that would be noisy to repeat inline — such as
constructing a collaborator graph or loading test data — extract it into a pytest fixture. Fixtures
guarantee a fresh instance for each test by default (`scope="function"`).

```python
import pytest

@pytest.fixture
def store() -> Store:
    """Provide a store pre-loaded with default inventory."""
    s = Store()
    s.add_inventory(Product.SHAMPOO, 10)
    s.add_inventory(Product.CONDITIONER, 5)
    return s

def test__purchase__when_enough_inventory__succeeds(store: Store):
    # ARRANGE
    customer = Customer()

    # ACT
    result = customer.purchase(store, Product.SHAMPOO, 3)

    # ASSERT
    assert result is True
    assert store.get_inventory(Product.SHAMPOO) == 7
```

### What to avoid — module-level mutable state

Never initialize the system under test as a module-level variable shared across tests. This
silently breaks isolation when the object has mutable state.

```python
# Bad — shared mutable state across tests
foo = Foo()  # ← avoid

def test__first():
    foo.do_something()  # mutates foo

def test__second():
    # foo is already mutated from test_first — order-dependent!
    ...
```

---

## 8. Parametrized tests

Use `@pytest.mark.parametrize` to run the same test logic over multiple inputs. This eliminates
duplication when the test structure is identical but the data varies.

```python
import pytest

@pytest.mark.parametrize(
    "sense, expected",
    [
        ("<=", True),
        (">=", True),
        ("=", True),
        ("<", False),
        ("!=", False),
    ],
)
def test__validate_sense__given_input__returns_expected(sense: str, expected: bool):
    # ACT
    result = validate_sense(sense)

    # ASSERT
    assert result == expected
```

Rules:

- Use parametrize when the test body is identical across cases — only inputs and expected
  outputs change.
- Do not use parametrize to combine unrelated behaviors into one test. If the arrange or assert
  sections differ, write separate tests.
- Give descriptive IDs when the default string representation is unclear:

```python
@pytest.mark.parametrize("value", [0, -1, 100], ids=["zero", "negative", "large"])
def test__boundary__given_value__behaves_correctly(value: int):
    ...
```

---

## 9. Test markers

Use pytest markers to categorize tests. Register custom markers in `pytest.ini` to avoid warnings.

```ini
# pytest.ini
[pytest]
markers =
    integration: marks tests as integration tests (deselect with '-m "not integration"')
```

Apply the marker to integration tests:

```python
import pytest

@pytest.mark.integration
def test__optimize_endpoint__given_valid_input__returns_success():
    ...
```

Run subsets from the command line:

```bash
# Unit tests only
pytest -m "not integration"

# Integration tests only
pytest -m integration

# All tests
pytest
```

---

## 10. Mocking guidance

Use mocking sparingly and only at I/O boundaries. Do not mock domain logic or value
objects — those should be tested with real instances.

### When to mock

- **External services**: HTTP clients, database connections, email senders.
- **I/O and external calls**: File system access, third-party SDK calls.
- **Time-dependent code**: `datetime.now()`, `time.time()`.

### When not to mock

- **Domain models and value objects**: Use real instances.
- **Pure functions**: They have no side effects — call them directly.
- **Internal collaborators in the same layer**: Prefer integration over isolation.

```python
from unittest.mock import MagicMock

def test__use_case__when_solver_returns_optimal__returns_success():
    # ARRANGE
    mock_solver = MagicMock()
    mock_solver.solve.return_value = OptimizationResult(
        status="Optimal",
        objective_value=42.0,
        variable_values={"x": 1.0},
    )
    use_case = SolveOptimization(engine=mock_solver)

    # ACT
    result = use_case.execute(problem)

    # ASSERT
    assert result.status == "Optimal"
    mock_solver.solve.assert_called_once()
```

Prefer dependency injection over patching. If you must patch, use `unittest.mock.patch` as a
decorator or context manager, and always patch where the object is *used*, not where it is defined.

---

## 11. Coverage target: 90% line coverage

The project targets **90% line coverage** measured by `pytest-cov`.

Run coverage:

```bash
pytest --cov=app --cov-report=term-missing
```

Cover every non-trivial branch: happy paths, error paths, and edge cases. If the overall coverage
falls below 90%, investigate whether the shortfall is in domain logic (fix it with real tests) or
in structurally uncoverable code (document the reason).

Do not chase 100% by writing tests for trivial code or changing production design.

---

## 12. Keep tests readable: one assertion per behavior

Each test should verify one behavioral outcome. Multiple assertions are fine if they all describe
the same behavior.

```python
# Okay — both assertions describe the same outcome
def test__purchase__when_successful__updates_inventory_and_returns_true():
    # ARRANGE
    store = Store()
    store.add_inventory(Product.SHAMPOO, 10)
    customer = Customer()

    # ACT
    result = customer.purchase(store, Product.SHAMPOO, 1)

    # ASSERT
    assert result is True
    assert store.get_inventory(Product.SHAMPOO) == 9

# Bad — two different behaviors in one test
def test_purchase():
    # tests success path AND failure path together — split these
    ...
```

---
