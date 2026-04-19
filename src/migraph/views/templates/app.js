// mviz · Migration Visualizer

let initialData = null;
let currentData = null;
let selectedRevision = null;

// Utilities
function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function setStatus(message, isError = false) {
  const statusText = document.getElementById("status");
  const statusIndicator = document.getElementById("statusIndicator");
  statusText.textContent = message;
  statusText.className = isError ? "status-text error" : "status-text";
  statusIndicator.className = isError 
    ? "status-indicator error" 
    : message.includes("...") 
      ? "status-indicator active" 
      : "status-indicator ready";
}

function setBadgeList(id, values, type = "") {
  const root = document.getElementById(id);
  root.innerHTML = "";
  if (!values || !values.length) {
    const el = document.createElement("div");
    el.className = "empty-state";
    el.textContent = "None";
    root.appendChild(el);
    return;
  }
  for (const value of values) {
    const el = document.createElement("span");
    el.className = type ? `badge ${type}` : "badge";
    el.textContent = value;
    el.title = value;
    root.appendChild(el);
  }
}

function shorten(value, maxLength) {
  if (!value) return "";
  if (value.length <= maxLength) return value;
  return `${value.slice(0, maxLength - 1)}…`;
}

// Graph Helpers
function findNode(revision) {
  return (
    currentData.layout.nodes.find((entry) => entry.revision === revision) ||
    null
  );
}

function findMigration(revision) {
  return (
    currentData.graph.migrations.find((entry) => entry.revision === revision) ||
    null
  );
}

function findInitialMigration(revision) {
  return (
    initialData?.graph?.migrations?.find((entry) => entry.revision === revision) ||
    null
  );
}

function currentParentLabel(migration) {
  if (!migration) return "None";
  if (Array.isArray(migration.down_revision))
    return migration.down_revision.join(", ");
  return migration.down_revision || "root";
}

function getAllRevisions() {
  return currentData?.graph?.migrations?.map(m => m.revision) || [];
}

// SVG Path Calculations
const ARROW_SIZE = 7; // matches marker refX

function edgePath(from, to, nodeWidth, nodeHeight) {
  const startX = from.x + nodeWidth / 2;
  const endX = to.x + nodeWidth / 2;
  const goingDown = from.y <= to.y;
  const startY = goingDown ? from.y + nodeHeight : from.y;
  // Pull endpoint back by arrow size so the arrowhead tip lands at the node rect edge
  const endY = goingDown
    ? to.y - ARROW_SIZE
    : to.y + nodeHeight + ARROW_SIZE;
  const bend = Math.max(40, Math.abs(endY - startY) / 2);
  const control1Y = goingDown ? startY + bend : startY - bend;
  const control2Y = goingDown ? endY - bend : endY + bend;
  return `M ${startX} ${startY} C ${startX} ${control1Y}, ${endX} ${control2Y}, ${endX} ${endY}`;
}

function positionInitialViewport() {
  const container = document.getElementById("graphContainer");
  if (!container || !currentData?.layout) return;

  const canvas = currentData.layout.canvas;
  container.scrollLeft = Math.max(0, (canvas.width - container.clientWidth) / 2);
  container.scrollTop = 0;
}

function isDetachedNode(revision) {
  const initialMigration = findInitialMigration(revision);
  const migration = findMigration(revision);
  return Boolean(initialMigration?.down_revision != null && migration?.down_revision == null);
}

function pinDetachedNodePosition(revision) {
  const node = findNode(revision);
  if (!node || !currentData?.graph?.ui_state) return;

  currentData.graph.ui_state.positions[revision] = { x: node.x, y: node.y };
  if (!currentData.graph.ui_state.pinned.includes(revision)) {
    currentData.graph.ui_state.pinned.push(revision);
  }
}

function clearPinnedNodePosition(revision) {
  if (!currentData?.graph?.ui_state?.positions) return;
  delete currentData.graph.ui_state.positions[revision];
  currentData.graph.ui_state.pinned = currentData.graph.ui_state.pinned.filter(
    (entry) => entry !== revision
  );
}

