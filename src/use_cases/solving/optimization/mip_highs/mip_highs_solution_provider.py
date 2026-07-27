"""
ROLE: Implementation — of SolutionProvider, for the HiGHS solver technology.

WHY THIS EXISTS:
    This is the only file in the project that imports highspy — everything
    about building the model (variables, objective, constraints) and reading
    the solution back out lives here, with no shared abstraction between this
    and MipGoogleScipSolutionProvider: each technology owns its own complete
    formulation, since the two solvers' APIs don't share a common shape worth
    abstracting over for a template this size.
"""

from __future__ import annotations

import logging
from pathlib import Path

import highspy
import numpy as np

from domain.product import Product
from domain.recommendation import Recommendation
from domain.request import Request
from use_cases.solving.optimization.solution_provider import SolutionProvider
from use_cases.solving.preprocessing.pre_processed_data import PreProcessedData

logger = logging.getLogger(__name__)

# Floating-point values returned by MIP solvers for integer variables are not
# always exact (e.g. 0.9999 instead of 1). Values are rounded to the nearest
# integer when extracting the solution.
_FEASIBLE_STATUSES = {
    highspy.HighsModelStatus.kOptimal,
    highspy.HighsModelStatus.kObjectiveBound,
    highspy.HighsModelStatus.kObjectiveTarget,
    highspy.HighsModelStatus.kSolutionLimit,
}


