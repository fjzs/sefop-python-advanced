// Vanilla JS, no build step, no framework — see CLAUDE.md/the design plan for why.
// This file's whole job: build a product row table, turn the form into the
// POST /solve JSON body the backend expects, and render whatever comes back.

const productsBody = document.getElementById("products-body");
const form = document.getElementById("solve-form");
const solveButton = document.getElementById("solve-button");
const resultSection = document.getElementById("result");
const resultContent = document.getElementById("result-content");

function addProductRow(values) {
  const defaults = values || { name: "", priceUsd: "", weightKg: "", calories: "" };
  const row = document.createElement("tr");
  row.innerHTML = `
    <td><input type="text" class="product-name" value="${defaults.name}" required /></td>
    <td><input type="number" class="product-price" step="0.01" min="0.01" value="${defaults.priceUsd}" required /></td>
    <td><input type="number" class="product-weight" step="0.01" min="0.01" value="${defaults.weightKg}" required /></td>
    <td><input type="number" class="product-calories" step="1" min="1" value="${defaults.calories}" required /></td>
    <td><button type="button" class="remove-product">Remove</button></td>
  `;
  row.querySelector(".remove-product").addEventListener("click", () => row.remove());
  productsBody.appendChild(row);
}

document.getElementById("add-product").addEventListener("click", () => addProductRow());

function collectPayload() {
  const products = Array.from(productsBody.querySelectorAll("tr")).map((row) => ({
    name: row.querySelector(".product-name").value,
    priceUsd: Number(row.querySelector(".product-price").value),
    weightKg: Number(row.querySelector(".product-weight").value),
    calories: Number(row.querySelector(".product-calories").value),
  }));
  return {
    maxWeightKg: Number(document.getElementById("max-weight-kg").value),
    maxBudgetUsd: Number(document.getElementById("max-budget-usd").value),
    products,
  };
}

function renderRecommendation(recommendation) {
  const rows = recommendation.items
    .map(
      (item) =>
        `<tr><td>${item.name}</td><td>${item.quantity}</td><td>$${item.priceUsd.toFixed(2)}</td><td>${item.weightKg.toFixed(2)} kg</td><td>${item.calories}</td></tr>`
    )
    .join("");
  return `
    <table>
      <thead><tr><th>Product</th><th>Units</th><th>Unit price</th><th>Unit weight</th><th>Unit calories</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
    <p>
      <strong>Total calories:</strong> ${recommendation.totalCalories} —
      <strong>Cost:</strong> $${recommendation.totalCostUsd.toFixed(2)} —
      <strong>Weight:</strong> ${recommendation.totalWeightKg.toFixed(2)} kg
    </p>
  `;
}

async function handleSubmit(event) {
  event.preventDefault();
  solveButton.disabled = true;
  solveButton.textContent = "Solving…";

  try {
    const response = await fetch("/solve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(collectPayload()),
    });

    if (!response.ok) {
      // 422 = Pydantic field-level validation rejected the payload before it
      // ever reached the solver (see schemas.py); show FastAPI's own detail.
      const problem = await response.json();
      resultContent.innerHTML = `<p class="status-failure">Invalid input: ${JSON.stringify(problem.detail)}</p>`;
    } else {
      const body = await response.json();
      if (body.status === "SUCCESS") {
        resultContent.innerHTML =
          `<p class="status-success">Solved.</p>` + renderRecommendation(body.recommendation);
      } else {
        resultContent.innerHTML = `<p class="status-failure">${body.message}</p>`;
      }
    }
  } catch (error) {
    resultContent.innerHTML = `<p class="status-failure">Request failed: ${error}</p>`;
  } finally {
    resultSection.hidden = false;
    solveButton.disabled = false;
    solveButton.textContent = "Solve";
  }
}

form.addEventListener("submit", handleSubmit);

// One pre-filled example row so the form is solvable on first load, without
// requiring the user to already know the product shape.
addProductRow({ name: "banana", priceUsd: 1.0, weightKg: 0.5, calories: 100 });