function ensureNodeVisible(revision) {
  const container = document.getElementById("graphContainer");
  const node = findNode(revision);
  if (!container || !node || !currentData?.layout) return;

  const { node_width: nodeWidth, node_height: nodeHeight } = currentData.layout;
  const padding = 24;
  const left = node.x - padding;
  const right = node.x + nodeWidth + padding;
  const top = node.y - padding;
  const bottom = node.y + nodeHeight + padding;

  if (left < container.scrollLeft) {
    container.scrollLeft = Math.max(0, left);
  } else if (right > container.scrollLeft + container.clientWidth) {
    container.scrollLeft = Math.max(0, right - container.clientWidth);
  }

  if (top < container.scrollTop) {
    container.scrollTop = Math.max(0, top);
  } else if (bottom > container.scrollTop + container.clientHeight) {
    container.scrollTop = Math.max(0, bottom - container.clientHeight);
  }
}

// State Management
function setSelectedRevision(revision) {
  selectedRevision = revision;
  renderSelectedNodePanel();
  renderGraph(currentData);

  // Update button states
  document.getElementById("clearSelectionButton").disabled = !revision;
  const migration = revision ? findMigration(revision) : null;
  document.getElementById("detachButton").disabled = !migration || migration.down_revision == null;

  if (revision) {
    setStatus(`${shorten(revision, 16)} selected · click another node to set as its parent`);
  }
}

function updateParent(revision, parentRevision) {
  const migration = findMigration(revision);
  if (!migration) return;

  if (parentRevision == null) {
    pinDetachedNodePosition(revision);
  } else {
    clearPinnedNodePosition(revision);
  }

  migration.down_revision = parentRevision;
}

// Rendering
function renderSelectedNodePanel() {
  const selectedNode = document.getElementById("selectedNode");
  const migration = selectedRevision ? findMigration(selectedRevision) : null;

  if (!migration) {
    selectedNode.innerHTML = '<div class="empty-state">Click a node to inspect</div>';
    return;
  }

  const parent = currentParentLabel(migration);
  const allRevisions = getAllRevisions().filter(r => r !== migration.revision);
  
  // Build parent selector options
  const options = [
    '<option value="">-- None (root) --</option>',
    ...allRevisions.map(r => {
      const isSelected = (Array.isArray(migration.down_revision) 
        ? migration.down_revision.includes(r)
        : migration.down_revision === r);
      return `<option value="${r}" ${isSelected ? 'selected' : ''}>${r}</option>`;
    })
  ].join('');
  
  selectedNode.innerHTML = `
    <div class="detail-row">
      <span class="detail-label">Revision</span>
      <span class="detail-value">${migration.revision}</span>
    </div>
    <div class="detail-row">
      <span class="detail-label">Parent</span>
      <select id="parentSelect" class="detail-value" style="font-family: var(--font-mono); font-size: 11px; background: var(--bg-tertiary); color: var(--text-primary); border: 1px solid var(--border); padding: 4px; width: 100%;">
        ${options}
      </select>
    </div>
    <div class="detail-row">
      <span class="detail-label">Path</span>
      <span class="detail-value">${migration.path}</span>
    </div>
  `;
  
  // Bind change event to parent selector
  const select = document.getElementById("parentSelect");
  if (select) {
    select.addEventListener("change", async (e) => {
      const newParent = e.target.value || null;
      updateParent(migration.revision, newParent);
      try {
        const parentLabel = newParent || "root";
        await previewGraph(`Updated parent → ${shorten(parentLabel, 20)}`);
      } catch (error) {
        setStatus(`Failed to update parent: ${error.message}`, true);
      }
    });
  }
}

