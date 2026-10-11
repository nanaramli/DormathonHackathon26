/* ===== State ===== */
let selectedFiles = [];
let loadedFileInfo = null;
let chartInstances = {};
let currentPanel = "home";

/* ===== DOM ===== */
const $ = (id) => document.getElementById(id);
const uploadZone = $("uploadZone");
const fileInput = $("fileInput");
const loadedFilesInfo = $("loadedFilesInfo");
const dataSummaryBox = $("dataSummaryBox");
const statusPill = $("statusPill");
const statusText = $("statusText");
const instructionInput = $("instructionInput");
const analyzeBtn = $("analyzeBtn");
const loadingBar = $("loadingBar");
const loadingSub = $("loadingSub");
const resultsSection = $("panel-results");
const toastContainer = $("toastContainer");
const resetBtn = $("resetBtn");
const menuToggle = $("menuToggle");
const sidebar = $("sidebar");
const sidebarOverlay = $("sidebarOverlay");
const topbarTitle = $("topbarTitle");
const scrollProgress = $("scrollProgress");
const tabsBar = $("tabsBar");

/* ===== Init ===== */
document.addEventListener("DOMContentLoaded", () => {
    setupUploadZone();
    setupAnalyzeButton();
    setupSidebar();
    setupTabs();
    setupScrollProgress();
    updateAnalyzeButton();
});

/* ===== Sidebar ===== */
function setupSidebar() {
    document.querySelectorAll(".nav-item").forEach((item) => {
        item.addEventListener("click", (e) => {
            if (item.classList.contains("disabled")) {
                e.preventDefault();
                return;
            }
            const panel = item.dataset.panel;
            switchPanel(panel);
        });
    });

    menuToggle.addEventListener("click", () => {
        sidebar.classList.add("open");
        sidebarOverlay.classList.add("show");
    });

    sidebarOverlay.addEventListener("click", () => {
        sidebar.classList.remove("open");
        sidebarOverlay.classList.remove("show");
    });
}

function switchPanel(panelId) {
    document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
    $("panel-" + panelId).classList.add("active");

    document.querySelectorAll(".nav-item").forEach((n) => {
        n.classList.remove("active");
        if (n.dataset.panel === panelId) n.classList.add("active");
    });

    const titles = { home: "Start", results: "Results" };
    topbarTitle.textContent = titles[panelId] || "Dashboard";
    currentPanel = panelId;

    window.scrollTo({ top: 0, behavior: "smooth" });

    if (window.innerWidth <= 900) {
        sidebar.classList.remove("open");
        sidebarOverlay.classList.remove("show");
    }
}

function enableNav(panelId) {
    const nav = document.querySelector(`.nav-item[data-panel="${panelId}"]`);
    if (nav) nav.classList.remove("disabled");
}

/* ===== Tabs ===== */
function setupTabs() {
    document.querySelectorAll(".tab").forEach((tab) => {
        tab.addEventListener("click", () => {
            const target = tab.dataset.tab;
            document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
            document.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));
            tab.classList.add("active");
            $("tab-" + target).classList.add("active");
        });
    });
}

/* ===== Scroll Progress ===== */
function setupScrollProgress() {
    window.addEventListener("scroll", () => {
        const scrollable = document.documentElement.scrollHeight - window.innerHeight;
        const pct = scrollable > 0 ? (window.scrollY / scrollable) * 100 : 0;
        scrollProgress.style.width = pct + "%";
    });
}

/* ===== Upload Zone ===== */
function setupUploadZone() {
    uploadZone.addEventListener("click", () => fileInput.click());

    fileInput.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
            selectedFiles = Array.from(e.target.files);
            handleFilesLoaded();
        }
    });

    uploadZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        uploadZone.classList.add("dragover");
    });

    uploadZone.addEventListener("dragleave", () => uploadZone.classList.remove("dragover"));

    uploadZone.addEventListener("drop", (e) => {
        e.preventDefault();
        uploadZone.classList.remove("dragover");
        if (e.dataTransfer.files.length > 0) {
            selectedFiles = Array.from(e.dataTransfer.files);
            fileInput.files = e.dataTransfer.files;
            handleFilesLoaded();
        }
    });
}

/* ===== Handle Files ===== */
function handleFilesLoaded() {
    if (selectedFiles.length === 0) return;

    let html = '<h4>&#9989; Files Ready</h4>';
    selectedFiles.forEach((f, i) => {
        const ext = f.name.split(".").pop().toLowerCase();
        html += `<div class="file-chip">
            <span class="file-ext-badge ${ext}">${ext}</span>
            <span class="file-name">${escapeHtml(f.name)}</span>
            <span class="file-size">${formatBytes(f.size)}</span>
            <button class="file-remove" data-idx="${i}" title="Remove">
                <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
        </div>`;
    });
    loadedFilesInfo.innerHTML = html;
    loadedFilesInfo.style.display = "block";
    dataSummaryBox.style.display = "none";

    loadedFilesInfo.querySelectorAll(".file-remove").forEach((btn) => {
        btn.addEventListener("click", (e) => {
            e.stopPropagation();
            const idx = parseInt(btn.dataset.idx);
            selectedFiles.splice(idx, 1);
            if (selectedFiles.length === 0) {
                loadedFilesInfo.style.display = "none";
            } else {
                handleFilesLoaded();
            }
            updateAnalyzeButton();
        });
    });

    updateStatus("ok", `${selectedFiles.length} file${selectedFiles.length > 1 ? "s" : ""} ready`);
    resetBtn.style.display = "flex";
    updateAnalyzeButton();
}

