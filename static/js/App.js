const CURRENCY = "₹"; // change to "$", "€", etc.

const $ = (id) => document.getElementById(id);
const money = (n) =>
  CURRENCY + Number(n).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const COLORS = ["#6c7bff", "#38d6b0", "#ffb86b", "#ff6b81", "#b38cff", "#5ec8ff", "#ffd96b", "#8fe388"];
let categoryChart = null;
let monthChart = null;

const hasChart = typeof Chart !== "undefined";
if (hasChart) {
  Chart.defaults.color = "#8f9bb3";
  Chart.defaults.borderColor = "#263049";
}

/* ---------- helpers ---------- */


async function api(url, options = {}) {
  const method = (options.method || "GET").toUpperCase();
  const headers = new Headers(options.headers || {});

  if (["POST", "PUT", "PATCH", "DELETE"].includes(method)) {
    const csrfToken = document.querySelector(
      'meta[name="csrf-token"]'
    )?.content;

    if (!csrfToken) {
      throw new Error("Security token missing. Refresh the page and try again.");
    }

    headers.set("X-CSRF-Token", csrfToken);
  }

  const res = await fetch(url, {
    ...options,
    method,
    headers,
  });

  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    throw new Error(data.error || "Something went wrong.");
  }

  return data;
}


function toast(message, isError = false) {
  const el = $("toast");
  el.textContent = message;
  el.className = "toast show" + (isError ? " error" : "");
  setTimeout(() => (el.className = "toast"), 2500);
}

function debounce(fn, delay = 300) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

/* ---------- rendering ---------- */

function renderTable(expenses) {
  const body = $("expense-body");
  body.innerHTML = "";
  $("empty").classList.toggle("hidden", expenses.length > 0);

  expenses.forEach((e) => {
    const tr = document.createElement("tr");

    const date = document.createElement("td");
    date.textContent = e.date;

    const catCell = document.createElement("td");
    const badge = document.createElement("span");
    badge.className = "badge";
    badge.textContent = e.category;
    catCell.appendChild(badge);

    const desc = document.createElement("td");
    desc.textContent = e.description || "-";

    const amount = document.createElement("td");
    amount.className = "right";
    amount.textContent = money(e.amount);

    const actions = document.createElement("td");
    actions.className = "right";
    const del = document.createElement("button");
    del.className = "delete-btn";
    del.title = "Delete";
    del.textContent = "🗑";
    del.addEventListener("click", () => deleteExpense(e.id));
    actions.appendChild(del);

    tr.append(date, catCell, desc, amount, actions);
    body.appendChild(tr);
  });
}

function renderCharts(summary) {
  if (!hasChart) return; // <- add this line 
  if (categoryChart) categoryChart.destroy();
  if (monthChart) monthChart.destroy();

  categoryChart = new Chart($("category-chart"), {
    type: "doughnut",
    data: {
      labels: summary.categories.map((c) => c.category),
      datasets: [{
        data: summary.categories.map((c) => c.total),
        backgroundColor: COLORS,
        borderWidth: 0,
      }],
    },
    options: {
      maintainAspectRatio: false,
      cutout: "65%",
      plugins: { legend: { position: "bottom", labels: { boxWidth: 12 } } },
    },
  });

  monthChart = new Chart($("month-chart"), {
    type: "bar",
    data: {
      labels: summary.months.map((m) => m.month),
      datasets: [{
        data: summary.months.map((m) => m.total),
        backgroundColor: "#6c7bff",
        borderRadius: 6,
      }],
    },
    options: {
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true } },
    },
  });
}

function renderCategoryFilter(categories) {
  const select = $("filter-category");
  const current = select.value;
  select.innerHTML = '<option value="">All categories</option>';
  categories.forEach((c) => {
    const opt = document.createElement("option");
    opt.value = c.category;
    opt.textContent = c.category;
    select.appendChild(opt);
  });
  select.value = current;
}

/* ---------- data loading ---------- */

async function loadExpenses() {
  const params = new URLSearchParams({
    search: $("search").value,
    category: $("filter-category").value,
  });
  renderTable(await api("/api/expenses?" + params));
}

async function loadSummary() {
  const summary = await api("/api/summary");
  $("stat-total").textContent = money(summary.total);
  $("stat-month").textContent = money(summary.this_month);
  $("stat-count").textContent = summary.count;
  $("stat-top").textContent = summary.top_category;
  renderCharts(summary);
  renderCategoryFilter(summary.categories);
}

async function refresh() {
  try {
    await Promise.all([loadSummary(), loadExpenses()]);
  } catch (err) {
    toast(err.message, true);
  }
}

/* ---------- actions ---------- */

async function deleteExpense(id) {
  if (!confirm("Delete this expense?")) return;
  try {
    await api("/api/expenses/" + id, { method: "DELETE" });
    toast("Expense deleted");
    refresh();
  } catch (err) {
    toast(err.message, true);
  }
}

$("expense-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = {
    date: $("date").value,
    category: $("category").value,
    description: $("description").value,
    amount: $("amount").value,
  };

  try {
    await api("/api/expenses", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    event.target.reset();
    $("date").value = today();
    toast("Expense added ✅");
    refresh();
  } catch (err) {
    toast(err.message, true);
  }
});

$("search").addEventListener("input", debounce(loadExpenses));
$("filter-category").addEventListener("change", loadExpenses);

/* ---------- start ---------- */

const today = () => new Date().toLocaleDateString("en-CA"); // YYYY-MM-DD in local time
$("date").value = today();
refresh();