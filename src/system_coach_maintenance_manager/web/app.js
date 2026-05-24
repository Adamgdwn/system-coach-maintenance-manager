const statusText = document.querySelector("#statusText");
const summaryGrid = document.querySelector("#summaryGrid");
const environmentGrid = document.querySelector("#environmentGrid");
const componentGrid = document.querySelector("#componentGrid");
const stackMatches = document.querySelector("#stackMatches");
const learningPath = document.querySelector("#learningPath");
const recommendations = document.querySelector("#recommendations");
const commandLog = document.querySelector("#commandLog");
const runReviewButton = document.querySelector("#runReviewButton");
const shareSummaryButton = document.querySelector("#shareSummaryButton");
const runMaintenanceButton = document.querySelector("#runMaintenanceButton");
const runMapButton = document.querySelector("#runMapButton");
const suggestedRoots = document.querySelector("#suggestedRoots");
const customRootsInput = document.querySelector("#customRootsInput");
const mapSummaryGrid = document.querySelector("#mapSummaryGrid");
const mapTeachingNotes = document.querySelector("#mapTeachingNotes");
const configGrid = document.querySelector("#configGrid");
const scanResults = document.querySelector("#scanResults");
const maintenanceSummaryGrid = document.querySelector("#maintenanceSummaryGrid");
const maintenanceFindings = document.querySelector("#maintenanceFindings");
const maintenancePlans = document.querySelector("#maintenancePlans");
const popCosmicConcernInput = document.querySelector("#popCosmicConcernInput");
const popCosmicScopeInput = document.querySelector("#popCosmicScopeInput");
const popCosmicScanButton = document.querySelector("#popCosmicScanButton");
const popCosmicResearchButton = document.querySelector("#popCosmicResearchButton");
const popCosmicAnalyzeButton = document.querySelector("#popCosmicAnalyzeButton");
const popCosmicPlanButton = document.querySelector("#popCosmicPlanButton");
const popCosmicExecuteButton = document.querySelector("#popCosmicExecuteButton");
const popCosmicVerifyButton = document.querySelector("#popCosmicVerifyButton");
const popCosmicSummary = document.querySelector("#popCosmicSummary");
const popCosmicAnalysis = document.querySelector("#popCosmicAnalysis");
const popCosmicConfirmationInput = document.querySelector("#popCosmicConfirmationInput");
const popCosmicActionLog = document.querySelector("#popCosmicActionLog");
const requestInput = document.querySelector("#requestInput");
const prepareRequestButton = document.querySelector("#prepareRequestButton");
const requestPlan = document.querySelector("#requestPlan");
const refreshHistoryButton = document.querySelector("#refreshHistoryButton");
const historyPath = document.querySelector("#historyPath");
const historyChanges = document.querySelector("#historyChanges");
const historyLessons = document.querySelector("#historyLessons");
const historyRecords = document.querySelector("#historyRecords");
const coachQuestionInput = document.querySelector("#coachQuestionInput");
const askCoachButton = document.querySelector("#askCoachButton");
const coachConversation = document.querySelector("#coachConversation");
const componentTemplate = document.querySelector("#componentTemplate");
let currentReport = null;
let currentMap = null;
let currentMaintenance = null;
let currentRequestPlan = null;
let currentHistory = null;
let currentPopCosmicScan = null;
let currentPopCosmicResearch = null;
let currentPopCosmicAnalysis = null;
let currentPopCosmicPlan = null;
let currentPopCosmicResult = null;