/* ===== Data Summary ===== */
function renderDataSummary(data, sourceLabel) {
    const s = data.summary || {};
    let tags = "";
    if (s.income_categories && s.income_categories.length) tags += `<span class="tag tag-income">Income: ${s.income_categories.join(", ")}</span>`;
    if (s.expense_categories && s.expense_categories.length) tags += `<span class="tag tag-expense">Expense: ${s.expense_categories.join(", ")}</span>`;
    if (s.invoice_statuses && s.invoice_statuses.length) tags += `<span class="tag tag-status">Status: ${s.invoice_statuses.join(", ")}</span>`;

    let fileSummaryHtml = "";
    if (data.file_summaries && data.file_summaries.length) {
        fileSummaryHtml = '<div style="margin-bottom:16px;display:flex;flex-direction:column;gap:6px;">';
        data.file_summaries.forEach((f) => {
            fileSummaryHtml += `<div class="file-chip">
                <span class="file-ext-badge ${f.detected_as === 'invoices' ? 'csv' : 'xlsx'}">${f.format || f.detected_as}</span>
                <span class="file-name">${escapeHtml(f.filename)}</span>
                <span class="file-size">${f.row_count} rows</span>
            </div>`;
        });
        fileSummaryHtml += '</div>';
    }

    let notesHtml = "";
    if (data.adaptation_notes && data.adaptation_notes.length) {
        notesHtml = `<div class="adaptation-notes-box">
            <strong>Adaptation Notes</strong>
            <ul>${data.adaptation_notes.map((n) => `<li>${escapeHtml(n)}</li>`).join("")}</ul>
        </div>`;
    }

    dataSummaryBox.innerHTML = `
        ${fileSummaryHtml}
        <div class="summary-grid">
            <div class="summary-item"><div class="value">${data.invoice_count || 0}</div><div class="label">Invoices</div></div>
            <div class="summary-item"><div class="value">${data.transaction_count || 0}</div><div class="label">Transactions</div></div>
            <div class="summary-item"><div class="value">${s.income_transaction_count || 0}</div><div class="label">Income</div></div>
            <div class="summary-item"><div class="value">${s.expense_transaction_count || 0}</div><div class="label">Expenses</div></div>
        </div>
        <div class="summary-tags">${tags}</div>
        ${notesHtml}
    `;
    dataSummaryBox.style.display = "block";
}

/* ===== Analyze Button Enable/Disable ===== */
function updateAnalyzeButton() {
    const hasPrompt = instructionInput.value.trim().length > 0;
    const hasData = selectedFiles.length > 0;
    analyzeBtn.disabled = !(hasPrompt && hasData);
}

/* ===== Run Analysis ===== */
function setupAnalyzeButton() {
    analyzeBtn.addEventListener("click", () => runAnalysis());
    instructionInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !analyzeBtn.disabled) runAnalysis();
    });
    instructionInput.addEventListener("input", () => updateAnalyzeButton());

    resetBtn.addEventListener("click", () => {
        selectedFiles = [];
        loadedFileInfo = null;
        fileInput.value = "";
        instructionInput.value = "";
        loadedFilesInfo.style.display = "none";
        dataSummaryBox.style.display = "none";
        resultsSection.querySelector(".kpi-grid").innerHTML = "";
        resultsSection.querySelector("#chartsGrid").innerHTML = "";
        resultsSection.querySelector("#tablesSection").innerHTML = "";
        updateStatus("", "No data loaded");
        document.querySelectorAll(".nav-item").forEach((n) => {
            if (n.dataset.panel !== "home") n.classList.add("disabled");
        });
        resetBtn.style.display = "none";
        switchPanel("home");
        updateAnalyzeButton();
        showToast("Ready for new data.", "info");
    });
}

async function runAnalysis() {
    const instruction = instructionInput.value.trim();
    if (!instruction) {
        showToast("Please type what you need.", "error");
        return;
    }
    if (selectedFiles.length === 0) {
        showToast("Upload files first.", "error");
        return;
    }

    loadingBar.style.display = "flex";
    analyzeBtn.disabled = true;
    loadingSub.textContent = "Running analysis pipeline...";

    const formData = new FormData();
    formData.append("instruction", instruction);
    formData.append("use_sample", "false");
    selectedFiles.forEach((f) => formData.append("files", f));

    try {
        const resp = await fetch("/api/analyze", { method: "POST", body: formData });
        const data = await resp.json();

        if (!resp.ok) {
            showToast(data.error || "Analysis failed", "error");
            return;
        }

        if (data.adaptation_notes && data.adaptation_notes.length) {
            loadedFileInfo = {
                invoice_count: data.dataset_summary?.invoice_count || 0,
                transaction_count: data.dataset_summary?.transaction_count || 0,
                summary: data.dataset_summary,
                adaptation_notes: data.adaptation_notes,
            };
        }

        renderResults(data);
        showToast("Analysis complete!", "success");
    } catch (e) {
        showToast("Network error: " + e.message, "error");
    } finally {
        loadingBar.style.display = "none";
        analyzeBtn.disabled = false;
    }
}

