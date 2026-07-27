import json

import pytest

from domain.product import Product
from domain.recommendation import Recommendation
from domain.request import Request
from adapters.json_result_writer import JsonResultWriter
from use_cases.optimization_response import OptimizationResponse


@pytest.fixture
def banana() -> Product:
    return Product(name="banana", price_usd=0.5, weight_kg=0.12, calories=89)


@pytest.fixture
def request_(banana) -> Request:
    return Request(max_weight_kg=5.0, max_budget_usd=10.0, products=[banana])


@pytest.fixture
def recommendation(request_, banana) -> Recommendation:
    return Recommendation(request=request_, quantities={banana: 3})


def _timestamp_folder_name(response: OptimizationResponse) -> str:
    return response.timestamp.strftime("%Y_%m_%d_%H_%M_%S")


def test__json_result_writer__on_success__copies_input_file_into_run_folder(tmp_path, recommendation):
    # ARRANGE
    input_path = tmp_path / "data.json"
    input_path.write_text('{"maxWeightKg": 5.0}', encoding="utf-8")
    output_root = tmp_path / "output"
    writer = JsonResultWriter(output_folder_path=str(output_root))
    response = OptimizationResponse.success(recommendation)

    # ACT
    run_folder = writer.write("1", response, input_path)

    # ASSERT
    expected_folder = output_root / "1" / _timestamp_folder_name(response)
    assert run_folder == expected_folder
    assert (run_folder / "input.json").read_text(encoding="utf-8") == '{"maxWeightKg": 5.0}'


def test__json_result_writer__on_success__writes_status_json_with_success_status(tmp_path, recommendation):
    # ARRANGE
    input_path = tmp_path / "data.json"
    input_path.write_text("{}", encoding="utf-8")
    writer = JsonResultWriter(output_folder_path=str(tmp_path / "output"))
    response = OptimizationResponse.success(recommendation)

    # ACT
    run_folder = writer.write("1", response, input_path)

    # ASSERT
    status = json.loads((run_folder / "status.json").read_text(encoding="utf-8"))
    assert status["status"] == "SUCCESS"
    assert status["message"] is None


def test__json_result_writer__on_failure__writes_status_and_message_but_no_solution(tmp_path):
    # ARRANGE
    input_path = tmp_path / "data.json"
    input_path.write_text("{}", encoding="utf-8")
    writer = JsonResultWriter(output_folder_path=str(tmp_path / "output"))
    response = OptimizationResponse.failure("no combination fits the budget")

    # ACT
    run_folder = writer.write("1", response, input_path)

    # ASSERT
    status = json.loads((run_folder / "status.json").read_text(encoding="utf-8"))
    assert status["status"] == "FAILURE"
    assert status["message"] == "no combination fits the budget"
    assert not (run_folder / "solution.json").exists()


def test__json_result_writer__on_success__writes_one_entry_per_product_including_unpurchased(tmp_path, banana):
    # ARRANGE — apple is in the catalog but not purchased (quantity 0)
    apple = Product(name="apple", price_usd=1.20, weight_kg=0.15, calories=95)
    req = Request(max_weight_kg=5.0, max_budget_usd=10.0, products=[banana, apple])
    recommendation = Recommendation(request=req, quantities={banana: 3})
    input_path = tmp_path / "data.json"
    input_path.write_text("{}", encoding="utf-8")
    writer = JsonResultWriter(output_folder_path=str(tmp_path / "output"))
    response = OptimizationResponse.success(recommendation)

    # ACT
    run_folder = writer.write("1", response, input_path)

    # ASSERT
    solution = json.loads((run_folder / "solution.json").read_text(encoding="utf-8"))
    products_by_name = {p["name"]: p for p in solution["products"]}
    assert products_by_name["banana"]["quantity"] == 3
    assert products_by_name["banana"]["line_calories"] == 267
    assert products_by_name["apple"]["quantity"] == 0
    assert solution["total_quantity"] == 3
    assert solution["total_calories"] == 267
