import json
import math

import pytest

from adapters.json_data_loader import JsonDataLoader


def _write_json(tmp_path, request_id: str, payload: dict) -> None:
    """Helper: write data.json for a given request_id into tmp_path."""
    folder = tmp_path / request_id
    folder.mkdir()
    (folder / "data.json").write_text(json.dumps(payload), encoding="utf-8")


def test__json_data_loader__when_file_missing__returns_none(tmp_path):
    # ARRANGE
    loader = JsonDataLoader(folder_path=str(tmp_path))

    # ACT
    result = loader.load("nonexistent")

    # ASSERT
    assert result is None


def test__json_data_loader__when_valid_json__returns_request(tmp_path):
    # ARRANGE
    payload = {
        "requestId": "1",
        "maxWeightKg": 1.0,
        "maxBudgetUsd": 5.0,
        "products": [{"name": "banana", "priceUsd": 1.00, "weightKg": 0.50, "calories": 100}],
    }
    _write_json(tmp_path, "1", payload)
    loader = JsonDataLoader(folder_path=str(tmp_path))

    # ACT
    result = loader.load("1")

    # ASSERT
    assert result is not None
    assert math.isclose(result.max_weight_kg, 1.0)
    assert math.isclose(result.max_budget_usd, 5.0)
    assert len(result.products) == 1
    assert result.products[0].name == "banana"
    assert math.isclose(result.products[0].price_usd, 1.00)
    assert math.isclose(result.products[0].weight_kg, 0.50)
    assert result.products[0].calories == 100


def test__json_data_loader__when_json_is_malformed__raises_value_error(tmp_path):
    # ARRANGE
    folder = tmp_path / "bad"
    folder.mkdir()
    (folder / "data.json").write_text("{ not valid json }", encoding="utf-8")
    loader = JsonDataLoader(folder_path=str(tmp_path))

    # ACT / ASSERT
    with pytest.raises(ValueError, match="not valid JSON"):
        loader.load("bad")


def test__json_data_loader__when_required_field_missing__raises_value_error(tmp_path):
    # ARRANGE — maxBudgetUsd is absent
    payload = {
        "requestId": "1",
        "maxWeightKg": 1.0,
        "products": [{"name": "banana", "priceUsd": 1.00, "weightKg": 0.50, "calories": 100}],
    }
    _write_json(tmp_path, "1", payload)
    loader = JsonDataLoader(folder_path=str(tmp_path))

    # ACT / ASSERT
    with pytest.raises(ValueError, match="missing required field"):
        loader.load("1")


def test__json_data_loader__when_product_field_missing__raises_value_error(tmp_path):
    # ARRANGE — weightKg is absent from the product entry
    payload = {
        "requestId": "1",
        "maxWeightKg": 1.0,
        "maxBudgetUsd": 5.0,
        "products": [{"name": "banana", "priceUsd": 1.00, "calories": 100}],  # weightKg omitted
    }
    _write_json(tmp_path, "1", payload)
    loader = JsonDataLoader(folder_path=str(tmp_path))

    # ACT / ASSERT
    with pytest.raises(ValueError, match="missing required field"):
        loader.load("1")