/* ===== Render Results ===== */
function renderResults(result) {
    Object.values(chartInstances).forEach((c) => c.destroy());
    chartInstances = {};

    enableNav("results");

    renderPipelineProgress(result);
    renderKPIs(result.findings || {});
    renderRecommendations(result.actions || []);
    renderCharts(result.findings || {});
    renderTables(result.findings || {});
    renderInsights(result.smart_insights || []);
    renderDataNotes(result.data_notes || []);
    renderOutputFiles(result);

    const hasReconciliation = result.findings?.reconciliation;
    const hasCustomerMessages = result.findings?.customer_messages;

    if (hasReconciliation) {
        renderReconciliation(result.findings.reconciliation);
    }
    if (hasCustomerMessages) {
        renderCustomerMessages(result.findings.customer_messages);
    }

    tabsBar.style.display = "flex";

    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));
    document.querySelector('.tab[data-tab="charts"]').classList.add("active");
    $("tab-charts").classList.add("active");

    switchPanel("results");
}

/* ===== Smart Plan Banner (REMOVED per user request) ===== */
// renderSmartPlanBanner function removed — GOAL DETERMINED card no longer shows on Results page.

/* ===== Pipeline Progress ===== */
function renderPipelineProgress(result) {
    const el = $("pipelineProgress");
    const steps = result.pipeline_steps;
    if (!steps || steps.length === 0) {
        el.style.display = "none";
        return;
    }

    const stepsHtml = steps.map((s, i) => {
        const delay = i * 0.1;
        return `<div class="pp-step ${s.status}" style="animation: panelIn 0.3s ease ${delay}s both;">
            <div class="pp-step-icon">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5">
                    <polyline points="20 6 9 17 4 12"/>
                </svg>
            </div>
            <div class="pp-step-body">
                <div class="pp-step-name">${esc(s.name)}</div>
                <div class="pp-step-detail">${esc(s.detail)}</div>
            </div>
        </div>`;
    }).join("");

    el.innerHTML = `<div class="pp-track">${stepsHtml}</div>`;
    el.style.display = "block";
}

/* ===== Smart Insights ===== */
function renderInsights(insights) {
    const list = $("insightsList");
    const badge = $("tabBadgeInsights");

    if (!insights || insights.length === 0) {
        badge.style.display = "none";
        list.innerHTML = '<p style="color:var(--text-3);font-size:14px;padding:20px;">No insights for this analysis.</p>';
        return;
    }

    badge.style.display = "inline-flex";
    badge.textContent = insights.length;

    list.innerHTML = insights.map((ins, i) => {
        const colorMap = {1: "var(--danger)", 2: "var(--warning)", 3: "var(--success)"};
        const labelMap = {1: "Critical", 2: "Important", 3: "Good"};
        const color = colorMap[ins.priority] || "var(--primary)";
        const label = labelMap[ins.priority] || "Info";

        return `<div class="insight-card priority-${ins.priority}" style="animation: panelIn 0.4s ease ${i * 0.08}s both;">
            <div class="insight-header">
                <span class="insight-badge" style="background:${color};">${label}</span>
                <span class="insight-category">${esc(ins.category)}</span>
            </div>
            <div class="insight-title">${esc(ins.title)}</div>
            <div class="insight-section">
                <div class="insight-label">Finding</div>
                <div class="insight-text">${esc(ins.finding)}</div>
            </div>
            <div class="insight-section">
                <div class="insight-label">Recommendation</div>
                <div class="insight-text">${esc(ins.recommendation)}</div>
            </div>
            <div class="insight-section">
                <div class="insight-label">Why It Matters</div>
                <div class="insight-text insight-rationale">${esc(ins.rationale)}</div>
            </div>
        </div>`;
    }).join("");
}