function setStatus(text) {
  statusText.textContent = text;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function renderSummary(report) {
  const breakdown = Object.entries(report.summary.category_breakdown)
    .map(([category, count]) => `${count} ${category}`)
    .join(" • ");

  summaryGrid.innerHTML = `
    <article class="summary-card">
      <span class="summary-label">Installed components</span>
      <strong>${report.summary.installed_component_count}</strong>
    </article>
    <article class="summary-card">
      <span class="summary-label">Detected mix</span>
      <strong>${breakdown || "No components found yet"}</strong>
    </article>
    <article class="summary-card">
      <span class="summary-label">Report generated</span>
      <strong>${new Date(report.generated_at).toLocaleString()}</strong>
    </article>
  `;
}

function renderEnvironment(report) {
  environmentGrid.innerHTML = "";
  Object.entries(report.environment).forEach(([key, value]) => {
    const card = document.createElement("article");
    card.className = "data-card";
    card.innerHTML = `<span>${key.replaceAll("_", " ")}</span><strong>${value}</strong>`;
    environmentGrid.appendChild(card);
  });
}

function renderComponents(report) {
  componentGrid.innerHTML = "";
  report.components.forEach((component) => {
    const fragment = componentTemplate.content.cloneNode(true);
    fragment.querySelector(".category").textContent = component.category;
    fragment.querySelector(".version").textContent = component.version || "Unknown version";
    fragment.querySelector(".title").textContent = component.label;
    fragment.querySelector(".role").textContent = component.role;
    fragment.querySelector(".path").textContent = component.path ? `Path: ${component.path}` : "Path unknown";
    fragment.querySelector(".tip").textContent = `Learning tip: ${component.learning_tip}`;
    const pairs = fragment.querySelector(".pairs");
    const pairText = component.pairs_well_with.length
      ? `Works well with: ${component.pairs_well_with.join(", ")}`
      : "No built-in pairing note yet.";
    pairs.textContent = pairText;
    componentGrid.appendChild(fragment);
  });
}

function renderStackMatches(report) {
  stackMatches.innerHTML = "";
  const matches = report.summary.primary_stack_matches;
  if (!matches.length) {
    stackMatches.innerHTML = `<article class="stack-card"><h3>Still learning the shape</h3><p>No strong stack pattern matched yet. That usually means the environment is minimal or highly specialized.</p></article>`;
    return;
  }
  matches.forEach((match) => {
    const item = document.createElement("article");
    item.className = "stack-card";
    item.innerHTML = `
      <div class="stack-topline">
        <h3>${match.title}</h3>
        <span class="pill confidence">${match.confidence} confidence</span>
      </div>
      <p>${match.summary}</p>
      <p>${match.coaching}</p>
    `;
    stackMatches.appendChild(item);
  });
}

function renderLearningPath(report) {
  learningPath.innerHTML = "";
  report.learning_path.forEach((step) => {
    const item = document.createElement("li");
    item.textContent = step;
    learningPath.appendChild(item);
  });
}

function renderRecommendations(report) {
  recommendations.innerHTML = "";
  report.recommendations.forEach((itemText) => {
    const item = document.createElement("li");
    item.textContent = itemText;
    recommendations.appendChild(item);
  });
}

function renderCommandLog(report) {
  commandLog.innerHTML = "";
  if (!report.command_log.length) {
    commandLog.textContent = "No commands were needed.";
    return;
  }
  report.command_log.forEach((entry) => {
    const line = document.createElement("div");
    line.className = "command-entry";
    line.innerHTML = `
      <code>${entry.command}</code>
      <span>exit ${entry.exit_code}</span>
      <span>${entry.duration_ms}ms</span>
      <p>${entry.output || "No output"}</p>
    `;
    commandLog.appendChild(line);
  });
}

function renderSuggestedRoots(payload) {
  suggestedRoots.innerHTML = "";
  payload.suggested_roots.forEach((root) => {
    const label = document.createElement("label");
    label.className = "chip-option";
    label.innerHTML = `
      <input type="checkbox" value="${root.path}" />
      <span>${root.path}</span>
    `;
    suggestedRoots.appendChild(label);
  });
}

function selectedRoots() {
  const checked = [...document.querySelectorAll("#suggestedRoots input:checked")].map((input) => input.value.trim());
  const manual = customRootsInput.value
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
  return [...new Set([...checked, ...manual])];
}

function renderMapSummary(map) {
  mapSummaryGrid.innerHTML = `
    <article class="summary-card">
      <span class="summary-label">Roots scanned</span>
      <strong>${map.summary.roots_scanned}</strong>
    </article>
    <article class="summary-card">
      <span class="summary-label">Projects detected</span>
      <strong>${map.summary.projects_detected}</strong>
    </article>
    <article class="summary-card">
      <span class="summary-label">Configs detected</span>
      <strong>${map.summary.configs_detected}</strong>
    </article>
    <article class="summary-card">
      <span class="summary-label">Entries scanned</span>
      <strong>${map.summary.entries_scanned}</strong>
    </article>
  `;

  mapTeachingNotes.innerHTML = "";
  map.teaching_notes.forEach((note) => {
    const item = document.createElement("li");
    item.textContent = note;
    mapTeachingNotes.appendChild(item);
  });
}

function renderConfigFindings(map) {
  configGrid.innerHTML = "";
  if (!map.config_findings.length) {
    configGrid.innerHTML = `<article class="stack-card"><h3>No common config files found</h3><p>The selected roots did not expose any of the built-in config markers yet.</p></article>`;
    return;
  }
  map.config_findings.forEach((finding) => {
    const item = document.createElement("article");
    item.className = "stack-card";
    item.innerHTML = `<h3>${finding.label}</h3><p>${finding.path}</p><p>${finding.teaching}</p>`;
    configGrid.appendChild(item);
  });
}

function renderScanResults(map) {
  scanResults.innerHTML = "";
  if (!map.scans.length) {
    scanResults.innerHTML = `<article class="stack-card"><h3>No roots scanned yet</h3><p>Select one or more roots, then run a filesystem map.</p></article>`;
    return;
  }
  map.scans.forEach((scan) => {
    const projects = scan.projects.length
      ? scan.projects
          .map((project) => `<li><strong>${project.path}</strong><br>${project.types.join(", ")}<br>${project.teaching}</li>`)
          .join("")
      : "<li>No project markers found in this root.</li>";

    const dirs = scan.interesting_directories.length
      ? `<p><strong>Interesting directories:</strong> ${scan.interesting_directories.join(", ")}</p>`
      : "";

    const errors = scan.permission_errors.length
      ? `<p><strong>Permission limits:</strong> ${scan.permission_errors.join(", ")}</p>`
      : "";

    const card = document.createElement("article");
    card.className = "stack-card";
    card.innerHTML = `
      <div class="stack-topline">
        <h3>${scan.root}</h3>
        <span class="pill">${scan.summary.projects_detected} projects</span>
      </div>
      <p>Scanned ${scan.summary.entries_scanned} entries, including ${scan.summary.directories} directories and ${scan.summary.files} files.</p>
      ${dirs}
      ${errors}
      <ul class="text-list compact-list">${projects}</ul>
    `;
    scanResults.appendChild(card);
  });
}

function renderMaintenance(report) {
  maintenanceSummaryGrid.innerHTML = `
    <article class="summary-card">
      <span class="summary-label">Findings</span>
      <strong>${report.summary.finding_count}</strong>
    </article>
    <article class="summary-card">
      <span class="summary-label">Warnings</span>
      <strong>${report.summary.severity_counts.warning || 0}</strong>
    </article>
    <article class="summary-card">
      <span class="summary-label">Critical</span>
      <strong>${report.summary.severity_counts.critical || 0}</strong>
    </article>
    <article class="summary-card">
      <span class="summary-label">Approval plans</span>
      <strong>${report.summary.approval_required_count}</strong>
    </article>
  `;

  maintenanceFindings.innerHTML = "";
  report.findings.forEach((finding) => {
    const card = document.createElement("article");
    card.className = "stack-card";
    const steps = finding.recommended_next_steps.map((step) => `<li>${step}</li>`).join("");
    card.innerHTML = `
      <div class="stack-topline">
        <h3>${finding.title}</h3>
        <span class="pill confidence">${finding.severity}</span>
      </div>
      <p>${finding.summary}</p>
      <ul class="text-list compact-list">${steps}</ul>
    `;
    maintenanceFindings.appendChild(card);
  });

  renderApprovalQueue();
}

function planDetailsHtml(plan) {
  const commands = plan.commands?.length
    ? plan.commands.map((command) => `<li><code>${command}</code></li>`).join("")
    : "<li>No commands prepared yet.</li>";
  const manualSteps = plan.manual_steps?.length
    ? `<p><strong>Manual steps</strong></p><ul class="text-list compact-list">${plan.manual_steps
        .map((step) => `<li>${step}</li>`)
        .join("")}</ul>`
    : "";
  const rollback = plan.rollback?.length
    ? `<p><strong>Rollback</strong></p><ul class="text-list compact-list">${plan.rollback
        .map((step) => `<li>${step}</li>`)
        .join("")}</ul>`
    : "";
  const contract = plan.action_contract
    ? `
      <p><strong>Action runner contract</strong></p>
      <ul class="text-list compact-list">
        <li>Contract: ${plan.action_contract.contract_version}</li>
        <li>Action id: ${plan.action_contract.id}</li>
        <li>Eligible for guarded execution: ${plan.action_contract.eligible_for_guarded_execution ? "yes" : "no"}</li>
        <li>Execution enabled: ${plan.action_contract.execution_enabled ? "yes" : "no"}</li>
        <li>Confirmation phrase: <code>${plan.action_contract.confirmation_phrase}</code></li>
        ${(plan.action_contract.execution_gate?.reasons || []).map((reason) => `<li>Gate: ${reason}</li>`).join("")}
        ${(plan.action_contract.post_check || []).map((step) => `<li>Post-check: ${step}</li>`).join("")}
      </ul>
    `
    : "";
  return `
    <p>${plan.summary || plan.expected_effect}</p>
    <p>Risk: ${plan.risk} · Requires privilege: ${plan.requires_privilege ? "yes" : "no"} · Reversible: ${plan.reversible ? "yes" : "no"} · Approval required: ${plan.approval_required ? "yes" : "no"} · Execution enabled: ${plan.execution_enabled ? "yes" : "no"}</p>
    <p><strong>Commands</strong></p>
    <ul class="text-list compact-list">${commands}</ul>
    ${manualSteps}
    <p><strong>Expected effect</strong></p>
    <p>${plan.expected_effect}</p>
    ${rollback}
    <p>${plan.approval_prompt}</p>
    ${contract}
  `;
}

function renderApprovalQueue() {
  maintenancePlans.innerHTML = "";
  const queuedPlans = [
    ...(currentMaintenance?.action_plans || []),
    ...(currentRequestPlan ? [currentRequestPlan] : []),
  ];
  if (!queuedPlans.length) {
    maintenancePlans.innerHTML = `<article class="stack-card"><h3>No approval queue yet</h3><p>Run diagnostics or prepare a Request Desk plan to populate this queue.</p></article>`;
    return;
  }

  queuedPlans.forEach((plan, index) => {
    const card = document.createElement("article");
    card.className = "stack-card";
    card.innerHTML = `
      <div class="stack-topline">
        <h3>${index + 1}. ${plan.title}</h3>
        <span class="pill">${plan.risk} risk</span>
      </div>
      ${planDetailsHtml(plan)}
    `;
    maintenancePlans.appendChild(card);
  });
}

function renderRequestPlan(plan) {
  requestPlan.innerHTML = `
    <article class="stack-card">
      <div class="stack-topline">
        <h3>${plan.title}</h3>
        <span class="pill">${plan.platform}</span>
      </div>
      ${planDetailsHtml(plan)}
    </article>
  `;
  renderApprovalQueue();
}

function renderPopCosmicScan(scan) {
  const profile = scan.profile || {};
  const findings = (scan.findings || [])
    .map((finding) => `<li>${escapeHtml(finding.severity)}: ${escapeHtml(finding.summary)}</li>`)
    .join("");
  popCosmicSummary.innerHTML = `
    <article class="stack-card">
      <h3>${escapeHtml(profile.pretty_name || "Unknown Linux")}</h3>
      <p>Scope: ${escapeHtml(scan.scope)} · Applicable: ${escapeHtml(scan.applicable)} · COSMIC signal: ${escapeHtml(profile.has_cosmic_signal)}</p>
      <ul class="text-list compact-list">${findings || "<li>No findings returned.</li>"}</ul>
    </article>
  `;
}

function renderPopCosmicAnalysis(analysis) {
  const hypotheses = (analysis.hypotheses || [])
    .map((item) => `<li>${escapeHtml(item.id || "H")}: ${escapeHtml(item.summary || "")}</li>`)
    .join("");
  const actions = (analysis.ranked_actions || []).map((item, index) => `
    <li>${index + 1}. <strong>${escapeHtml(item.action_key)}</strong> - ${escapeHtml(item.title || "")} [${escapeHtml(item.risk || "unknown")}]</li>
  `).join("");
  popCosmicAnalysis.innerHTML = `
    <article class="stack-card">
      <h3>${escapeHtml(analysis.working_problem || "Pop/COSMIC analysis")}</h3>
      <p>Source: ${escapeHtml(analysis.source || "unknown")} ${escapeHtml(analysis.model || "")} · Surface: ${escapeHtml(analysis.likely_surface || "unknown")} · Confidence: ${escapeHtml(analysis.confidence ?? "unknown")}</p>
      <p><strong>Hypotheses</strong></p>
      <ul class="text-list compact-list">${hypotheses || "<li>No hypotheses returned.</li>"}</ul>
      <p><strong>Ranked actions</strong></p>
      <ul class="text-list compact-list">${actions || "<li>No actions returned.</li>"}</ul>
    </article>
  `;
}

function renderPopCosmicPlan(plan) {
  currentRequestPlan = plan;
  renderRequestPlan(plan);
  popCosmicActionLog.innerHTML = `
    <div class="command-entry">
      <code>${escapeHtml(plan.title)}</code>
      <span>${escapeHtml(plan.risk)} risk</span>
      <p>${escapeHtml(plan.summary)}</p>
      <p>Confirmation phrase: <code>${escapeHtml(plan.action_contract?.confirmation_phrase || "")}</code></p>
    </div>
  `;
}

function renderHistory(history) {
  historyPath.textContent = `History path: ${history.path}`;
  historyChanges.innerHTML = "";
  (history.changed_since_last || []).forEach((change) => {
    const card = document.createElement("article");
    card.className = "stack-card";
    card.innerHTML = `<h3>Changed since last run</h3><p>${change}</p>`;
    historyChanges.appendChild(card);
  });

  historyLessons.innerHTML = "";
  if (!history.known_good_lessons.length) {
    historyLessons.innerHTML = `<article class="stack-card"><h3>No known-good lessons yet</h3><p>Clean diagnostic snapshots will appear here only when the evidence supports them.</p></article>`;
  } else {
    history.known_good_lessons.forEach((lesson) => {
      const card = document.createElement("article");
      card.className = "stack-card";
      card.innerHTML = `<h3>Known-good lesson</h3><p>${lesson}</p>`;
      historyLessons.appendChild(card);
    });
  }

  historyRecords.innerHTML = "";
  if (!history.records.length) {
    historyRecords.textContent = "No history records yet.";
    return;
  }

  history.records.forEach((record) => {
    const entry = document.createElement("div");
    entry.className = "command-entry";
    entry.innerHTML = `
      <code>${record.kind}</code>
      <span>${record.recorded_at || "unknown time"}</span>
      <span>${record.id}</span>
      <p>${JSON.stringify(record.summary)}</p>
    `;
    historyRecords.appendChild(entry);
  });
}

function appendCoachMessage(speaker, text) {
  const entry = document.createElement("div");
  entry.className = "command-entry";
  entry.innerHTML = `<code>${speaker}</code><p>${text}</p>`;
  coachConversation.appendChild(entry);
}

async function loadScanOptions() {
  const response = await fetch("/api/scan-options", { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Scan options failed with status ${response.status}`);
  }
  renderSuggestedRoots(await response.json());
}

async function runMap() {
  const roots = selectedRoots();
  if (!roots.length) {
    setStatus("Choose at least one root before running a filesystem map.");
    return;
  }
  setStatus("Scanning the selected roots locally...");
  runMapButton.disabled = true;
  try {
    const response = await fetch("/api/map", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ roots }),
    });
    if (!response.ok) {
      throw new Error(`Map request failed with status ${response.status}`);
    }
    currentMap = await response.json();
    renderMapSummary(currentMap);
    renderConfigFindings(currentMap);
    renderScanResults(currentMap);
    setStatus("Filesystem map complete. Review the discovered roots, projects, and configs below.");
  } catch (error) {
    console.error(error);
    setStatus(`Filesystem map failed: ${error.message}`);
  } finally {
    runMapButton.disabled = false;
  }
}

async function copyShareSummary() {
  if (!currentReport) {
    setStatus("Run a local review before copying a share summary.");
    return;
  }

  const lines = [
    "System Coach and Maintenance Manager",
    "",
    `Generated: ${new Date(currentReport.generated_at).toLocaleString()}`,
    `Operating system: ${currentReport.environment.os}`,
    `Shell: ${currentReport.environment.shell}`,
    `Installed components: ${currentReport.summary.installed_component_count}`,
    "Detected tools:",
    ...currentReport.components.slice(0, 18).map((component) => `- ${component.label} (${component.category})`),
  ];

  if (currentMap) {
    lines.push("");
    lines.push(`Roots scanned: ${currentMap.summary.roots_scanned}`);
    lines.push(`Projects detected: ${currentMap.summary.projects_detected}`);
    lines.push(`Configs detected: ${currentMap.summary.configs_detected}`);
  }

  if (currentMaintenance) {
    lines.push("");
    lines.push(`Maintenance findings: ${currentMaintenance.summary.finding_count}`);
    lines.push(`Approval-required plans: ${currentMaintenance.summary.approval_required_count}`);
    currentMaintenance.findings
      .slice(0, 8)
      .forEach((finding) => lines.push(`- ${finding.title} [${finding.severity}]: ${finding.summary}`));
  }

  lines.push("");
  lines.push("Generated locally on this machine.");
  const summary = lines.join("\n");

  try {
    await navigator.clipboard.writeText(summary);
    setStatus("Share summary copied to the clipboard.");
  } catch (error) {
    console.error(error);
    setStatus("Clipboard copy failed in this browser session.");
  }
}

async function runMaintenance() {
  setStatus("Running read-only maintenance diagnostics...");
  runMaintenanceButton.disabled = true;
  try {
    const response = await fetch("/api/maintenance", { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`Maintenance request failed with status ${response.status}`);
    }
    currentMaintenance = await response.json();
    renderMaintenance(currentMaintenance);
    await loadHistory();
    setStatus("Maintenance diagnostics complete. No fixes were executed.");
  } catch (error) {
    console.error(error);
    setStatus(`Maintenance diagnostics failed: ${error.message}`);
  } finally {
    runMaintenanceButton.disabled = false;
  }
}

async function prepareRequestPlan() {
  const request = requestInput.value.trim();
  if (!request) {
    setStatus("Describe a maintenance request before preparing a plan.");
    return;
  }
  setStatus("Preparing an approval-required plan...");
  prepareRequestButton.disabled = true;
  try {
    const response = await fetch("/api/request-plan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        request,
        os_name: currentReport?.environment?.os || currentMaintenance?.metrics?.platform?.os,
        desktop_hint:
          currentReport?.environment?.desktop ||
          currentMaintenance?.metrics?.desktop?.current_desktop,
        maintenance_report: currentMaintenance,
      }),
    });
    if (!response.ok) {
      throw new Error(`Request plan failed with status ${response.status}`);
    }
    currentRequestPlan = await response.json();
    renderRequestPlan(currentRequestPlan);
    await loadHistory();
    appendCoachMessage("Plan", `${currentRequestPlan.title}\nExecution enabled: ${currentRequestPlan.execution_enabled}`);
    setStatus("Approval-required plan prepared. No change was executed.");
  } catch (error) {
    console.error(error);
    setStatus(`Request plan failed: ${error.message}`);
  } finally {
    prepareRequestButton.disabled = false;
  }
}

async function loadHistory() {
  const response = await fetch("/api/history", { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`History request failed with status ${response.status}`);
  }
  currentHistory = await response.json();
  renderHistory(currentHistory);
}

async function runPopCosmicScan() {
  setStatus("Running Pop!_OS/COSMIC deep scan...");
  popCosmicScanButton.disabled = true;
  try {
    const response = await fetch("/api/pop-cosmic/deep-scan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scope: popCosmicScopeInput.value || "standard" }),
    });
    if (!response.ok) {
      throw new Error(`Pop/COSMIC scan failed with status ${response.status}`);
    }
    currentPopCosmicScan = await response.json();
    renderPopCosmicScan(currentPopCosmicScan);
    setStatus("Pop!_OS/COSMIC scan complete.");
  } catch (error) {
    console.error(error);
    setStatus(`Pop!_OS/COSMIC scan failed: ${error.message}`);
  } finally {
    popCosmicScanButton.disabled = false;
  }
}

async function researchPopCosmic() {
  if (!currentPopCosmicScan) {
    await runPopCosmicScan();
  }
  setStatus("Preparing Pop!_OS/COSMIC research records...");
  const response = await fetch("/api/pop-cosmic/research", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      symptom: popCosmicConcernInput.value.trim(),
      profile: currentPopCosmicScan?.profile,
      enabled: false,
    }),
  });
  currentPopCosmicResearch = await response.json();
  const records = (currentPopCosmicResearch.records || [])
    .map((record) => `<li>[${escapeHtml(record.trust_level)}] ${escapeHtml(record.title)}</li>`)
    .join("");
  popCosmicAnalysis.innerHTML = `<article class="stack-card"><h3>Research records</h3><p>${escapeHtml(currentPopCosmicResearch.privacy)}</p><ul class="text-list compact-list">${records}</ul></article>`;
  setStatus("Pop!_OS/COSMIC research records prepared.");
}

async function analyzePopCosmic() {
  if (!currentPopCosmicScan) {
    await runPopCosmicScan();
  }
  setStatus("Asking local model ladder to analyze Pop!_OS/COSMIC evidence...");
  const response = await fetch("/api/pop-cosmic/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      symptom: popCosmicConcernInput.value.trim(),
      scan: currentPopCosmicScan,
      research: currentPopCosmicResearch?.records || [],
    }),
  });
  currentPopCosmicAnalysis = await response.json();
  renderPopCosmicAnalysis(currentPopCosmicAnalysis);
  setStatus("Pop!_OS/COSMIC analysis complete.");
}

async function buildPopCosmicPlan() {
  if (!currentPopCosmicAnalysis) {
    await analyzePopCosmic();
  }
  const action = (currentPopCosmicAnalysis.ranked_actions || [])[0] || { action_key: "deep-scan-standard" };
  const response = await fetch("/api/pop-cosmic/plan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      action_key: action.action_key,
      analysis: currentPopCosmicAnalysis,
      scan: currentPopCosmicScan,
    }),
  });
  currentPopCosmicPlan = await response.json();
  renderPopCosmicPlan(currentPopCosmicPlan);
  renderApprovalQueue();
  setStatus("Pop!_OS/COSMIC fix plan prepared.");
}

async function executePopCosmicPlan() {
  if (!currentPopCosmicPlan) {
    setStatus("Build a Pop!_OS/COSMIC fix plan first.");
    return;
  }
  const response = await fetch("/api/pop-cosmic/execute", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      plan: currentPopCosmicPlan,
      confirmation: popCosmicConfirmationInput.value.trim(),
    }),
  });
  currentPopCosmicResult = await response.json();
  popCosmicActionLog.innerHTML += `
    <div class="command-entry">
      <code>${escapeHtml(currentPopCosmicResult.action_id || "action")}</code>
      <span>${escapeHtml(currentPopCosmicResult.status)}</span>
      <p>${escapeHtml(currentPopCosmicResult.output || currentPopCosmicResult.error || "No output.")}</p>
    </div>
  `;
  setStatus(`Pop!_OS/COSMIC action ${currentPopCosmicResult.status}.`);
}

async function verifyPopCosmicPlan() {
  if (!currentPopCosmicResult) {
    setStatus("No Pop!_OS/COSMIC action result is available to verify.");
    return;
  }
  const response = await fetch("/api/pop-cosmic/verify", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      symptom: popCosmicConcernInput.value.trim(),
      result: currentPopCosmicResult,
      scan: currentPopCosmicScan,
    }),
  });
  const payload = await response.json();
  currentPopCosmicScan = payload.post_scan;
  renderPopCosmicScan(currentPopCosmicScan);
  setStatus("Pop!_OS/COSMIC verification complete and lesson saved.");
}

async function askCoach() {
  const question = coachQuestionInput.value.trim();
  if (!question) {
    setStatus("Type a question for the local coach first.");
    return;
  }
  appendCoachMessage("You", question);
  setStatus("Local AI is thinking...");
  askCoachButton.disabled = true;
  try {
    const response = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        report: currentReport,
        system_map: currentMap,
        maintenance_report: currentMaintenance,
        request_plan: currentRequestPlan,
      }),
    });
    if (!response.ok) {
      throw new Error(`Coach request failed with status ${response.status}`);
    }
    const payload = await response.json();
    appendCoachMessage(`Coach [${payload.model || "local engine unavailable"}]`, payload.answer);
    setStatus("Coach answer ready.");
  } catch (error) {
    console.error(error);
    setStatus(`Coach request failed: ${error.message}`);
  } finally {
    askCoachButton.disabled = false;
  }
}

async function runReview() {
  setStatus("Running local probe agents...");
  runReviewButton.disabled = true;
  try {
    const response = await fetch("/api/report", { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`Request failed with status ${response.status}`);
    }
    const report = await response.json();
    currentReport = report;
    renderSummary(report);
    renderEnvironment(report);
    renderComponents(report);
    renderStackMatches(report);
    renderLearningPath(report);
    renderRecommendations(report);
    renderCommandLog(report);
    setStatus("Review complete. Explore the sections below to learn the environment.");
  } catch (error) {
    console.error(error);
    setStatus(`Review failed: ${error.message}`);
  } finally {
    runReviewButton.disabled = false;
  }
}

runMapButton.addEventListener("click", runMap);
shareSummaryButton.addEventListener("click", copyShareSummary);
runReviewButton.addEventListener("click", runReview);
runMaintenanceButton.addEventListener("click", runMaintenance);
popCosmicScanButton.addEventListener("click", runPopCosmicScan);
popCosmicResearchButton.addEventListener("click", researchPopCosmic);
popCosmicAnalyzeButton.addEventListener("click", analyzePopCosmic);
popCosmicPlanButton.addEventListener("click", buildPopCosmicPlan);
popCosmicExecuteButton.addEventListener("click", executePopCosmicPlan);
popCosmicVerifyButton.addEventListener("click", verifyPopCosmicPlan);
prepareRequestButton.addEventListener("click", prepareRequestPlan);
refreshHistoryButton.addEventListener("click", () => {
  loadHistory()
    .then(() => setStatus("Local maintenance history refreshed."))
    .catch((error) => {
      console.error(error);
      setStatus(`History refresh failed: ${error.message}`);
    });
});
askCoachButton.addEventListener("click", askCoach);
loadScanOptions().catch((error) => {
  console.error(error);
  setStatus(`Could not load scan options: ${error.message}`);
});
runReview();
runMaintenance();
loadHistory().catch((error) => {
  console.error(error);
  setStatus(`Could not load history: ${error.message}`);
});
