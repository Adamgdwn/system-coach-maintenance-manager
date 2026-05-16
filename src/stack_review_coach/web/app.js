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
const requestInput = document.querySelector("#requestInput");
const prepareRequestButton = document.querySelector("#prepareRequestButton");
const requestPlan = document.querySelector("#requestPlan");
const coachQuestionInput = document.querySelector("#coachQuestionInput");
const askCoachButton = document.querySelector("#askCoachButton");
const coachConversation = document.querySelector("#coachConversation");
const componentTemplate = document.querySelector("#componentTemplate");
let currentReport = null;
let currentMap = null;
let currentMaintenance = null;
let currentRequestPlan = null;

function setStatus(text) {
  statusText.textContent = text;
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

  maintenancePlans.innerHTML = "";
  if (!report.action_plans.length) {
    maintenancePlans.innerHTML = `<article class="stack-card"><h3>No approval queue yet</h3><p>The current diagnostics did not prepare a maintenance plan.</p></article>`;
    return;
  }

  report.action_plans.forEach((plan) => {
    const card = document.createElement("article");
    card.className = "stack-card";
    const commands = plan.commands.map((command) => `<li><code>${command}</code></li>`).join("");
    card.innerHTML = `
      <div class="stack-topline">
        <h3>${plan.title}</h3>
        <span class="pill">${plan.risk} risk</span>
      </div>
      <p>${plan.expected_effect}</p>
      <p>Requires privilege: ${plan.requires_privilege ? "yes" : "no"} · Reversible: ${plan.reversible ? "yes" : "no"} · Execution enabled: ${plan.execution_enabled ? "yes" : "no"}</p>
      <ul class="text-list compact-list">${commands}</ul>
      <p>${plan.approval_prompt}</p>
    `;
    maintenancePlans.appendChild(card);
  });
}

function renderRequestPlan(plan) {
  const commands = plan.commands.length
    ? plan.commands.map((command) => `<li><code>${command}</code></li>`).join("")
    : "<li>No commands prepared yet.</li>";
  const manualSteps = plan.manual_steps.map((step) => `<li>${step}</li>`).join("");
  const rollback = plan.rollback.map((step) => `<li>${step}</li>`).join("");
  requestPlan.innerHTML = `
    <article class="stack-card">
      <div class="stack-topline">
        <h3>${plan.title}</h3>
        <span class="pill">${plan.platform}</span>
      </div>
      <p>${plan.summary}</p>
      <p>Risk: ${plan.risk} · Requires privilege: ${plan.requires_privilege ? "yes" : "no"} · Reversible: ${plan.reversible ? "yes" : "no"} · Execution enabled: ${plan.execution_enabled ? "yes" : "no"}</p>
      <p><strong>Commands</strong></p>
      <ul class="text-list compact-list">${commands}</ul>
      <p><strong>Manual steps</strong></p>
      <ul class="text-list compact-list">${manualSteps}</ul>
      <p><strong>Rollback</strong></p>
      <ul class="text-list compact-list">${rollback}</ul>
      <p>${plan.approval_prompt}</p>
    </article>
  `;
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
    "System Stack Review and Coach",
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
      }),
    });
    if (!response.ok) {
      throw new Error(`Request plan failed with status ${response.status}`);
    }
    currentRequestPlan = await response.json();
    renderRequestPlan(currentRequestPlan);
    appendCoachMessage("Plan", `${currentRequestPlan.title}\nExecution enabled: ${currentRequestPlan.execution_enabled}`);
    setStatus("Approval-required plan prepared. No change was executed.");
  } catch (error) {
    console.error(error);
    setStatus(`Request plan failed: ${error.message}`);
  } finally {
    prepareRequestButton.disabled = false;
  }
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
prepareRequestButton.addEventListener("click", prepareRequestPlan);
askCoachButton.addEventListener("click", askCoach);
loadScanOptions().catch((error) => {
  console.error(error);
  setStatus(`Could not load scan options: ${error.message}`);
});
runReview();
runMaintenance();