/* ===== KPI Cards ===== */
function renderKPIs(findings) {
    const grid = $("kpiGrid");
    const cards = [];

    if (findings.net_profit) {
        const np = findings.net_profit;
        const profitClass = np.net_profit >= 0 ? "kpi-positive" : "kpi-negative";
        cards.push(kpiCard("Total Revenue", np.total_revenue, "All income transactions", "kpi-neutral"));
        cards.push(kpiCard("Total Expenses", np.total_expenses, "All expense transactions", "kpi-negative"));
        cards.push(kpiCard("Net Profit", np.net_profit, `${np.profit_margin_pct}% margin`, profitClass));
    }
    if (findings.outstanding) {
        const out = findings.outstanding;
        cards.push(kpiCard("Outstanding", out.total_outstanding,
            out.overdue_amount > 0 ? fmtRM(out.overdue_amount) + " overdue" : "No overdue",
            out.total_outstanding > 0 ? "kpi-negative" : "kpi-positive"));
        cards.push(kpiCard("Collection Rate", out.collection_rate_pct + "%",
            "Paid vs invoiced", out.collection_rate_pct >= 80 ? "kpi-positive" : "kpi-negative", true));
    }
    if (findings.profit_by_category) {
        const pbc = findings.profit_by_category;
        cards.push(kpiCard("Est. Total Profit", pbc.total_profit,
            `Across ${pbc.categories.length} categories`,
            pbc.total_profit >= 0 ? "kpi-positive" : "kpi-negative"));
    }
    if (findings.expense_ratio) {
        const er = findings.expense_ratio;
        cards.push(kpiCard("Expense Ratio", er.expense_ratio_pct + "%",
            `Top: ${er.top_expense_category}`, "kpi-neutral"));
    }
    if (findings.regional_analysis) {
        const ra = findings.regional_analysis;
        cards.push(kpiCard("Regions", ra.total_regions, `Best: ${ra.best_region}`, "kpi-neutral"));
    }
    if (findings.revenue_concentration) {
        const rc = findings.revenue_concentration;
        cards.push(kpiCard("Top Category Share", rc.top_category_share_pct + "%",
            rc.is_concentrated ? "High concentration risk" : "Well diversified",
            rc.is_concentrated ? "kpi-negative" : "kpi-positive"));
    }

    // Data Quality KPI
    if (findings.data_quality) {
        const dq = findings.data_quality;
        const dqClass = dq.score >= 75 ? "kpi-positive" : dq.score >= 60 ? "kpi-neutral" : "kpi-negative";
        cards.push(kpiCard("Data Quality", dq.score + "/100",
            `Grade ${dq.grade} — ${dq.issues?.length || 0} issue(s)`, dqClass));
    }

    grid.innerHTML = cards.join("");

    grid.querySelectorAll("[data-counter]").forEach((el) => {
        animateCounter(el, parseFloat(el.dataset.counter), el.dataset.prefix || "");
    });
}

function kpiCard(label, value, sub, valueClass, isNumeric) {
    if (isNumeric) {
        return `<div class="kpi-card">
            <div class="kpi-label">${label}</div>
            <div class="kpi-value ${valueClass}" data-counter="${value}" data-prefix="">0%</div>
            <div class="kpi-sub">${sub}</div>
        </div>`;
    }
    return `<div class="kpi-card">
        <div class="kpi-label">${label}</div>
        <div class="kpi-value ${valueClass}">${fmtRM(value)}</div>
        <div class="kpi-sub">${sub}</div>
    </div>`;
}

/* ===== Animated Counter ===== */
function animateCounter(el, target, prefix) {
    const duration = 800;
    const start = performance.now();
    function tick(now) {
        const elapsed = now - start;
        const t = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - t, 3);
        const val = Math.round(target * eased * 10) / 10;
        el.textContent = val.toFixed(1) + "%";
        if (t < 1) requestAnimationFrame(tick);
        else el.textContent = target + "%";
    }
    requestAnimationFrame(tick);
}

