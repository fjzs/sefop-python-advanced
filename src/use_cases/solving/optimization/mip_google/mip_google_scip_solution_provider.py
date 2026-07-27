"""
ROLE: Implementation — of SolutionProvider, for the MathOpt technology configured to run
the GSCIP (SCIP) solver backend.

WHY THIS EXISTS:
    Mirrors MipHighsSolutionProvider's contract and internal shape (variables ->
    objective -> constraints -> extract) but drives MathOpt's expression-based model-building
    API (build a linear expression with normal Python operators) instead of HiGHS's
    index/matrix-based one, since the two libraries don't share a common enough shape to
    abstract over for a template this size.
"""

from __future__ import annotations

import logging
from pathlib import Path

from google.protobuf import text_format
from ortools.math_opt.python import mathopt

from domain.product import Product
from domain.recommendation import Recommendation
from domain.request import Request
from use_cases.solving.optimization.solution_provider import SolutionProvider
from use_cases.solving.preprocessing.pre_processed_data import PreProcessedData

logger = logging.getLogger(__name__)


class MipGoogleScipSolutionProvider(SolutionProvider):
    """Builds the knapsack MIP model against Google OR-Tools MathOpt and solves it with SCIP.

        maximize   sum(i) calories_i * x_i
        subject to sum(i) price_i * x_i  <= max_budget_usd
                   sum(i) weight_i * x_i <= max_weight_kg
                   x_i >= 0, integer

    Where x_i is the number of units of product i selected.
    """

    @property
    def name(self) -> str:
        return "MIP (Google SCIP)"

    def solve(self, data: PreProcessedData, output_dir: Path | None = None) -> Recommendation | None:
        """Build, solve, and extract a Recommendation from the MathOpt model.

        Args:
            data: The preprocessed knapsack data with products and constraints.
            output_dir: If given, the built model is dumped as "model.pbtxt" in
                this directory before solving starts. MathOpt's Python API has no
                LP/MPS exporter (unlike highspy), so the protobuf text format is
                the most readable dump it can produce. Pass None to skip writing it.

        Returns:
            The single optimal Recommendation, or None if no feasible solution exists.
        """
        request = data.request
        # Wrapping feasible_products in a temporary Request lets model building
        # iterate only products that can be selected, while the final
        # Recommendation is still built against the original request.
        feasible_request = Request(
            max_weight_kg=request.max_weight_kg,
            max_budget_usd=request.max_budget_usd,
            products=data.feasible_products,
        )

        model = mathopt.Model(name="knapsack")
        variables = self._add_variables(feasible_request, model)
        self._set_objective(feasible_request, variables, model)
        self._add_constraints(feasible_request, variables, model)

        if output_dir is not None:
            output_dir.mkdir(parents=True, exist_ok=True)
            proto_text = text_format.MessageToString(model.export_model())
            (output_dir / "model.pbtxt").write_text(proto_text, encoding="utf-8")

        # enable_output=True mirrors HiGHS's default behavior of printing its
        # solve progress to the console; MathOpt defaults this to off.
        result = mathopt.solve(model, mathopt.SolverType.GSCIP, params=mathopt.SolveParameters(enable_output=True))
        logger.info("MathOpt/GSCIP terminated with: %s", result.termination.reason)

        return self._extract_recommendation(request, feasible_request, variables, result)

    def _add_variables(self, request: Request, model: mathopt.Model) -> dict[str, mathopt.Variable]:
        """Add one non-negative integer variable per product.

        Args:
            request: Request wrapping only the feasible products.
            model: The MathOpt model instance being built for this solve() call.

        Returns:
            Mapping from variable name to the MathOpt Variable, used to
            reference variables when building constraints and the objective.
        """
        variables: dict[str, mathopt.Variable] = {}
        for product in request.products:
            name = self.variable_name(product.name)
            variables[name] = model.add_integer_variable(lb=0, name=name)
        return variables

    def _set_objective(self, request: Request, variables: dict[str, mathopt.Variable], model: mathopt.Model) -> None:
        """Set the calorie-maximization objective.

        Args:
            request: Request wrapping only the feasible products.
            variables: Mapping from variable name to MathOpt Variable.
            model: The MathOpt model instance being built for this solve() call.
        """
        model.maximize(
            sum(product.calories * variables[self.variable_name(product.name)] for product in request.products)
        )

    def _add_constraints(self, request: Request, variables: dict[str, mathopt.Variable], model: mathopt.Model) -> None:
        """Add the budget and weight capacity constraints.

        Args:
            request: Request wrapping only the feasible products.
            variables: Mapping from variable name to MathOpt Variable.
            model: The MathOpt model instance being built for this solve() call.
        """
        model.add_linear_constraint(
            sum(product.price_usd * variables[self.variable_name(product.name)] for product in request.products)
            <= request.max_budget_usd,
            name="budget_limit",
        )
        model.add_linear_constraint(
            sum(product.weight_kg * variables[self.variable_name(product.name)] for product in request.products)
            <= request.max_weight_kg,
            name="weight_limit",
        )

    def _extract_recommendation(
        self,
        request: Request,
        feasible_request: Request,
        variables: dict[str, mathopt.Variable],
        result: mathopt.SolveResult,
    ) -> Recommendation | None:
        """Convert the MathOpt solution back into a domain Recommendation.

        Args:
            request: The original request (Recommendation is built against
                this, not feasible_request, so quantities can be validated
                against the request's real budget/weight limits).
            feasible_request: Request wrapping only the feasible products,
                whose products are the keys of variables.
            variables: Mapping from variable name to MathOpt Variable.
            result: The result returned by mathopt.solve().

        Returns:
            A Recommendation, or None if no feasible solution exists.
        """
        if not result.has_primal_feasible_solution():
            return None

        values = result.variable_values()
        # Keyed with the same variable_name() used to build the model, so a
        # solved variable name maps straight back to its Product with no
        # separate "strip the prefix" logic to keep in sync.
        product_map = {self.variable_name(p.name): p for p in request.products}
        quantities: dict[Product, int] = {}
        for product in feasible_request.products:
            name = self.variable_name(product.name)
            value = values[variables[name]]
            qty = int(round(value))
            if qty >= 1:
                quantities[product_map[name]] = qty

        if not quantities:
            return None

        return Recommendation(request=request, quantities=quantities)

    @staticmethod
    def variable_name(product_name: str) -> str:
        """Return the solver-facing variable name for a product's decision variable.

        Prefixing with "quantity_" makes the model.pbtxt dump self-explanatory: a
        reader immediately sees "quantity_banana" as the number of units of banana
        bought, rather than a bare "banana" that could be confused with some other
        variable kind referencing the same product if the model grows later. The
        variable is a general (unbounded) integer, not binary — it counts units,
        it isn't a yes/no decision.
        """
        return f"quantity_{product_name}"
