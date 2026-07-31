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

// Random-instance generator: lets a user try larger instances (e.g. above
// the 50-product heuristic threshold in Orchestrator._max_products_for_mip)
// without hand-entering rows one at a time.

function randomInRange(min, max, decimals) {
  const value = Math.random() * (max - min) + min;
  return Number(value.toFixed(decimals));
}

function randomIntInRange(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

// Scales the request's maxWeightKg/maxBudgetUsd to a fraction of the
// generated products' totals, so the instance stays solvable and
// non-trivial regardless of how many products were generated.
const GENERATED_LIMIT_FRACTION = 0.5;

function generateRandomProducts(n) {
  productsBody.innerHTML = "";

  let totalWeightKg = 0;
  let totalPriceUsd = 0;
  for (let i = 1; i <= n; i++) {
    const priceUsd = randomInRange(0.5, 10.0, 2);
    const weightKg = randomInRange(0.05, 2.0, 2);
    const calories = randomIntInRange(10, 800);
    totalWeightKg += weightKg;
    totalPriceUsd += priceUsd;
    addProductRow({ name: `product${i}`, priceUsd, weightKg, calories });
  }

  document.getElementById("max-weight-kg").value = (totalWeightKg * GENERATED_LIMIT_FRACTION).toFixed(2);
  document.getElementById("max-budget-usd").value = (totalPriceUsd * GENERATED_LIMIT_FRACTION).toFixed(2);
}

document.getElementById("generate-products").addEventListener("click", () => {
  const generateCountInput = document.getElementById("generate-count");
  // Read the raw string first: Number("") is 0, which would otherwise slip
  // past the range check below instead of being caught as "empty".
  const rawValue = generateCountInput.value;
  const n = Number(rawValue);

  if (rawValue === "" || !Number.isInteger(n) || n < 1 || n > 200) {
    // Same inline error-display pattern handleSubmit uses for /solve errors.
    resultContent.innerHTML = `<p class="status-failure">Invalid input: enter a whole number of products between 1 and 200.</p>`;
    resultSection.hidden = false;
    return;
  }

  generateRandomProducts(n);
});

// Capacity dashboard: reports the *last solved* recommendation, not the
// draft form. It only ever gets new numbers from handleSubmit's SUCCESS
// branch below, so editing the limits or the product rows never moves it.
const capacityCaloriesEl = document.getElementById("capacity-calories");
const gauges = {
  budget: {
    fill: document.getElementById("gauge-budget-fill"),
    value: document.getElementById("gauge-budget-value"),
    pair: (used, limit) => `$${used.toFixed(2)} / $${limit.toFixed(2)}`,
  },
  weight: {
    fill: document.getElementById("gauge-weight-fill"),
    value: document.getElementById("gauge-weight-value"),
    pair: (used, limit) => `${used.toFixed(2)} / ${limit.toFixed(2)} kg`,
  },
};

function setGauge(gauge, used, limit) {
  // A successful Recommendation can never exceed its own request's limit
  // (see domain/recommendation.py's __post_init__ check), so used/limit is
  // always <= 1 here; the cap is just a guard against float rounding at
  // exactly 100%.
  const percent = limit > 0 ? Math.min((used / limit) * 100, 100) : 0;
  gauge.fill.style.width = `${percent}%`;
  gauge.value.textContent = gauge.pair(used, limit);
}

function updateCapacityDashboard(recommendation, limits) {
  capacityCaloriesEl.textContent = `${recommendation.totalCalories} kcal`;
  setGauge(gauges.budget, recommendation.totalCostUsd, limits.maxBudgetUsd);
  setGauge(gauges.weight, recommendation.totalWeightKg, limits.maxWeightKg);
}

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
    .map((item) => {
      const totalCost = item.priceUsd * item.quantity;
      const totalWeight = item.weightKg * item.quantity;
      const totalCalories = item.calories * item.quantity;
      return `<tr><td>${item.name}</td><td>${item.quantity}</td><td>$${totalCost.toFixed(2)}</td><td>${totalWeight.toFixed(2)} kg</td><td>${totalCalories}</td></tr>`;
    })
    .join("");
  return `
    <table>
      <thead><tr><th>Product</th><th>Units</th><th>Total cost</th><th>Total weight</th><th>Total calories</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

async function handleSubmit(event) {
  event.preventDefault();
  solveButton.disabled = true;
  solveButton.textContent = "Solving…";

  try {
    const payload = collectPayload();
    const response = await fetch("/solve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
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
        updateCapacityDashboard(body.recommendation, payload);
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
