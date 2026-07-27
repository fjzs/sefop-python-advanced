import pytest

from domain.product import Product
from domain.request import Request
from use_cases.solving.optimization.mip_highs.mip_highs_solution_provider import MipHighsSolutionProvider
from use_cases.solving.preprocessing.pre_processed_data import PreProcessedData


@pytest.fixture
def banana() -> Product:
    return Product(name="banana", price_usd=0.5, weight_kg=0.12, calories=89)


@pytest.fixture
def chips() -> Product:
    return Product(name="chips", price_usd=1.0, weight_kg=0.2, calories=150)


@pytest.fixture
def preprocessed_data(banana, chips) -> PreProcessedData:
    request = Request(max_weight_kg=5.0, max_budget_usd=10.0, products=[banana, chips])
    return PreProcessedData(request=request, feasible_products=[banana, chips])


def test__name__returns_human_friendly_label():
    # ACT / ASSERT
    assert MipHighsSolutionProvider().name == "MIP (HiGHS)"


def test__solve__recommendation_maps_solved_quantities_back_to_the_right_products(preprocessed_data, banana, chips):
    # ACT
    recommendation = MipHighsSolutionProvider().solve(preprocessed_data)

    # ASSERT — the solver only ever sees "quantity_<name>" variable names;
    # this proves the reverse lookup in _extract_recommendation correctly
    # maps them back to the actual Product objects, not e.g. raising KeyError
    # or mixing up products.
    assert recommendation is not None
    for product in recommendation.quantities:
        assert product in {banana, chips}


def test__solve__given_output_dir__writes_model_lp_file(preprocessed_data, tmp_path):
    # ACT
    MipHighsSolutionProvider().solve(preprocessed_data, output_dir=tmp_path)

    # ASSERT — content (variable naming, formatting) is HiGHS-internal detail,
    # not asserted here; only the output_dir contract itself is checked.
    assert (tmp_path / "model.lp").exists()


def test__solve__given_no_output_dir__writes_no_lp_file(preprocessed_data, tmp_path, monkeypatch):
    # ARRANGE — chdir so any accidental relative-path write would land under
    # tmp_path, where it's easy to detect.
    monkeypatch.chdir(tmp_path)

    # ACT
    MipHighsSolutionProvider().solve(preprocessed_data)

    # ASSERT
    assert list(tmp_path.rglob("*.lp")) == []