/* ===== Charts ===== */
function renderCharts(findings) {
    const grid = $("chartsGrid");
    const charts = [];

    if (findings.monthly_trends && findings.monthly_trends.months && findings.monthly_trends.months.length > 0) {
        const mt = findings.monthly_trends;
        charts.push({
            title: "Monthly Income vs Expenses",
            canvasId: "chartMonthly",
            render: () => {
                chartInstances["chartMonthly"] = new Chart($("chartMonthly"), {
                    type: "bar",
                    data: {
                        labels: mt.months,
                        datasets: [
                            { label: "Income", data: mt.months.map((m) => mt.income_by_month[m] || 0),
                              backgroundColor: "rgba(5,150,105,0.7)", borderColor: "rgba(5,150,105,1)", borderWidth: 1, borderRadius: 4 },
                            { label: "Expenses", data: mt.months.map((m) => mt.expense_by_month[m] || 0),
                              backgroundColor: "rgba(220,38,38,0.7)", borderColor: "rgba(220,38,38,1)", borderWidth: 1, borderRadius: 4 },
                        ],
                    },
                    options: chartOpts(true, true),
                });
            },
        });
    }

    if (findings.revenue_by_category && findings.revenue_by_category.by_category) {
        const rbc = findings.revenue_by_category;
        const cats = Object.keys(rbc.by_category);
        if (cats.length > 0) {
            charts.push({
                title: "Revenue by Category",
                canvasId: "chartRevenue",
                render: () => {
                    chartInstances["chartRevenue"] = new Chart($("chartRevenue"), {
                        type: "doughnut",
                        data: { labels: cats, datasets: [{ data: cats.map((c) => rbc.by_category[c]), backgroundColor: palette(cats.length), borderWidth: 3, borderColor: "#fff" }] },
                        options: doughnutOpts(),
                    });
                },
            });
        }
    }

    if (findings.expense_by_category && findings.expense_by_category.by_category) {
        const ebc = findings.expense_by_category;
        const cats = Object.keys(ebc.by_category);
        if (cats.length > 0) {
            charts.push({
                title: "Expenses by Category",
                canvasId: "chartExpense",
                render: () => {
                    chartInstances["chartExpense"] = new Chart($("chartExpense"), {
                        type: "doughnut",
                        data: { labels: cats, datasets: [{ data: cats.map((c) => ebc.by_category[c]), backgroundColor: palette(cats.length), borderWidth: 3, borderColor: "#fff" }] },
                        options: doughnutOpts(),
                    });
                },
            });
        }
    }

    if (findings.profit_by_category && findings.profit_by_category.categories) {
        const pbc = findings.profit_by_category;
        charts.push({
            title: "Estimated Profit by Category",
            canvasId: "chartProfit",
            render: () => {
                chartInstances["chartProfit"] = new Chart($("chartProfit"), {
                    type: "bar",
                    data: {
                        labels: pbc.categories.map((c) => c.category),
                        datasets: [{ label: "Profit", data: pbc.categories.map((c) => c.profit),
                            backgroundColor: pbc.categories.map((c) => c.is_loss_making ? "rgba(220,38,38,0.7)" : "rgba(79,70,229,0.7)"),
                            borderRadius: 4, borderWidth: 1 }],
                    },
                    options: { ...chartOpts(false, true), indexAxis: "y" },
                });
            },
        });
    }

    if (findings.invoice_status && findings.invoice_status.by_status) {
        const ist = findings.invoice_status;
        const statuses = Object.keys(ist.by_status);
        if (statuses.length > 0) {
            charts.push({
                title: "Invoice Status",
                canvasId: "chartInvoiceStatus",
                render: () => {
                    const cm = { paid: "rgba(5,150,105,0.75)", overdue: "rgba(220,38,38,0.75)", pending: "rgba(217,119,6,0.75)", cancelled: "rgba(100,116,139,0.6)", partial: "rgba(217,119,6,0.5)" };
                    chartInstances["chartInvoiceStatus"] = new Chart($("chartInvoiceStatus"), {
                        type: "doughnut",
                        data: { labels: statuses, datasets: [{ data: statuses.map((s) => ist.by_status[s]),
                            backgroundColor: statuses.map((s) => cm[s] || "rgba(79,70,229,0.7)"), borderWidth: 3, borderColor: "#fff" }] },
                        options: doughnutOpts(),
                    });
                },
            });
        }
    }

    if (findings.regional_analysis && findings.regional_analysis.regions) {
        const ra = findings.regional_analysis;
        charts.push({
            title: "Revenue & Profit by Region",
            canvasId: "chartRegional",
            render: () => {
                chartInstances["chartRegional"] = new Chart($("chartRegional"), {
                    type: "bar",
                    data: {
                        labels: ra.regions.map((r) => r.region),
                        datasets: [
                            { label: "Revenue", data: ra.regions.map((r) => r.revenue), backgroundColor: "rgba(79,70,229,0.7)", borderRadius: 4, borderWidth: 1 },
                            { label: "Profit", data: ra.regions.map((r) => r.profit),
                              backgroundColor: ra.regions.map((r) => r.profit >= 0 ? "rgba(5,150,105,0.7)" : "rgba(220,38,38,0.7)"), borderRadius: 4, borderWidth: 1 },
                        ],
                    },
                    options: chartOpts(true, true),
                });
            },
        });
    }

    if (findings.monthly_trends && findings.monthly_trends.months && findings.monthly_trends.months.length > 0) {
        const mt = findings.monthly_trends;
        charts.push({
            title: "Monthly Net Profit Trend",
            canvasId: "chartNetTrend",
            render: () => {
                chartInstances["chartNetTrend"] = new Chart($("chartNetTrend"), {
                    type: "line",
                    data: {
                        labels: mt.months,
                        datasets: [{ label: "Net", data: mt.months.map((m) => mt.net_by_month[m] || 0),
                            borderColor: "rgba(79,70,229,1)", backgroundColor: "rgba(79,70,229,0.12)",
                            fill: true, tension: 0.35, pointRadius: 5, pointHoverRadius: 7, pointBackgroundColor: "rgba(79,70,229,1)" }],
                    },
                    options: chartOpts(false, false),
                });
            },
        });
    }

    grid.innerHTML = charts.map((c) => `
        <div class="chart-card">
            <h3>${c.title}</h3>
            <div class="chart-container"><canvas id="${c.canvasId}"></canvas></div>
        </div>
    `).join("");

    charts.forEach((c) => { const el = $(c.canvasId); if (el) c.render(); });
}