class MipHighsSolutionProvider(SolutionProvider):
    """Builds the knapsack MIP model directly against highspy and solves it.

        maximize   sum(i) calories_i * x_i
        subject to sum(i) price_i * x_i  <= max_budget_usd
                   sum(i) weight_i * x_i <= max_weight_kg
                   x_i >= 0, integer

    Where x_i is the number of units of product i selected.
    """

    @property
    def name(self) -> str:
        return "MIP (HiGHS)"

    def solve(self, data: PreProcessedData, output_dir: Path | None = None) -> Recommendation | None:
        """Build, solve, and extract a Recommendation from the MIP model.

        Args:
            data: The preprocessed knapsack data with products and constraints.
            output_dir: If given, the built model is dumped as "model.lp" in
                this directory before solving starts. This lets a data
                scientist inspect the exact formulation HiGHS received —
                useful when a solution looks wrong. Pass None to skip writing it.

        Returns:
            The single optimal Recommendation, or None if no feasible
            solution exists.
        """
        request = data.request
        # Wrapping feasible_products in a temporary Request lets column
        # building iterate only products that can be selected, while the
        # final Recommendation is still built against the original request.
        feasible_request = Request(
            max_weight_kg=request.max_weight_kg,
            max_budget_usd=request.max_budget_usd,
            products=data.feasible_products,
        )

        highs_model = highspy.Highs()
        col_index = self._add_variables(feasible_request, highs_model)
        self._set_objective(feasible_request, col_index, highs_model)
        self._add_constraints(feasible_request, col_index, highs_model)

        if output_dir is not None:
            output_dir.mkdir(parents=True, exist_ok=True)
            # highspy infers the output format (LP vs MPS) from the file
            # extension, so ".lp" is what selects the human-readable LP format.
            highs_model.writeModel(str(output_dir / "model.lp"))

        highs_model.run()
        status = highs_model.getModelStatus()
        logger.info("HiGHS terminated with status: %s", status)

        return self._extract_recommendation(request, feasible_request, status, highs_model)

    def _add_variables(self, request: Request, highs_model: highspy.Highs) -> dict[str, int]:
        """Add one non-negative integer variable per product.

        Args:
            request: Request wrapping only the feasible products.
            highs_model: The HiGHS model instance being built for this solve() call.

        Returns:
            Mapping from variable name to HiGHS column index, used to
            reference variables when building constraints and the objective.
        """
        col_index: dict[str, int] = {}
        for i, product in enumerate(request.products):
            highs_model.addVar(0.0, highspy.kHighsInf)
            # Without this, HiGHS defaults to generic labels ("c0", "c1", ...)
            # for every column, which makes the model.lp dump unreadable.
            name = self.variable_name(product.name)
            highs_model.passColName(i, name)
            highs_model.changeColIntegrality(i, highspy.HighsVarType.kInteger)
            col_index[name] = i
        return col_index

    def _set_objective(self, request: Request, col_index: dict[str, int], highs_model: highspy.Highs) -> None:
        """Set the calorie-maximization objective.

        Args:
            request: Request wrapping only the feasible products.
            col_index: Mapping from variable name to HiGHS column index.
            highs_model: The HiGHS model instance being built for this solve() call.
        """
        for product in request.products:
            highs_model.changeColCost(col_index[self.variable_name(product.name)], product.calories)
        highs_model.changeObjectiveSense(highspy.ObjSense.kMaximize)

    def _add_constraints(self, request: Request, col_index: dict[str, int], highs_model: highspy.Highs) -> None:
        """Add the budget and weight capacity constraints.

        Args:
            request: Request wrapping only the feasible products.
            col_index: Mapping from variable name to HiGHS column index.
            highs_model: The HiGHS model instance being built for this solve() call.
        """
        indices = np.array([col_index[self.variable_name(p.name)] for p in request.products], dtype=np.int32)

        # Constraint: sum(i) price_i * x_i <= max_budget_usd
        budget_coeffs = np.array([p.price_usd for p in request.products], dtype=np.float64)
        highs_model.addRow(-highspy.kHighsInf, request.max_budget_usd, len(indices), indices, budget_coeffs)
        highs_model.passRowName(0, "budget_limit")

        # Constraint: sum(i) weight_i * x_i <= max_weight_kg
        weight_coeffs = np.array([p.weight_kg for p in request.products], dtype=np.float64)
        highs_model.addRow(-highspy.kHighsInf, request.max_weight_kg, len(indices), indices, weight_coeffs)
        highs_model.passRowName(1, "weight_limit")

    def _extract_recommendation(
        self,
        request: Request,
        feasible_request: Request,
        status: highspy.HighsModelStatus,
        highs_model: highspy.Highs,
    ) -> Recommendation | None:
        """Convert the HiGHS solution back into a domain Recommendation.

        Args:
            request: The original request (Recommendation is built against
                this, not feasible_request, so quantities can be validated
                against the request's real budget/weight limits).
            feasible_request: Request wrapping only the feasible products,
                whose ordering matches the columns HiGHS solved for.
            status: The model status returned by HiGHS.
            highs_model: The HiGHS model instance that was solved.

        Returns:
            A Recommendation, or None if no feasible solution exists.
        """
        if status not in _FEASIBLE_STATUSES:
            return None

        sol = highs_model.getSolution()
        # Keyed with the same variable_name() used to build the model, so a
        # solved variable name maps straight back to its Product with no
        # separate "strip the prefix" logic to keep in sync.
        product_map = {self.variable_name(p.name): p for p in request.products}
        quantities: dict[Product, int] = {}
        for i, product in enumerate(feasible_request.products):
            value = sol.col_value[i]
            qty = int(round(value))
            if qty >= 1:
                quantities[product_map[self.variable_name(product.name)]] = qty

        if not quantities:
            return None

        return Recommendation(request=request, quantities=quantities)

    @staticmethod
    def variable_name(product_name: str) -> str:
        """Return the solver-facing variable name for a product's decision variable.

        Prefixing with "quantity_" makes model.lp self-explanatory: a reader
        immediately sees "quantity_banana" as the number of units of banana
        bought, rather than a bare "banana" that could be confused with some
        other variable kind referencing the same product if the model grows
        later. The variable is a general (unbounded) integer, not binary — it
        counts units, it isn't a yes/no decision.
        """
        return f"quantity_{product_name}"
