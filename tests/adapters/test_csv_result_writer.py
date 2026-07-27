import pytest

from domain.product import Product
from domain.recommendation import Recommendation
from domain.request import Request
from adapters.csv_result_writer import CsvResultWriter
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


def test__csv_result_writer__on_success__copies_input_file_into_run_folder(tmp_path, recommendation):
    # ARRANGE
    input_path = tmp_path / "data.json"
    input_path.write_text('{"maxWeightKg": 5.0}', encoding="utf-8")
    output_root = tmp_path / "output"
    writer = CsvResultWriter(output_folder_path=str(output_root))
    response = OptimizationResponse.success(recommendation)

    # ACT
    run_folder = writer.write("1", response, input_path)

    # ASSERT
    expected_folder = output_root / "1" / _timestamp_folder_name(response)
    assert run_folder == expected_folder
    assert (run_folder / "input.json").read_text(encoding="utf-8") == '{"maxWeightKg": 5.0}'


def test__csv_result_writer__on_success__writes_status_txt_with_success_status(tmp_path, recommendation):
    # ARRANGE
    input_path = tmp_path / "data.json"
    input_path.write_text("{}", encoding="utf-8")
    writer = CsvResultWriter(output_folder_path=str(tmp_path / "output"))
    response = OptimizationResponse.success(recommendation)

    # ACT
    run_folder = writer.write("1", response, input_path)

    # ASSERT
    status_text = (run_folder / "status.txt").read_text(encoding="utf-8")
    assert "SUCCESS" in status_text


def test__csv_result_writer__on_failure__writes_status_and_message_but_no_csv(tmp_path):
    # ARRANGE
    input_path = tmp_path / "data.json"
    input_path.write_text("{}", encoding="utf-8")
    writer = CsvResultWriter(output_folder_path=str(tmp_path / "output"))
    response = OptimizationResponse.failure("no combination fits the budget")

    # ACT
    run_folder = writer.write("1", response, input_path)

    # ASSERT
    status_text = (run_folder / "status.txt").read_text(encoding="utf-8")
    assert "FAILURE" in status_text
    assert "no combination fits the budget" in status_text
    assert not (run_folder / "solution.csv").exists()


def test__csv_result_writer__on_success__writes_one_row_per_product_including_unpurchased(tmp_path, banana):
    # ARRANGE — apple is in the catalog but not purchased (quantity 0)
    apple = Product(name="apple", price_usd=1.20, weight_kg=0.15, calories=95)
    req = Request(max_weight_kg=5.0, max_budget_usd=10.0, products=[banana, apple])
    recommendation = Recommendation(request=req, quantities={banana: 3})
    input_path = tmp_path / "data.json"
    input_path.write_text("{}", encoding="utf-8")
    writer = CsvResultWriter(output_folder_path=str(tmp_path / "output"))
    response = OptimizationResponse.success(recommendation)

    # ACT
    run_folder = writer.write("1", response, input_path)

    # ASSERT
    rows = (run_folder / "solution.csv").read_text(encoding="utf-8").splitlines()
    assert rows[0] == "name,price_usd,weight_kg,calories,quantity,line_cost_usd,line_weight_kg,line_calories"
    assert rows[1] == "banana,0.5,0.12,89,3,1.5,0.36,267"
    assert rows[2] == "apple,1.2,0.15,95,0,0.0,0.0,0"
    assert rows[3] == "TOTAL,,,,3,1.5,0.36,267"
