// Alembic Viz - Browser UI Controller

let initialData = null;
let currentData = null;
let selectedRevision = null;
let activeGesture = null;

// Utils
function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function setStatus(message, isError = false) {
  const status = document.getElementById("status");
  status.textContent = message;
  status.style.color = isError ? "#ff8d9d" : "var(--muted)";
}

function setList(id, values) {
  const root = document.getElementById(id);
  root.innerHTML = "";
  if (!values.length) {
    const el = document.createElement("span");
    el.className = "muted";
    el.textContent = "None";
    root.appendChild(el);
    return;
  }
  for (const value of values) {
    const el = document.createElement("span");
    el.className = "pill";
    el.textContent = value;
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

function currentParentLabel(migration) {
  if (!migration) return "None";
  if (Array.isArray(migration.down_revision))
    return migration.down_revision.join(", ");
  return migration.down_revision || "root";
}

// SVG Path Calculations
function edgePath(from, to, nodeWidth, nodeHeight) {
  const startX = from.x + nodeWidth / 2;
  const endX = to.x + nodeWidth / 2;
  const goingDown = from.y <= to.y;
  const startY = goingDown ? from.y + nodeHeight : from.y;
  const endY = goingDown ? to.y : to.y + nodeHeight;
  const bend = Math.max(40, Math.abs(endY - startY) / 2);
  const control1Y = goingDown ? startY + bend : startY - bend;
  const control2Y = goingDown ? endY - bend : endY + bend;
  return `M ${startX} ${startY} C ${startX} ${control1Y}, ${endX} ${control2Y}, ${endX} ${endY}`;
}

function tempEdgePath(from, point, nodeWidth, nodeHeight) {
  const startX = from.x + nodeWidth / 2;
  const startY = from.y + nodeHeight;
  const endX = point.x;
  const endY = point.y;
  const bend = Math.max(40, Math.abs(endY - startY) / 2);
  const goingDown = startY <= endY;
  const control1Y = goingDown ? startY + bend : startY - bend;
  const control2Y = goingDown ? endY - bend : endY + bend;
  return `M ${startX} ${startY} C ${startX} ${control1Y}, ${endX} ${control2Y}, ${endX} ${endY}`;
}

// State Management
function setSelectedRevision(revision) {
  selectedRevision = revision;
  renderSelectedNodePanel();
  renderGraph(currentData);
}

function upsertUiPosition(revision, x, y) {
  currentData.graph.ui_state.positions[revision] = { x, y };
}

function syncNodePosition(revision, x, y) {
  const node = findNode(revision);
  if (!node) return;
  node.x = x;
  node.y = y;
  upsertUiPosition(revision, x, y);
}

function updateParent(revision, parentRevision) {
  const migration = findMigration(revision);
  if (!migration) return;
  migration.down_revision = parentRevision;
}

// Rendering
function renderSelectedNodePanel() {
  const selectedNode = document.getElementById("selectedNode");
  const detachButton = document.getElementById("detachButton");
  const clearSelectionButton = document.getElementById("clearSelectionButton");
  const migration = selectedRevision ? findMigration(selectedRevision) : null;

  if (!migration) {
    selectedNode.innerHTML =
      '<div class="muted">Click a node to inspect or detach its parent.</div>';
    detachButton.disabled = true;
    clearSelectionButton.disabled = true;
    return;
  }

  detachButton.disabled = migration.down_revision == null;
  clearSelectionButton.disabled = false;
  selectedNode.innerHTML = [
    `<div><strong>Revision</strong>${migration.revision}</div>`,
    `<div><strong>Parent</strong>${currentParentLabel(migration)}</div>`,
    `<div><strong>Path</strong>${migration.path}</div>`,
  ].join("");
}

function renderGraph(data) {
  document.getElementById("source").textContent = data.graph.source_directory;
  document.getElementById("count").textContent = String(
    data.summary.migrations_count,
  );
  document.getElementById("headsCount").textContent = String(
    data.summary.heads.length,
  );
  document.getElementById("orphansCount").textContent = String(
    data.summary.orphans.length,
  );
  document.getElementById("cyclesCount").textContent = String(
    data.summary.cycles.length,
  );
  setList("heads", data.summary.heads);
  setList("orphans", data.summary.orphans);

  if (!data.layout.nodes.length) {
    document.getElementById("app").textContent = "No migrations found.";
    return;
  }

  const nodeWidth = data.layout.node_width;
  const nodeHeight = data.layout.node_height;
  const nodes = new Map(data.layout.nodes.map((node) => [node.revision, node]));
  const svg = [];

  svg.push(
    `<svg width="${data.layout.canvas.width}" height="${data.layout.canvas.height}" viewBox="0 0 ${data.layout.canvas.width} ${data.layout.canvas.height}" xmlns="http://www.w3.org/2000/svg">`,
  );

  // Draw edges
  for (const edge of data.layout.edges) {
    const from = nodes.get(edge.from);
    const to = nodes.get(edge.to);
    if (!from || !to) continue;
    svg.push(
      `<path class="edge" d="${edgePath(from, to, nodeWidth, nodeHeight)}" />`,
    );
  }

  // Draw temporary edge during connect gesture
  if (activeGesture && activeGesture.type === "connect") {
    const from = nodes.get(activeGesture.revision);
    if (from) {
      svg.push(
        `<path class="edge temp" d="${tempEdgePath(from, activeGesture.pointer, nodeWidth, nodeHeight)}" />`,
      );
    }
  }

  // Draw nodes
  for (const node of data.layout.nodes) {
    const classes = ["node"];
    if (node.is_head) classes.push("head");
    if (node.is_orphan) classes.push("orphan");
    if (node.in_cycle) classes.push("cycle");
    if (selectedRevision === node.revision) classes.push("selected");
    if (
      activeGesture &&
      activeGesture.type === "connect" &&
      activeGesture.hoverTarget === node.revision &&
      activeGesture.revision !== node.revision
    ) {
      classes.push("drop-target");
    }

    const description = shorten(node.description || node.path, 28);
    const revision = shorten(node.revision, 22);
    const parentText = Array.isArray(node.down_revision)
      ? node.down_revision.join(", ")
      : node.down_revision || "root";

    svg.push(
      `<g class="${classes.join(" ")}" data-revision="${node.revision}" style="cursor: grab" transform="translate(${node.x}, ${node.y})">`,
    );
    svg.push(
      `<title>${node.revision}\n${node.description || node.path}\nparent: ${parentText}</title>`,
    );
    svg.push(`<rect width="${nodeWidth}" height="${nodeHeight}" />`);
    svg.push(
      `<circle class="connect-handle" data-connect-revision="${node.revision}" cx="${Math.round(nodeWidth / 2)}" cy="${nodeHeight - 8}" r="7" />`,
    );
    svg.push(`<text class="node-title" x="14" y="28">${revision}</text>`);
    svg.push(`<text class="node-subtitle" x="14" y="50">${description}</text>`);
    svg.push(
      `<text class="node-subtitle" x="14" y="64">${shorten(node.path, 28)}</text>`,
    );
    svg.push(`</g>`);
  }
  svg.push("</svg>");
  document.getElementById("app").innerHTML = svg.join("");
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
  if (message) {
    setStatus(message);
  }
}

async function exportGraph() {
  const button = document.getElementById("exportButton");
  button.disabled = true;
  setStatus("Saving graph...");

  try {
    const response = await fetch("/api/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(currentData.graph),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.message || "Save failed");
    }
    if (!payload.output_file) {
      downloadGraph(currentData.graph);
      setStatus("Graph downloaded as graph-state.json");
    } else {
      setStatus(`Graph exported to ${payload.output_file}`);
    }
  } catch (error) {
    setStatus(`Failed to export graph: ${error}`, true);
  } finally {
    button.disabled = false;
  }
}

async function applyGraph() {
  const button = document.getElementById("applyButton");
  button.disabled = true;
  setStatus("Applying graph to repository...");

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
      `Applied graph to repo. Updated ${changed} file${changed === 1 ? "" : "s"}.`,
    );
  } catch (error) {
    setStatus(`Failed to apply graph: ${error}`, true);
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
  link.download = "graph-state.json";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

// Actions
function resetLayout() {
  if (!initialData) return;
  currentData = clone(initialData);
  currentData.graph.ui_state.positions = {};
  selectedRevision = null;
  renderSelectedNodePanel();
  renderGraph(currentData);
  setStatus("Layout reset to auto-positioned state.");
}

async function detachSelectedParent() {
  if (!selectedRevision) return;
  updateParent(selectedRevision, null);
  try {
    await previewGraph(`Detached parent from ${selectedRevision}`);
  } catch (error) {
    setStatus(`Failed to detach parent: ${error}`, true);
  }
}

// Gestures
function graphPointFromEvent(event) {
  const graphWrap = document.querySelector(".graph-wrap");
  const rect = graphWrap.getBoundingClientRect();
  return {
    x: graphWrap.scrollLeft + event.clientX - rect.left,
    y: graphWrap.scrollTop + event.clientY - rect.top,
  };
}

function beginMove(revision, event) {
  const node = findNode(revision);
  if (!node) return;
  activeGesture = {
    type: "move",
    revision,
    startPointerX: event.clientX,
    startPointerY: event.clientY,
    startX: node.x,
    startY: node.y,
  };
  setSelectedRevision(revision);
  setStatus(`Dragging ${revision}`);
}

function beginConnect(revision, event) {
  const node = findNode(revision);
  if (!node) return;
  activeGesture = {
    type: "connect",
    revision,
    pointer: graphPointFromEvent(event),
    hoverTarget: null,
  };
  setSelectedRevision(revision);
  renderGraph(currentData);
  setStatus(`Drop ${revision} onto a new parent node below it.`);
}

async function completeConnect(targetRevision) {
  if (!activeGesture || activeGesture.type !== "connect") return;
  const childRevision = activeGesture.revision;
  activeGesture = null;

  if (!targetRevision) {
    renderGraph(currentData);
    setStatus(`Reparent cancelled for ${childRevision}`);
    return;
  }
  if (targetRevision === childRevision) {
    renderGraph(currentData);
    setStatus("A migration cannot depend on itself.", true);
    return;
  }

  updateParent(childRevision, targetRevision);
  try {
    await previewGraph(
      `Updated parent of ${childRevision} to ${targetRevision}`,
    );
  } catch (error) {
    setStatus(`Failed to update parent: ${error}`, true);
  }
}

// Event Binding
function bindInteractions() {
  const app = document.getElementById("app");

  app.addEventListener("pointerdown", (event) => {
    const handle = event.target.closest("[data-connect-revision]");
    if (handle) {
      event.preventDefault();
      event.stopPropagation();
      beginConnect(handle.dataset.connectRevision, event);
      return;
    }

    const node = event.target.closest("[data-revision]");
    if (!node || event.button !== 0) return;
    beginMove(node.dataset.revision, event);
  });

  app.addEventListener("click", (event) => {
    const node = event.target.closest("[data-revision]");
    if (node) {
      setSelectedRevision(node.dataset.revision);
    }
  });

  window.addEventListener("pointermove", (event) => {
    if (!activeGesture) return;

    if (activeGesture.type === "move") {
      const graphWrap = document.querySelector(".graph-wrap");
      const deltaX =
        event.clientX - activeGesture.startPointerX + graphWrap.scrollLeft;
      const deltaY =
        event.clientY - activeGesture.startPointerY + graphWrap.scrollTop;
      syncNodePosition(
        activeGesture.revision,
        Math.max(20, Math.round(activeGesture.startX + deltaX)),
        Math.max(20, Math.round(activeGesture.startY + deltaY)),
      );
      renderGraph(currentData);
      return;
    }

    if (activeGesture.type === "connect") {
      activeGesture.pointer = graphPointFromEvent(event);
      const target = event.target.closest
        ? event.target.closest("[data-revision]")
        : null;
      activeGesture.hoverTarget = target ? target.dataset.revision : null;
      renderGraph(currentData);
    }
  });

  window.addEventListener("pointerup", async (event) => {
    if (!activeGesture) return;

    if (activeGesture.type === "move") {
      const revision = activeGesture.revision;
      activeGesture = null;
      setStatus(`Position saved for ${revision}`);
      return;
    }

    if (activeGesture.type === "connect") {
      const target = event.target.closest
        ? event.target.closest("[data-revision]")
        : null;
      await completeConnect(target ? target.dataset.revision : null);
    }
  });
}

// Initialization
document.getElementById("exportButton").addEventListener("click", exportGraph);
document.getElementById("applyButton").addEventListener("click", applyGraph);
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
    setStatus(
      "Drag nodes to move them. Drag the gold bottom handle onto another node to reparent.",
    );
  })
  .catch((error) => {
    document.getElementById("app").textContent =
      `Failed to load graph: ${error}`;
    setStatus(`Failed to load graph: ${error}`, true);
  });