/* ===== Tables ===== */
function renderTables(findings) {
    const section = $("tablesSection");
    const tables = [];

    if (findings.category_summary && findings.category_summary.length > 0) {
        tables.push(buildTable("Category Summary", findings.category_summary, [
            { key: "category", label: "Category" },
            { key: "income_rm", label: "Income", fmt: "rm" },
            { key: "expense_rm", label: "Expense", fmt: "rm" },
            { key: "net_rm", label: "Net", fmt: "rm", sign: true },
            { key: "transaction_count", label: "Txns" },
        ]));
    }
    if (findings.profit_by_category && findings.profit_by_category.categories) {
        tables.push(buildTable("Profitability by Category", findings.profit_by_category.categories, [
            { key: "category", label: "Category" },
            { key: "revenue", label: "Revenue", fmt: "rm" },
            { key: "total_cost", label: "Total Cost", fmt: "rm" },
            { key: "profit", label: "Profit", fmt: "rm", sign: true },
            { key: "profit_margin_pct", label: "Margin", fmt: "pct" },
            { key: "status", label: "Status", custom: (r) => `<span class="loss-tag ${r.is_loss_making ? "loss" : "profit"}">${r.is_loss_making ? "LOSS" : "PROFIT"}</span>` },
        ]));
    }
    if (findings.invoice_status && findings.invoice_status.by_status) {
        const ist = findings.invoice_status;
        const rows = Object.keys(ist.by_status).map((s) => ({ status: s, count: ist.by_status[s], total_amount_rm: ist.by_status_amount[s] || 0 }));
        tables.push(buildTable("Invoice Status", rows, [
            { key: "status", label: "Status" }, { key: "count", label: "Count" }, { key: "total_amount_rm", label: "Total Amount", fmt: "rm" },
        ]));
    }
    if (findings.outstanding) {
        const out = findings.outstanding;
        const rows = [...(out.overdue_invoices || []), ...(out.pending_invoices || [])];
        if (rows.length > 0) {
            tables.push(buildTable("Overdue & Pending Invoices", rows, [
                { key: "invoice_id", label: "Invoice ID" }, { key: "customer_name", label: "Customer" },
                { key: "due_date", label: "Due" },
                { key: "invoice_amount_rm", label: "Amount", fmt: "rm" }, { key: "amount_paid_rm", label: "Paid", fmt: "rm" },
                { key: "balance_due_rm", label: "Balance", fmt: "rm" }, { key: "status", label: "Status" },
            ]));
        }
    }
    if (findings.monthly_trends && findings.monthly_trends.months) {
        const mt = findings.monthly_trends;
        const rows = mt.months.map((m) => ({ month: m, income_rm: mt.income_by_month[m] || 0, expense_rm: mt.expense_by_month[m] || 0, net_rm: mt.net_by_month[m] || 0 }));
        tables.push(buildTable("Monthly Trends", rows, [
            { key: "month", label: "Month" }, { key: "income_rm", label: "Income", fmt: "rm" },
            { key: "expense_rm", label: "Expense", fmt: "rm" }, { key: "net_rm", label: "Net", fmt: "rm", sign: true },
        ]));
    }
    if (findings.regional_analysis && findings.regional_analysis.regions) {
        tables.push(buildTable("Regional Analysis", findings.regional_analysis.regions, [
            { key: "region", label: "Region" }, { key: "revenue", label: "Revenue", fmt: "rm" },
            { key: "profit", label: "Profit", fmt: "rm", sign: true },
            { key: "profit_margin_pct", label: "Margin", fmt: "pct" }, { key: "invoice_count", label: "Invoices" },
        ]));
    }
    if (findings.customer_breakdown && findings.customer_breakdown.customers) {
        const cb = findings.customer_breakdown;
        const rows = cb.customers.map((c) => ({ customer_name: c, invoiced_rm: cb.invoiced_by_customer[c] || 0, outstanding_rm: cb.outstanding_by_customer[c] || 0 }));
        tables.push(buildTable("Customer Breakdown", rows, [
            { key: "customer_name", label: "Customer" }, { key: "invoiced_rm", label: "Invoiced", fmt: "rm" },
            { key: "outstanding_rm", label: "Outstanding", fmt: "rm" },
        ]));
    }
    if (findings.expense_ratio && findings.expense_ratio.top_expense_categories) {
        tables.push(buildTable("Expense Categories", findings.expense_ratio.top_expense_categories, [
            { key: "category", label: "Category" }, { key: "amount", label: "Amount", fmt: "rm" },
        ]));
    }

    section.innerHTML = tables.map((t) => `
        <div class="table-card">
            <h3>${t.title}</h3>
            <div class="table-wrap">${t.html}</div>
        </div>
    `).join("");
}

function buildTable(title, rows, cols) {
    if (!rows || rows.length === 0) return { title, html: '<p style="color:var(--text-3);font-size:14px;">No data available.</p>' };
    const th = cols.map((c) => `<th>${c.label}</th>`).join("");
    const tr = rows.map((r) => {
        const tds = cols.map((c) => {
            if (c.custom) return `<td>${c.custom(r)}</td>`;
            let v = r[c.key]; if (v === undefined || v === null) v = "";
            if (c.fmt === "rm") { const cl = c.sign ? (v >= 0 ? "kpi-positive" : "kpi-negative") : ""; return `<td class="${cl}">${fmtRM(v)}</td>`; }
            if (c.fmt === "pct") return `<td>${v}%</td>`;
            return `<td>${esc(String(v))}</td>`;
        }).join("");
        return `<tr>${tds}</tr>`;
    }).join("");
    return { title, html: `<table class="data-table"><thead><tr>${th}</tr></thead><tbody>${tr}</tbody></table>` };
}

