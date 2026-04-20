// mviz · Migration Visualizer

let initialData = null;
let currentData = null;
let selectedRevision = null;
let cy = null;
let lockedPanX = null;

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
  return currentData?.graph?.migrations?.map((m) => m.revision) || [];
}

function isDetachedNode(revision) {
  const initialMigration = findInitialMigration(revision);
  const migration = findMigration(revision);
  return Boolean(
    initialMigration?.down_revision != null && migration?.down_revision == null
  );
}

function isChangedNode(revision) {
  const initialMigration = findInitialMigration(revision);
  const migration = findMigration(revision);
  if (!initialMigration || !migration) return false;
  if (migration.down_revision == null) return false;
  const serialize = (value) =>
    Array.isArray(value) ? JSON.stringify([...value].sort()) : value ?? null;
  return serialize(initialMigration.down_revision) !== serialize(migration.down_revision);
}

// State Management
function setSelectedRevision(revision) {
  selectedRevision = revision;
  renderSelectedNodePanel();
  refreshNodeClasses();

  document.getElementById("clearSelectionButton").disabled = !revision;
  const migration = revision ? findMigration(revision) : null;
  document.getElementById("detachButton").disabled =
    !migration || migration.down_revision == null;

  if (revision) {
    setStatus(
      `${shorten(revision, 16)} selected · click another node to set as its parent`
    );
  }
}

function updateParent(revision, parentRevision) {
  const migration = findMigration(revision);
  if (!migration) return;
  migration.down_revision = parentRevision;
}

// Cytoscape
const CY_STYLE = [
  {
    selector: "node",
    style: {
      shape: "rectangle",
      width: 220,
      height: 72,
      "background-color": "#1a1a1d",
      "border-color": "#3a3a3f",
      "border-width": 1,
      label: "data(label)",
      "text-wrap": "wrap",
      "text-valign": "center",
      "text-halign": "center",
      "font-family": "JetBrains Mono, monospace",
      "font-size": 11,
      color: "#fafafa",
      "text-max-width": 196,
      "line-height": 1.4,
    },
  },
  {
    selector: "node:hover",
    style: { "border-color": "#a0a0a8" },
  },
  {
    selector: "node.head",
    style: {
      "background-color": "#00ff88",
      "background-opacity": 0.12,
      "border-color": "#00ff88",
      color: "#fafafa",
    },
  },
  {
    selector: "node.orphan",
    style: {
      "background-color": "#ffaa00",
      "background-opacity": 0.12,
      "border-color": "#ffaa00",
      color: "#fafafa",
    },
  },
  {
    selector: "node.cycle",
    style: {
      "background-color": "#ff0066",
      "background-opacity": 0.12,
      "border-color": "#ff0066",
      "border-width": 2,
      color: "#fafafa",
    },
  },
  {
    selector: "node.changed",
    style: {
      "background-color": "#a78bfa",
      "background-opacity": 0.12,
      "border-color": "#a78bfa",
      "border-width": 2,
      color: "#fafafa",
    },
  },
  {
    selector: "node.detached",
    style: {
      "background-color": "#ff3333",
      "background-opacity": 0.12,
      "border-color": "#ff3333",
      "border-width": 2,
      "border-style": "dashed",
      color: "#fafafa",
    },
  },
  {
    selector: "node.selected",
    style: {
      "background-color": "#00d4ff",
      "background-opacity": 0.12,
      "border-color": "#00d4ff",
      "border-width": 2,
      color: "#fafafa",
    },
  },
  {
    selector: "node.selected.detached",
    style: {
      "background-color": "#00d4ff",
      "background-opacity": 0.12,
      "border-color": "#ff3333",
      "border-style": "dashed",
      color: "#fafafa",
    },
  },
  {
    selector: "edge",
    style: {
      "curve-style": "bezier",
      "target-arrow-shape": "triangle",
      "line-color": "#404048",
      "target-arrow-color": "#404048",
      width: 1.5,
      "arrow-scale": 1.2,
    },
  },
];

function nodeLabel(node) {
  const revision = shorten(node.revision, 20);
  const description = shorten(node.description || node.path, 30);
  const parentText = Array.isArray(node.down_revision)
    ? node.down_revision.join(", ")
    : node.down_revision || "root";
  return `${revision}\n${description}\n\u2190 ${shorten(parentText, 24)}`;
}

