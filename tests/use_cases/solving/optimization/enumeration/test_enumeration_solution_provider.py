import pytest

from domain.product import Product
from domain.request import Request
from use_cases.solving.optimization.enumeration.enumeration_solution_provider import (
    EnumerationSolutionProvider,
    combination_count,
)
from use_cases.solving.preprocessing.pre_processed_data import PreProcessedData


@pytest.fixture
def banana() -> Product:
    return Product(name="banana", price_usd=1.0, weight_kg=1.0, calories=10)


@pytest.fixture
def chips() -> Product:
    return Product(name="chips", price_usd=2.0, weight_kg=1.0, calories=15)


def test__name__returns_human_friendly_label():
    # ACT / ASSERT
    assert EnumerationSolutionProvider().name == "Brute-force Enumeration"


def test__solve__known_optimum__returns_the_best_combination(banana, chips):
    # ARRANGE — budget=4, weight=4. Hand-verified by exhaustive listing: 4
    # banana = 40 calories beats every other combination (e.g. 2 chips = 30,
    # 2 banana + 1 chips = 35).
    request = Request(max_weight_kg=4.0, max_budget_usd=4.0, products=[banana, chips])
    data = PreProcessedData(request=request, feasible_products=[banana, chips])

    # ACT
    recommendation = EnumerationSolutionProvider().solve(data)

    # ASSERT
    assert recommendation is not None
    assert recommendation.total_calories == 40
    assert recommendation.quantities == {banana: 4}


def test__solve__given_no_feasible_products__returns_none():
    # ARRANGE — Request requires a non-empty product catalogue, but
    # feasible_products (what preprocessing decided actually fits) can still
    # be empty, simulating "nothing survived preprocessing" without needing
    # PreProcess itself in this unit test.
    unaffordable = Product(name="unaffordable", price_usd=100.0, weight_kg=1.0, calories=10)
    request = Request(max_weight_kg=5.0, max_budget_usd=5.0, products=[unaffordable])
    data = PreProcessedData(request=request, feasible_products=[])

    # ACT / ASSERT
    assert EnumerationSolutionProvider().solve(data) is None


def test__solve__tie_between_equal_products__keeps_first_enumerated_combination():
    # ARRANGE — cookie_a and cookie_b are identical in every field but name.
    # Both are individually optimal (10 calories for $1/1kg with budget=1,
    # weight=1), but only one unit total fits. itertools.product varies its
    # *last* argument fastest (like the innermost loop of nested for-loops),
    # so with cookie_a's range first and cookie_b's second, the visiting
    # order is (0,0), (0,1), (1,0), (1,1) — the first feasible combination
    # reached is "1 cookie_b", and the strict '>' comparison in solve() means
    # a later equal-calorie combination ("1 cookie_a") never displaces it.
    cookie_a = Product(name="cookie_a", price_usd=1.0, weight_kg=1.0, calories=10)
    cookie_b = Product(name="cookie_b", price_usd=1.0, weight_kg=1.0, calories=10)
    request = Request(max_weight_kg=1.0, max_budget_usd=1.0, products=[cookie_a, cookie_b])
    data = PreProcessedData(request=request, feasible_products=[cookie_a, cookie_b])

    # ACT
    recommendation = EnumerationSolutionProvider().solve(data)

    # ASSERT
    assert recommendation is not None
    assert recommendation.quantities == {cookie_b: 1}


def test__combination_count__matches_product_of_per_product_bounds(banana, chips):
    # ARRANGE — banana: floor(min(4/1, 4/1)) = 4 -> 5 values (0..4).
    # chips: floor(min(4/2, 4/1)) = 2 -> 3 values (0..2).
    request = Request(max_weight_kg=4.0, max_budget_usd=4.0, products=[banana, chips])
    data = PreProcessedData(request=request, feasible_products=[banana, chips])

    # ACT / ASSERT
    assert combination_count(data) == 5 * 3
