import pytest

from adapters.json_solution_loader import JsonSolutionLoader


def test__load__given_missing_file__returns_none(tmp_path):
    # ARRANGE
    loader = JsonSolutionLoader()

    # ACT
    result = loader.load(tmp_path / "missing.json")

    # ASSERT
    assert result is None


def test__load__given_malformed_json__raises_value_error(tmp_path):
    # ARRANGE
    path = tmp_path / "solution.json"
    path.write_text("{ not valid json }", encoding="utf-8")
    loader = JsonSolutionLoader()

    # ACT / ASSERT
    with pytest.raises(ValueError, match="not valid JSON"):
        loader.load(path)


def test__load__given_non_object_json__raises_value_error(tmp_path):
    # ARRANGE
    path = tmp_path / "solution.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")
    loader = JsonSolutionLoader()

    # ACT / ASSERT
    with pytest.raises(ValueError, match="JSON object"):
        loader.load(path)


def test__load__given_non_positive_quantity__raises_value_error(tmp_path):
    # ARRANGE
    path = tmp_path / "solution.json"
    path.write_text('{"banana": 0}', encoding="utf-8")
    loader = JsonSolutionLoader()

    # ACT / ASSERT
    with pytest.raises(ValueError, match="positive integer"):
        loader.load(path)


def test__load__given_non_integer_quantity__raises_value_error(tmp_path):
    # ARRANGE
    path = tmp_path / "solution.json"
    path.write_text('{"banana": 1.5}', encoding="utf-8")
    loader = JsonSolutionLoader()

    # ACT / ASSERT
    with pytest.raises(ValueError, match="positive integer"):
        loader.load(path)


def test__load__given_valid_json__returns_quantities(tmp_path):
    # ARRANGE
    path = tmp_path / "solution.json"
    path.write_text('{"banana": 3, "chips": 2}', encoding="utf-8")
    loader = JsonSolutionLoader()

    # ACT
    quantities = loader.load(path)

    # ASSERT
    assert quantities == {"banana": 3, "chips": 2}