/* ===== Recommended Actions ===== */
function renderRecommendations(actions) {
    const section = $("recSection");
    const list = $("recList");
    if (!actions || actions.length === 0) {
        section.style.display = "none";
        return;
    }
    section.style.display = "block";
    const colorMap = { 1: "var(--danger)", 2: "var(--warning)", 3: "var(--success)" };
    const labelMap = { 1: "URGENT", 2: "IMPORTANT", 3: "GOOD TO DO" };
    list.innerHTML = actions.map((a, i) => {
        const color = colorMap[a.priority] || "var(--primary)";
        const label = labelMap[a.priority] || "INFO";
        const effort = a.priority === 1 ? "Low effort, high impact" : a.priority === 2 ? "Medium effort" : "Strategic";
        return `<div class="rec-card priority-${a.priority}" style="animation: panelIn 0.4s ease ${i * 0.08}s both; border-left: 4px solid ${color};">
            <div class="rec-header">
                <span class="rec-badge" style="background:${color};">P${a.priority} &middot; ${label}</span>
                <span class="rec-effort">${effort}</span>
            </div>
            <div class="rec-title">${esc(a.title)}</div>
            <div class="rec-body">
                <div class="rec-field"><span class="rec-field-label">Problem:</span> ${esc(a.finding)}</div>
                <div class="rec-field"><span class="rec-field-label">Action:</span> ${esc(a.recommendation)}</div>
                <div class="rec-field"><span class="rec-field-label">Why:</span> ${esc(a.rationale)}</div>
            </div>
            <div class="rec-source">Source: ${esc(a.data_source)}</div>
        </div>`;
    }).join("");
}

/* ===== Data Notes ===== */
function renderDataNotes(notes) {
    const list = $("dataNotesList");
    if (!notes || notes.length === 0) {
        list.innerHTML = '<p style="color:var(--text-3);font-size:14px;padding:20px;">No notes for this analysis.</p>';
        return;
    }
    list.innerHTML = notes.map((n, i) => `<li style="animation: panelIn 0.3s ease ${i * 0.05}s both;">${esc(n)}</li>`).join("");
}

/* ===== Output Files ===== */
function renderOutputFiles(result) {
    const list = $("outputFilesList");
    const files = [];
    if (result.report_download) files.push({ name: result.report_download, type: "txt", label: "Full Text Report" });
    if (result.csv_downloads) result.csv_downloads.forEach((name) => files.push({ name, type: "csv", label: name.replace(/_/g, " ").replace(/\.csv$/i, "") }));

    if (files.length === 0) {
        list.innerHTML = '<p style="color:var(--text-3);font-size:14px;padding:20px;">No files generated.</p>';
        return;
    }

    list.innerHTML = files.map((f) => `
        <div class="output-file-item">
            <div class="file-info">
                <span class="file-ext ${f.type}">${f.type.toUpperCase()}</span>
                <span>${esc(f.label)}</span>
            </div>
            <a class="btn-download" href="/api/download/${encodeURIComponent(f.name)}" download>
                <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                Download
            </a>
        </div>
    `).join("");
}

/* ===== Helpers ===== */
function updateStatus(state, text) {
    statusPill.className = "status-pill" + (state ? " " + state : "");
    statusText.textContent = text;
}

function showToast(msg, type) {
    const toast = document.createElement("div");
    toast.className = "toast toast-" + (type || "info");
    const icon = type === "error" ? "\u26A0" : type === "success" ? "\u2713" : "i";
    toast.innerHTML = `<span style="font-weight:700;">${icon}</span> <span>${esc(msg)}</span>`;
    toastContainer.appendChild(toast);
    setTimeout(() => { toast.classList.add("out"); setTimeout(() => toast.remove(), 300); }, 3500);
}

