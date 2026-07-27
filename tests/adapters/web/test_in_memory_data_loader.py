import pytest

from adapters.web.in_memory_data_loader import InMemoryDataLoader
from domain.product import Product
from domain.request import Request


@pytest.fixture
def banana() -> Product:
    return Product(name="banana", price_usd=0.5, weight_kg=0.12, calories=89)


def test__in_memory_data_loader__when_id_unknown__returns_none():
    # ARRANGE
    loader = InMemoryDataLoader()

    # ACT
    result = loader.load("missing")

    # ASSERT
    assert result is None


def test__in_memory_data_loader__given_stored_request__loads_it_back_by_the_returned_id(banana):
    # ARRANGE
    loader = InMemoryDataLoader()
    request = Request(max_weight_kg=5.0, max_budget_usd=10.0, products=[banana])

    # ACT
    request_id = loader.store(request)
    result = loader.load(request_id)

    # ASSERT
    assert result is request


def test__in_memory_data_loader__store_called_twice__each_call_gets_its_own_id(banana):
    # ARRANGE
    loader = InMemoryDataLoader()
    first_request = Request(max_weight_kg=5.0, max_budget_usd=10.0, products=[banana])
    second_request = Request(max_weight_kg=1.0, max_budget_usd=1.0, products=[banana])

    # ACT
    first_id = loader.store(first_request)
    second_id = loader.store(second_request)

    # ASSERT
    assert first_id != second_id
    assert loader.load(first_id) is first_request
    assert loader.load(second_id) is second_request
