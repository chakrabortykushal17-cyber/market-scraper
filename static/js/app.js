// TradingEconomics Dashboard Frontend Interactivity

document.addEventListener("DOMContentLoaded", () => {
  let currentType = "all";
  let currentCategory = "all";
  let currentSearch = "";
  let currentSort = "change_percent_desc";
  let rawData = [];
  let gainersChartInstance = null;
  let losersChartInstance = null;

  const tableBody = document.getElementById("table-body");
  const marketTable = document.getElementById("market-table");
  const loadingEl = document.getElementById("loading");
  const lastUpdatedEl = document.getElementById("last-updated");
  const searchInput = document.getElementById("search-input");
  const selectCategory = document.getElementById("select-category");
  const selectSort = document.getElementById("select-sort");
  const categoryPillsContainer = document.getElementById("category-pills");
  const btnForceRefresh = document.getElementById("btn-force-refresh");
  const btnExport = document.getElementById("btn-export-menu");

  // Fetch summary and populate metrics
  async function fetchSummary(force = false) {
    try {
      const res = await fetch(`/api/summary?type=${currentType}&force_refresh=${force}`);
      const json = await res.json();
      if (json.success && json.summary) {
        const s = json.summary;
        document.getElementById("metric-total").textContent = s.total_items || 0;
        
        if (s.top_gainer) {
          document.getElementById("metric-gainer-name").textContent = s.top_gainer.name;
          document.getElementById("metric-gainer-val").textContent = `+${s.top_gainer.change_percent.toFixed(2)}% (${s.top_gainer.category})`;
        }
        
        if (s.top_loser) {
          document.getElementById("metric-loser-name").textContent = s.top_loser.name;
          document.getElementById("metric-loser-val").textContent = `${s.top_loser.change_percent.toFixed(2)}% (${s.top_loser.category})`;
        }

        const sentiment = s.gainers_count > s.losers_count ? "Bullish 🐂" : "Bearish 🐻";
        document.getElementById("metric-sentiment").textContent = sentiment;
        document.getElementById("metric-ratio").textContent = `${s.gainers_count} Gainers / ${s.losers_count} Losers`;
      }
    } catch (err) {
      console.error("Failed to fetch summary:", err);
    }
  }

  // Fetch categories to populate dropdown & pills
  async function fetchCategories() {
    try {
      const res = await fetch("/api/categories");
      const json = await res.json();
      if (json.success && json.categories) {
        selectCategory.innerHTML = '<option value="all">All Categories</option>';
        categoryPillsContainer.innerHTML = '<div class="pill active" data-cat="all">All Categories</div>';

        json.categories.forEach(cat => {
          // Dropdown option
          const opt = document.createElement("option");
          opt.value = cat.toLowerCase();
          opt.textContent = cat;
          selectCategory.appendChild(opt);

          // Pill
          const pill = document.createElement("div");
          pill.className = "pill";
          pill.dataset.cat = cat.toLowerCase();
          pill.textContent = cat;
          categoryPillsContainer.appendChild(pill);
        });

        // Pill click listener
        categoryPillsContainer.querySelectorAll(".pill").forEach(pill => {
          pill.addEventListener("click", () => {
            categoryPillsContainer.querySelectorAll(".pill").forEach(p => p.classList.remove("active"));
            pill.classList.add("active");
            currentCategory = pill.dataset.cat;
            selectCategory.value = currentCategory;
            renderTable();
          });
        });
      }
    } catch (err) {
      console.error("Failed to fetch categories:", err);
    }
  }

  // Main data fetch
  async function fetchData(force = false) {
    loadingEl.style.display = "block";
    marketTable.style.display = "none";

    try {
      const res = await fetch(`/api/data?type=${currentType}&force_refresh=${force}`);
      const json = await res.json();

      if (json.success) {
        rawData = json.data;
        const scrapedDate = new Date(json.scraped_at);
        lastUpdatedEl.textContent = `Updated: ${scrapedDate.toLocaleTimeString()}`;
        renderTable();
        updateCharts();
      }
    } catch (err) {
      console.error("Error fetching data:", err);
      loadingEl.textContent = "⚠️ Failed to scrape data. Click 'Refresh Scraper' to try again.";
    } finally {
      loadingEl.style.display = "none";
      marketTable.style.display = "table";
    }
  }

  function formatPct(val) {
    if (val === null || val === undefined) return '<span class="badge badge-neutral">N/A</span>';
    const formatted = val > 0 ? `+${val.toFixed(2)}%` : `${val.toFixed(2)}%`;
    const badgeClass = val > 0 ? "badge-positive" : val < 0 ? "badge-negative" : "badge-neutral";
    return `<span class="badge ${badgeClass}">${formatted}</span>`;
  }

  function renderTable() {
    let filtered = [...rawData];

    // Category filter
    if (currentCategory !== "all") {
      filtered = filtered.filter(item => item.category.toLowerCase() === currentCategory);
    }

    // Search filter
    if (currentSearch) {
      filtered = filtered.filter(item => 
        item.name.toLowerCase().includes(currentSearch) ||
        item.category.toLowerCase().includes(currentSearch) ||
        (item.unit && item.unit.toLowerCase().includes(currentSearch))
      );
    }

    // Sort logic
    const [sortField, sortDir] = currentSort.split("_");
    const isDesc = sortDir === "desc" || currentSort.endsWith("desc");

    filtered.sort((a, b) => {
      let valA = a[sortField];
      let valB = b[sortField];

      if (valA === null || valA === undefined) return 1;
      if (valB === null || valB === undefined) return -1;

      if (typeof valA === "string") {
        return isDesc ? valB.localeCompare(valA) : valA.localeCompare(valB);
      }
      return isDesc ? valB - valA : valA - valB;
    });

    // Render HTML rows
    tableBody.innerHTML = "";
    if (filtered.length === 0) {
      tableBody.innerHTML = `<tr><td colspan="11" style="text-align: center; padding: 40px; color: var(--text-muted);">No matching instruments found.</td></tr>`;
      return;
    }

    filtered.forEach(item => {
      const tr = document.createElement("tr");

      const tagClass = item.type === "stock" ? "tag-stock" : "tag-commodity";
      const unitText = item.unit ? `<small style="color: var(--text-muted); display: block; font-size: 0.75rem;">${item.unit}</small>` : "";

      tr.innerHTML = `
        <td><span class="${tagClass}">${item.type.toUpperCase()}</span></td>
        <td><strong style="color: var(--text-main);">${item.category}</strong></td>
        <td>
          <strong style="font-size: 0.95rem;">${item.name}</strong>
          ${unitText}
        </td>
        <td><strong>${item.price !== null ? item.price.toLocaleString(undefined, {minimumFractionDigits: 2}) : 'N/A'}</strong></td>
        <td style="color: ${item.change > 0 ? 'var(--success)' : item.change < 0 ? 'var(--danger)' : 'var(--text-muted)'}">
          ${item.change !== null ? (item.change > 0 ? '+' + item.change : item.change) : 'N/A'}
        </td>
        <td>${formatPct(item.change_percent)}</td>
        <td>${formatPct(item.weekly_percent)}</td>
        <td>${formatPct(item.monthly_percent)}</td>
        <td>${formatPct(item.ytd_percent)}</td>
        <td><span style="color: var(--text-muted);">${item.date || ''}</span></td>
        <td><a href="${item.url}" target="_blank" rel="noopener" class="external-link" title="Open on TradingEconomics">🔗 View</a></td>
      `;

      tableBody.appendChild(tr);
    });
  }

  function updateCharts() {
    const valid = rawData.filter(d => d.change_percent !== null && d.change_percent !== undefined);

    const sortedGainers = [...valid].sort((a, b) => b.change_percent - a.change_percent).slice(0, 7);
    const sortedLosers = [...valid].sort((a, b) => a.change_percent - b.change_percent).slice(0, 7);

    // Gainers Chart
    const ctxG = document.getElementById("gainersChart").getContext("2d");
    if (gainersChartInstance) gainersChartInstance.destroy();

    gainersChartInstance = new Chart(ctxG, {
      type: "bar",
      data: {
        labels: sortedGainers.map(d => d.name),
        datasets: [{
          label: "% Change",
          data: sortedGainers.map(d => d.change_percent),
          backgroundColor: "#10b981",
          borderRadius: 6
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          y: { grid: { color: "rgba(255,255,255,0.05)" }, ticks: { color: "#94a3b8" } },
          x: { grid: { display: false }, ticks: { color: "#f8fafc" } }
        }
      }
    });

    // Losers Chart
    const ctxL = document.getElementById("losersChart").getContext("2d");
    if (losersChartInstance) losersChartInstance.destroy();

    losersChartInstance = new Chart(ctxL, {
      type: "bar",
      data: {
        labels: sortedLosers.map(d => d.name),
        datasets: [{
          label: "% Change",
          data: sortedLosers.map(d => d.change_percent),
          backgroundColor: "#f43f5e",
          borderRadius: 6
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          y: { grid: { color: "rgba(255,255,255,0.05)" }, ticks: { color: "#94a3b8" } },
          x: { grid: { display: false }, ticks: { color: "#f8fafc" } }
        }
      }
    });
  }

  // Event Handlers
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      currentType = btn.dataset.type;
      fetchData();
      fetchSummary();
    });
  });

  searchInput.addEventListener("input", (e) => {
    currentSearch = e.target.value.toLowerCase().trim();
    renderTable();
  });

  selectCategory.addEventListener("change", (e) => {
    currentCategory = e.target.value;
    categoryPillsContainer.querySelectorAll(".pill").forEach(p => {
      p.classList.toggle("active", p.dataset.cat === currentCategory);
    });
    renderTable();
  });

  selectSort.addEventListener("change", (e) => {
    currentSort = e.target.value;
    renderTable();
  });

  const autoRefreshTimerEl = document.getElementById("auto-refresh-timer");
  let countdown = 15;

  function startCountdown() {
    setInterval(() => {
      countdown--;
      if (countdown <= 0) {
        if (autoRefreshTimerEl) autoRefreshTimerEl.textContent = "⚡ Updating live...";
        fetchData(true);
        fetchSummary(true);
        countdown = 15;
      } else {
        if (autoRefreshTimerEl) autoRefreshTimerEl.textContent = `⚡ Auto-updating in ${countdown}s`;
      }
    }, 1000);
  }

  btnForceRefresh.addEventListener("click", () => {
    countdown = 15;
    if (autoRefreshTimerEl) autoRefreshTimerEl.textContent = "⚡ Updating live...";
    fetchData(true);
    fetchSummary(true);
  });

  btnExport.addEventListener("click", () => {
    window.location.href = `/api/export?type=${currentType}&format=csv`;
  });

  // Auto-Start PC Integration
  const btnAutoStart = document.getElementById("btn-autostart");
  let autoStartEnabled = false;

  async function checkAutoStartStatus() {
    try {
      const res = await fetch("/api/autostart");
      const json = await res.json();
      if (json.success && json.status) {
        autoStartEnabled = json.status.enabled;
        updateAutoStartButtonUI();
      }
    } catch (err) {
      console.error("Failed to check autostart status:", err);
      if (btnAutoStart) btnAutoStart.textContent = "⚙️ Auto-Start: N/A";
    }
  }

  function updateAutoStartButtonUI() {
    if (!btnAutoStart) return;
    if (autoStartEnabled) {
      btnAutoStart.textContent = "⚡ PC Auto-Start: ON";
      btnAutoStart.style.borderColor = "var(--success)";
      btnAutoStart.style.color = "var(--success)";
    } else {
      btnAutoStart.textContent = "💤 PC Auto-Start: OFF";
      btnAutoStart.style.borderColor = "#94a3b8";
      btnAutoStart.style.color = "#94a3b8";
    }
  }

  if (btnAutoStart) {
    btnAutoStart.addEventListener("click", async () => {
      const newAction = autoStartEnabled ? "disable" : "enable";
      btnAutoStart.textContent = "⚙️ Saving...";
      try {
        const res = await fetch("/api/autostart", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: newAction, target: "scraper" })
        });
        const json = await res.json();
        if (json.status) {
          autoStartEnabled = json.status.enabled;
        }
        alert(json.message);
      } catch (err) {
        alert("Error connecting to server to update Auto-Start setting.");
      } finally {
        updateAutoStartButtonUI();
      }
    });
  }

  // Initial loads
  fetchCategories();
  fetchSummary();
  fetchData();
  checkAutoStartStatus();
  startCountdown();
});