function renderGraph(data) {
  const app = document.getElementById("app");

  // Update header stats
  document.getElementById("source").textContent = data.graph.source_directory || "Unknown";
  document.getElementById("count").textContent = String(data.summary.migrations_count || 0);
  document.getElementById("headsCount").textContent = String(data.summary.heads?.length || 0);
  document.getElementById("orphansCount").textContent = String(data.summary.orphans?.length || 0);
  document.getElementById("cyclesCount").textContent = String(data.summary.cycles?.length || 0);
  
  // Update badge lists
  setBadgeList("heads", data.summary.heads, "head");
  setBadgeList("orphans", data.summary.orphans, "orphan");

  // Empty state
  if (!data.layout.nodes.length) {
    app.className = "empty-state-container";
    app.innerHTML = `
      <div class="empty-state-container">
        <div class="empty-state-message">
          <div class="icon">∅</div>
          <div>No migrations found</div>
        </div>
      </div>
    `;
    return;
  }

  app.className = "graph-canvas";

  const nodeWidth = data.layout.node_width;
  const nodeHeight = data.layout.node_height;
  const nodes = new Map(data.layout.nodes.map((node) => [node.revision, node]));
  const svg = [];

  svg.push(
    `<svg width="${data.layout.canvas.width}" height="${data.layout.canvas.height}" viewBox="0 0 ${data.layout.canvas.width} ${data.layout.canvas.height}" xmlns="http://www.w3.org/2000/svg">`
  );

  svg.push(`<defs>
    <marker id="arrowhead" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto" markerUnits="userSpaceOnUse">
      <polygon points="0 0, 8 3, 0 6" fill="context-stroke" />
    </marker>
  </defs>`);

  // Draw edges
  for (const edge of data.layout.edges) {
    const from = nodes.get(edge.from);
    const to = nodes.get(edge.to);
    if (!from || !to) continue;
    svg.push(
      `<path class="edge" d="${edgePath(from, to, nodeWidth, nodeHeight)}" marker-end="url(#arrowhead)" />`
    );
  }

  // Draw nodes
  for (const node of data.layout.nodes) {
    const classes = ["node"];
    if (node.is_head) classes.push("head");
    if (node.is_orphan) classes.push("orphan");
    if (node.in_cycle) classes.push("cycle");
    if (isDetachedNode(node.revision)) classes.push("detached");
    if (selectedRevision === node.revision) classes.push("selected");

    const description = shorten(node.description || node.path, 32);
    const revision = shorten(node.revision, 20);
    const parentText = Array.isArray(node.down_revision)
      ? node.down_revision.join(", ")
      : node.down_revision || "root";

    svg.push(
      `<g class="${classes.join(" ")}" data-revision="${node.revision}" transform="translate(${node.x}, ${node.y})" style="cursor: pointer">`
    );
    svg.push(
      `<title>${node.revision}
${node.description || node.path}
parent: ${parentText}</title>`
    );
    svg.push(`<rect width="${nodeWidth}" height="${nodeHeight}" />`);
    
    // Text labels
    svg.push(`<text class="node-title" x="12" y="26">${revision}</text>`);
    svg.push(`<text class="node-meta" x="12" y="44">${description}</text>`);
    svg.push(
      `<text class="node-meta" x="12" y="58">← ${shorten(parentText, 24)}</text>`
    );
    
    svg.push(`</g>`);
  }
  
  svg.push("</svg>");
  app.innerHTML = svg.join("");
}

// API Calls
async function previewGraph(message) {
  const response = await fetch("/api/preview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(currentData.graph),
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.message || "Preview failed");
  }
  currentData = payload;
  renderSelectedNodePanel();
  renderGraph(currentData);
  if (selectedRevision) {
    requestAnimationFrame(() => ensureNodeVisible(selectedRevision));
  }
  if (message) {
    setStatus(message);
  }
}

async function exportGraph() {
  const button = document.getElementById("exportButton");
  button.disabled = true;
  setStatus("Exporting graph...");

  try {
    const response = await fetch("/api/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(currentData.graph),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.message || "Export failed");
    }
    if (!payload.output_file) {
      downloadGraph(currentData.graph);
      setStatus("Graph downloaded as mviz-export.json");
    } else {
      setStatus(`Exported to ${payload.output_file}`);
    }
  } catch (error) {
    setStatus(`Export failed: ${error.message}`, true);
  } finally {
    button.disabled = false;
  }
}

async function applyGraph() {
  const button = document.getElementById("applyButton");
  button.disabled = true;
  setStatus("Applying changes to repository...");

  try {
    const response = await fetch("/api/apply", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(currentData.graph),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.message || "Apply failed");
    }
    const changed = payload.data ? payload.data.changed_files_count : 0;
    setStatus(
      `Applied ${changed} file${changed === 1 ? "" : "s"} to repository`
    );
  } catch (error) {
    setStatus(`Apply failed: ${error.message}`, true);
  } finally {
    button.disabled = false;
  }
}