function nodeClasses(node) {
  const classes = [];
  if (node.is_head) classes.push("head");
  if (node.is_orphan) classes.push("orphan");
  if (node.in_cycle) classes.push("cycle");
  if (isDetachedNode(node.revision)) classes.push("detached");
  else if (isChangedNode(node.revision)) classes.push("changed");
  return classes;
}

function initCytoscape() {
  const container = document.getElementById("app");
  container.className = "";
  container.innerHTML = "";

  if (typeof cytoscapeDagre !== "undefined") {
    cytoscape.use(cytoscapeDagre);
  }

  cy = cytoscape({
    container,
    style: CY_STYLE,
    layout: { name: "preset" },
    userZoomingEnabled: false,
    userPanningEnabled: true,
    boxSelectionEnabled: false,
    minZoom: 0.1,
    maxZoom: 3,
  });

  container.addEventListener(
    "wheel",
    (e) => {
      e.preventDefault();
      if (e.ctrlKey || e.metaKey) {
        const zoomFactor = Math.exp(-e.deltaY * 0.002);
        const rect = container.getBoundingClientRect();
        cy.zoom({
          level: cy.zoom() * zoomFactor,
          renderedPosition: {
            x: e.clientX - rect.left,
            y: e.clientY - rect.top,
          },
        });
        lockedPanX = cy.pan().x;
      } else {
        const currentPan = cy.pan();
        cy.pan({
          x: currentPan.x,
          y: currentPan.y - e.deltaY,
        });
      }
    },
    { passive: false }
  );

  cy.on("pan", () => {
    if (lockedPanX === null) return;
    const p = cy.pan();
    if (p.x !== lockedPanX) {
      cy.pan({ x: lockedPanX, y: p.y });
    }
  });

  cy.on("tap", "node", (evt) => {
    const revision = evt.target.id();
    if (selectedRevision === revision) {
      setSelectedRevision(null);
    } else if (selectedRevision) {
      const child = selectedRevision;
      const parent = revision;
      updateParent(child, parent);
      setSelectedRevision(null);
      previewGraph(
        `Set parent of ${shorten(child, 12)} \u2192 ${shorten(parent, 12)}`
      ).catch((err) => setStatus(`Failed to rewire: ${err.message}`, true));
    } else {
      setSelectedRevision(revision);
    }
  });

  cy.on("tap", (evt) => {
    if (evt.target === cy) {
      setSelectedRevision(null);
    }
  });
}

function refreshNodeClasses() {
  if (!cy) return;
  cy.nodes().forEach((node) => node.removeClass("selected"));
  if (selectedRevision) {
    cy.$(`#${CSS.escape(selectedRevision)}`).addClass("selected");
  }
}

function loadGraph(data, { fit = false } = {}) {
  updateSidebar(data);

  if (!data.nodes || !data.nodes.length) {
    const app = document.getElementById("app");
    if (cy) {
      cy.destroy();
      cy = null;
    }
    app.className = "empty-state-container";
    app.innerHTML = `
      <div class="empty-state-message">
        <div class="icon">\u2205</div>
        <div>No migrations found</div>
      </div>
    `;
    return;
  }

  if (!cy) initCytoscape();

  cy.batch(() => {
    cy.elements().remove();

    for (const node of data.nodes) {
      cy.add({
        group: "nodes",
        data: {
          id: node.revision,
          label: nodeLabel(node),
          down_revision: node.down_revision,
          path: node.path,
          description: node.description,
        },
        classes: nodeClasses(node),
      });
    }

    for (const edge of data.edges) {
      cy.add({
        group: "edges",
        data: {
          id: `${edge.source}__${edge.target}`,
          source: edge.source,
          target: edge.target,
        },
      });
    }

    if (selectedRevision) {
      cy.$(`#${CSS.escape(selectedRevision)}`).addClass("selected");
    }
  });

  const previousZoom = fit ? null : cy.zoom();
  const previousPan = fit ? null : { ...cy.pan() };
  lockedPanX = null;

  cy.layout({
    name: "dagre",
    rankDir: "BT",
    nodeSep: 40,
    rankSep: 100,
    padding: 80,
  }).run();

  if (fit) {
    cy.fit(undefined, 40);
    if (cy.zoom() < 0.6) {
      cy.zoom(0.85);
      const heads = cy.nodes(".head");
      cy.center(heads.length ? heads : undefined);
    }
  } else {
    cy.zoom(previousZoom);
    cy.pan(previousPan);
  }
  lockedPanX = cy.pan().x;
}