function fmtRM(val) {
    if (val === undefined || val === null || val === "") return "RM 0.00";
    const num = Number(val);
    if (isNaN(num)) return `RM ${val}`;
    return "RM " + num.toLocaleString("en-MY", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
function formatBytes(b) { if (b < 1024) return b + " B"; if (b < 1048576) return (b / 1024).toFixed(1) + " KB"; return (b / 1048576).toFixed(1) + " MB"; }
function esc(s) { if (!s) return ""; return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;"); }
function escapeHtml(s) { return esc(s); }

function chartOpts(showLegend, showGrid) {
    return {
        responsive: true, maintainAspectRatio: false,
        animation: { duration: 600, easing: "easeOutQuart" },
        plugins: {
            legend: showLegend ? { position: "top", labels: { font: { size: 11, family: "Inter" }, usePointStyle: true, padding: 16 } } : { display: false },
            tooltip: { backgroundColor: "#0f172a", titleFont: { family: "Inter" }, bodyFont: { family: "Inter" }, padding: 12, cornerRadius: 8,
                callbacks: { label: (ctx) => { const l = ctx.dataset.label || ctx.label || ""; const v = ctx.parsed.y !== undefined ? ctx.parsed.y : (ctx.parsed || 0); return `${l}: ${fmtRM(v)}`; } } },
        },
        scales: showGrid ? {
            y: { ticks: { callback: (v) => "RM " + v.toLocaleString(), font: { size: 11, family: "Inter" } }, grid: { color: "rgba(226,232,240,0.6)" } },
            x: { ticks: { font: { size: 11, family: "Inter" } }, grid: { display: false } },
        } : { y: { ticks: { font: { size: 11 } } }, x: { ticks: { font: { size: 11 } } } },
    };
}

function doughnutOpts() {
    return {
        responsive: true, maintainAspectRatio: false,
        animation: { animateRotate: true, duration: 700, easing: "easeOutQuart" },
        plugins: {
            legend: { position: "bottom", labels: { font: { size: 11, family: "Inter" }, usePointStyle: true, padding: 14 } },
            tooltip: { backgroundColor: "#0f172a", padding: 12, cornerRadius: 8,
                callbacks: { label: (ctx) => `${ctx.label}: ${fmtRM(ctx.parsed)}` } },
        },
    };
}

function palette(n) {
    const p = ["rgba(79,70,229,0.75)", "rgba(5,150,105,0.75)", "rgba(220,38,38,0.75)", "rgba(217,119,6,0.75)", "rgba(124,58,237,0.75)", "rgba(236,72,153,0.75)", "rgba(14,165,233,0.75)", "rgba(34,197,94,0.75)"];
    if (n <= p.length) return p.slice(0, n);
    while (p.length < n) p.push(`hsla(${(p.length * 47) % 360}, 60%, 55%, 0.75)`);
    return p.slice(0, n);
}

/* ===== Reconciliation ===== */
function renderReconciliation(recon) {
    const s = recon.summary || {};
    const issues = recon.issues || [];

    const grid = $("kpiGrid");
    if (grid && s.total_issues !== undefined) {
        grid.innerHTML += kpiCard("Data Issues", s.total_issues,
            `${s.critical_count || 0} critical, ${s.warning_count || 0} warnings`,
            (s.critical_count || 0) > 0 ? "kpi-negative" : "kpi-positive");
    }

    const section = $("tablesSection");
    if (section && issues.length > 0) {
        const tableHtml = buildTable("Data Reconciliation Issues", issues, [
            { key: "severity", label: "Severity", custom: (r) => {
                const cl = r.severity === "critical" ? "kpi-negative" : r.severity === "warning" ? "kpi-neutral" : "kpi-positive";
                return `<span class="${cl}" style="font-weight:700;text-transform:uppercase;font-size:11px;">${r.severity}</span>`;
            }},
            { key: "category", label: "Type" },
            { key: "description", label: "Issue" },
            { key: "action", label: "Action Needed" },
        ]);
        section.innerHTML += `<div class="table-card">${tableHtml.title}<div class="table-wrap">${tableHtml.html}</div></div>`;
    }

    if (s.total_issues === 0) {
        const list = $("dataNotesList");
        if (list) list.innerHTML = '<li style="animation: panelIn 0.3s ease both;"><strong style="color: var(--success);">All records reconcile correctly.</strong> No data integrity issues found.</li>' + list.innerHTML;
    }
}

/* ===== Customer Messages ===== */
function renderCustomerMessages(messages) {
    if (!messages || messages.length === 0) return;

    const section = $("tablesSection");
    if (section) {
        const tableHtml = buildTable("Customer Follow-Up Messages", messages, [
            { key: "priority", label: "Pri", custom: (r) => `<span class="rec-priority-badge">P${r.priority}</span>` },
            { key: "customer_name", label: "Customer" },
            { key: "invoice_id", label: "Invoice" },
            { key: "amount_owed", label: "Owed", fmt: "rm" },
            { key: "status", label: "Status" },
            { key: "channel", label: "Channel" },
        ]);
        section.innerHTML += `<div class="table-card"><h3>Customer Follow-Up Messages</h3><div class="table-wrap">${tableHtml.html}</div></div>`;
    }

    const list = $("dataNotesList");
    if (list) {
        let msgHtml = '<li style="animation: panelIn 0.3s ease both; list-style: none; margin-bottom: 16px;"><strong>Customer Messages (ready to copy-paste):</strong></li>';
        messages.forEach((m, i) => {
            msgHtml += `<li style="animation: panelIn 0.3s ease ${i * 0.05}s both; list-style: none; margin-bottom: 12px; padding: 12px; border-radius: 8px; background: var(--surface-2);">
                <div style="display:flex;gap:8px;align-items:center;margin-bottom:8px;">
                    <span class="rec-priority-badge">P${m.priority}</span>
                    <strong>${esc(m.customer_name)}</strong>
                    <span style="color:var(--text-3);">|</span>
                    <span>${esc(m.invoice_id)}</span>
                    <span style="color:var(--text-3);">|</span>
                    <span class="kpi-negative" style="font-weight:700;">${fmtRM(m.amount_owed)}</span>
                    <span style="color:var(--text-3);">|</span>
                    <span style="font-size:11px;padding:2px 6px;border-radius:4px;background:var(--surface-3);">${esc(m.channel)}</span>
                </div>
                <pre style="white-space:pre-wrap;font-family:inherit;font-size:13px;line-height:1.6;color:var(--text-2);margin:0;">${esc(m.message)}</pre>
            </li>`;
        });
        list.innerHTML = msgHtml + list.innerHTML;
    }
}

/* ===== Action Plan (REMOVED per user request) ===== */
// renderActionPlan function removed — PLAN card no longer shows on Results page.