function downloadGraph(graph) {
  const blob = new Blob([JSON.stringify(graph, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "mviz-export.json";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

// Actions
async function refreshFromDisk() {
  const button = document.getElementById("refreshButton");
  button.disabled = true;
  setStatus("Refreshing from disk...");

  try {
    const response = await fetch("/api/refresh");
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.message || "Refresh failed");
    }
    initialData = clone(payload);
    currentData = clone(payload);
    selectedRevision = null;
    renderSelectedNodePanel();
    renderGraph(currentData);
    requestAnimationFrame(positionInitialViewport);
    setStatus("Refreshed from disk");
  } catch (error) {
    setStatus(`Refresh failed: ${error.message}`, true);
  } finally {
    button.disabled = false;
  }
}

function resetLayout() {
  if (!initialData) return;
  currentData = clone(initialData);
  currentData.graph.ui_state.positions = {};
  currentData.graph.ui_state.pinned = [];
  selectedRevision = null;
  renderSelectedNodePanel();
  renderGraph(currentData);
  setStatus("Layout reset to automatic positioning");
}

async function autoFormatLayout() {
  if (!currentData) return;

  currentData.graph.ui_state.positions = {};
  currentData.graph.ui_state.pinned = [];

  try {
    await previewGraph("Graph auto-formatted");
  } catch (error) {
    setStatus(`Auto-format failed: ${error.message}`, true);
  }
}

async function detachSelectedParent() {
  if (!selectedRevision) return;
  updateParent(selectedRevision, null);
  try {
    await previewGraph(`Detached parent from ${shorten(selectedRevision, 12)}`);
  } catch (error) {
    setStatus(`Detach failed: ${error.message}`, true);
  }
}

// Event Binding
function bindInteractions() {
  const app = document.getElementById("app");

  app.addEventListener("click", (event) => {
    const nodeEl = event.target.closest("[data-revision]");

    if (!nodeEl) {
      // Click on empty canvas → deselect
      setSelectedRevision(null);
      return;
    }

    const revision = nodeEl.dataset.revision;

    if (selectedRevision === revision) {
      // Click same node → cancel selection
      setSelectedRevision(null);
    } else if (selectedRevision) {
      // Second node clicked → set it as parent of the first selected node
      const child = selectedRevision;
      const parent = revision;
      updateParent(child, parent);
      setSelectedRevision(null);
      previewGraph(`Set parent of ${shorten(child, 12)} → ${shorten(parent, 12)}`)
        .catch((error) => setStatus(`Failed to rewire: ${error.message}`, true));
    } else {
      // Nothing selected → select this node
      setSelectedRevision(revision);
    }
  });
}

// Initialization
document.getElementById("exportButton").addEventListener("click", exportGraph);
document.getElementById("applyButton").addEventListener("click", applyGraph);
document.getElementById("refreshButton").addEventListener("click", refreshFromDisk);
document.getElementById("autoFormatButton").addEventListener("click", autoFormatLayout);
document.getElementById("resetButton").addEventListener("click", resetLayout);
document
  .getElementById("detachButton")
  .addEventListener("click", detachSelectedParent);
document
  .getElementById("clearSelectionButton")
  .addEventListener("click", () => setSelectedRevision(null));

bindInteractions();

fetch("/api/graph")
  .then((response) => response.json())
  .then((payload) => {
    initialData = clone(payload);
    currentData = clone(payload);
    renderSelectedNodePanel();
    renderGraph(currentData);
    requestAnimationFrame(positionInitialViewport);
    setStatus("Ready · Click a node to rewire its parent");
  })
  .catch((error) => {
    document.getElementById("app").innerHTML = `
      <div class="empty-state-container">
        <div class="empty-state-message">
          <div class="icon">✕</div>
          <div>Failed to load graph</div>
          <div style="margin-top: 8px; font-size: 12px;">${error.message}</div>
        </div>
      </div>
    `;
    setStatus(`Error: ${error.message}`, true);
  });