function updateSidebar(data) {
  document.getElementById("source").textContent =
    data.graph.source_directory || "Unknown";
  document.getElementById("count").textContent = String(
    data.summary.migrations_count || 0
  );
  document.getElementById("headsCount").textContent = String(
    data.summary.heads?.length || 0
  );
  document.getElementById("orphansCount").textContent = String(
    data.summary.orphans?.length || 0
  );
  document.getElementById("cyclesCount").textContent = String(
    data.summary.cycles?.length || 0
  );
  setBadgeList("heads", data.summary.heads, "head");
  setBadgeList("orphans", data.summary.orphans, "orphan");
}

// Rendering
function renderSelectedNodePanel() {
  const selectedNode = document.getElementById("selectedNode");
  const migration = selectedRevision ? findMigration(selectedRevision) : null;

  if (!migration) {
    selectedNode.innerHTML =
      '<div class="empty-state">Click a node to inspect</div>';
    return;
  }

  const allRevisions = getAllRevisions().filter(
    (r) => r !== migration.revision
  );

  const noneSelected = migration.down_revision == null;
  const options = [
    `<option value="" ${noneSelected ? "selected" : ""}>-- None (root) --</option>`,
    ...allRevisions.map((r) => {
      const isSelected = Array.isArray(migration.down_revision)
        ? migration.down_revision.includes(r)
        : migration.down_revision === r;
      return `<option value="${r}" ${isSelected ? "selected" : ""}>${r}</option>`;
    }),
  ].join("");

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

  const select = document.getElementById("parentSelect");
  if (select) {
    select.addEventListener("change", async (e) => {
      const newParent = e.target.value || null;
      updateParent(migration.revision, newParent);
      try {
        const parentLabel = newParent || "root";
        await previewGraph(`Updated parent \u2192 ${shorten(parentLabel, 20)}`);
      } catch (error) {
        setStatus(`Failed to update parent: ${error.message}`, true);
      }
    });
  }
}

// API Calls
async function previewGraph(message, { fit = false } = {}) {
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
  loadGraph(currentData, { fit });
  if (message) setStatus(message);
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
    loadGraph(currentData, { fit: true });
    setStatus("Refreshed from disk");
  } catch (error) {
    setStatus(`Refresh failed: ${error.message}`, true);
  } finally {
    button.disabled = false;
  }
}

async function resetLayout() {
  if (!initialData) return;
  currentData = clone(initialData);
  selectedRevision = null;
  try {
    await previewGraph("Reset to initial state", { fit: true });
  } catch (error) {
    setStatus(`Reset failed: ${error.message}`, true);
  }
}

async function autoFormatLayout() {
  if (!currentData) return;
  try {
    await previewGraph("Graph auto-formatted", { fit: true });
  } catch (error) {
    setStatus(`Auto-format failed: ${error.message}`, true);
  }
}

async function detachSelectedParent() {
  if (!selectedRevision) return;
  updateParent(selectedRevision, null);
  try {
    await previewGraph(
      `Detached parent from ${shorten(selectedRevision, 12)}`
    );
  } catch (error) {
    setStatus(`Detach failed: ${error.message}`, true);
  }
}

// Initialization
document.getElementById("exportButton").addEventListener("click", exportGraph);
document.getElementById("applyButton").addEventListener("click", applyGraph);
document.getElementById("refreshButton").addEventListener("click", refreshFromDisk);
document.getElementById("autoFormatButton").addEventListener("click", autoFormatLayout);
document.getElementById("resetButton").addEventListener("click", resetLayout);
document.getElementById("detachButton").addEventListener("click", detachSelectedParent);
document.getElementById("clearSelectionButton").addEventListener("click", () =>
  setSelectedRevision(null)
);

fetch("/api/graph")
  .then((response) => response.json())
  .then((payload) => {
    initialData = clone(payload);
    currentData = clone(payload);
    renderSelectedNodePanel();
    loadGraph(currentData, { fit: true });
    setStatus("Ready \u00b7 Click a node to rewire its parent");
  })
  .catch((error) => {
    document.getElementById("app").innerHTML = `
      <div class="empty-state-container">
        <div class="empty-state-message">
          <div class="icon">\u2715</div>
          <div>Failed to load graph</div>
          <div style="margin-top: 8px; font-size: 12px;">${error.message}</div>
        </div>
      </div>
    `;
    setStatus(`Error: ${error.message}`, true);
  });
