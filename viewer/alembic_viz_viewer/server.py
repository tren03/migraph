"""Local HTTP server for viewing migration graphs in a browser."""

import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional

from alembic_viz_contracts.models import GraphState
from alembic_viz_graph_ops import calculate_layers, detect_cycles, detect_heads, detect_orphans, topological_sort
from alembic_viz_writer.rewriter import ConflictFailure, ValidationFailure, WriterError, apply_graph_state

NODE_WIDTH = 220
NODE_HEIGHT = 72
LAYER_GAP = 130
COLUMN_GAP = 260
PADDING = 80


def build_view_model(graph: GraphState) -> Dict[str, Any]:
    """Build a browser-friendly graph payload with stable coordinates."""
    cycles = detect_cycles(graph)
    has_cycles = bool(cycles)
    order = topological_sort(graph) if not has_cycles else [migration.revision for migration in graph.migrations]
    layers = calculate_layers(graph) if not has_cycles else {revision: 0 for revision in order}
    heads = set(detect_heads(graph))
    orphans = set(detect_orphans(graph))
    cycle_nodes = {revision for cycle in cycles for revision in cycle[:-1]}

    rows_by_layer: Dict[int, List[str]] = {}
    for revision in order:
        layer = layers.get(revision, 0)
        rows_by_layer.setdefault(layer, []).append(revision)

    max_layer = max(rows_by_layer, default=0)
    positions: Dict[str, Dict[str, int]] = {}
    for layer, revisions in sorted(rows_by_layer.items()):
        display_layer = max_layer - layer
        for column, revision in enumerate(revisions):
            positions[revision] = {
                "x": PADDING + (column * COLUMN_GAP),
                "y": PADDING + (display_layer * LAYER_GAP),
            }

    for revision, position in graph.ui_state.positions.items():
        if revision in positions:
            positions[revision] = {"x": int(position.x), "y": int(position.y)}

    nodes = []
    edges = []
    revision_set = {migration.revision for migration in graph.migrations}
    for migration in graph.migrations:
        position = positions[migration.revision]
        nodes.append(
            {
                "revision": migration.revision,
                "down_revision": migration.down_revision,
                "path": migration.path,
                "description": migration.metadata.description,
                "timestamp": str(migration.timestamp) if migration.timestamp else None,
                "x": position["x"],
                "y": position["y"],
                "is_head": migration.revision in heads,
                "is_orphan": migration.revision in orphans,
                "in_cycle": migration.revision in cycle_nodes,
            }
        )

        parents = migration.down_revision
        if isinstance(parents, str):
            parents = [parents]
        elif parents is None:
            parents = []

        for parent in parents:
            if parent in revision_set:
                edges.append({"from": parent, "to": migration.revision})

    max_x = max((node["x"] for node in nodes), default=PADDING)
    max_y = max((node["y"] for node in nodes), default=PADDING)
    canvas = {
        "width": max_x + NODE_WIDTH + PADDING,
        "height": max_y + NODE_HEIGHT + PADDING,
    }

    return {
        "graph": graph.model_dump(mode="json"),
        "summary": {
            "migrations_count": len(graph.migrations),
            "heads": sorted(heads),
            "orphans": sorted(orphans),
            "cycles": cycles,
        },
        "layout": {
            "node_width": NODE_WIDTH,
            "node_height": NODE_HEIGHT,
            "canvas": canvas,
            "nodes": nodes,
            "edges": edges,
        },
    }


def preview_graph_state(graph: GraphState) -> Dict[str, Any]:
    """Return the viewer payload for an edited graph."""
    return build_view_model(graph)


def save_graph_state(graph: GraphState, output_path: Optional[str]) -> Optional[str]:
    """Persist an edited graph state when an output path is provided."""
    if not output_path:
        return None

    output = Path(output_path)
    output.write_text(json.dumps(graph.model_dump(mode="json"), indent=2), encoding="utf-8")
    return str(output)


def apply_graph_to_repo(graph: GraphState, directory: Optional[str], dry_run: bool = False) -> Dict[str, Any]:
    """Apply the current graph back to a repository directory."""
    target_directory = directory or graph.source_directory
    return apply_graph_state(graph=graph, directory=target_directory, dry_run=dry_run)


def _html_page() -> str:
    return """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Alembic Viz</title>
    <style>
      :root {
        color-scheme: dark;
        --bg: #0b1020;
        --panel: #111831;
        --panel-2: #182241;
        --text: #e6ecff;
        --muted: #9ca7c7;
        --edge: #6172a3;
        --head: #1f9d74;
        --orphan: #cc7a00;
        --cycle: #c53b53;
        --node: #1a2343;
        --node-border: #415487;
        --selected: #9ca8ff;
        --handle: #e0b24f;
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        font-family: Inter, ui-sans-serif, system-ui, sans-serif;
        background: linear-gradient(180deg, #08101f 0%, #0f1530 100%);
        color: var(--text);
      }
      .shell {
        display: grid;
        grid-template-columns: 340px minmax(0, 1fr);
        min-height: 100vh;
      }
      .sidebar {
        padding: 24px;
        border-right: 1px solid rgba(255,255,255,0.08);
        background: rgba(10, 15, 31, 0.82);
        backdrop-filter: blur(12px);
      }
      .graph-wrap {
        overflow: auto;
        padding: 24px;
      }
      h1 {
        margin: 0 0 8px;
        font-size: 28px;
      }
      .muted {
        color: var(--muted);
        font-size: 14px;
      }
      .stats {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 12px;
        margin: 24px 0;
      }
      .card {
        background: var(--panel);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 14px;
        padding: 14px;
      }
      .card strong {
        display: block;
        font-size: 22px;
        margin-top: 6px;
      }
      .panel {
        margin-top: 20px;
        background: var(--panel);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 14px;
        padding: 14px;
      }
      .panel h2 {
        margin: 0 0 10px;
        font-size: 14px;
      }
      .list {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 10px;
      }
      .pill {
        display: inline-flex;
        align-items: center;
        padding: 6px 10px;
        background: var(--panel-2);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 999px;
        font-size: 12px;
      }
      .legend {
        margin-top: 24px;
      }
      .legend-item {
        display: flex;
        align-items: center;
        gap: 8px;
        margin: 8px 0;
        color: var(--muted);
        font-size: 14px;
      }
      .dot {
        width: 12px;
        height: 12px;
        border-radius: 50%;
      }
      .controls {
        display: flex;
        gap: 10px;
        margin-top: 24px;
        flex-wrap: wrap;
      }
      button {
        appearance: none;
        border: 0;
        border-radius: 12px;
        padding: 10px 14px;
        background: linear-gradient(180deg, #7f8cff 0%, #5f6ce0 100%);
        color: white;
        font-weight: 700;
        cursor: pointer;
      }
      button.secondary {
        background: var(--panel-2);
        border: 1px solid rgba(255,255,255,0.08);
        color: var(--text);
      }
      button.danger {
        background: linear-gradient(180deg, #c06a50 0%, #9a4330 100%);
      }
      button:disabled {
        opacity: 0.6;
        cursor: default;
      }
      .status {
        margin-top: 12px;
        min-height: 20px;
        color: var(--muted);
        font-size: 13px;
      }
      .details-grid {
        display: grid;
        gap: 8px;
      }
      .details-grid strong {
        display: block;
        margin-bottom: 2px;
        font-size: 12px;
        color: var(--muted);
      }
      svg {
        background:
          radial-gradient(circle at top, rgba(61, 85, 150, 0.22), transparent 30%),
          rgba(8, 14, 29, 0.92);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 18px;
      }
      .edge {
        fill: none;
        stroke: var(--edge);
        stroke-width: 2;
        opacity: 0.9;
      }
      .edge.temp {
        stroke: var(--handle);
        stroke-dasharray: 6 5;
      }
      .node rect {
        fill: var(--node);
        stroke: var(--node-border);
        stroke-width: 1.5;
        rx: 14;
      }
      .node.head rect { stroke: var(--head); }
      .node.orphan rect { stroke: var(--orphan); }
      .node.cycle rect { stroke: var(--cycle); }
      .node.selected rect { stroke: var(--selected); stroke-width: 2.5; }
      .node.drop-target rect { stroke: var(--handle); stroke-width: 2.5; }
      .node-title {
        font-size: 14px;
        font-weight: 700;
        fill: var(--text);
      }
      .node-subtitle {
        font-size: 12px;
        fill: var(--muted);
      }
      .connect-handle {
        fill: var(--handle);
        cursor: crosshair;
        stroke: rgba(0,0,0,0.35);
        stroke-width: 1;
      }
      .empty {
        padding: 48px;
        text-align: center;
        color: var(--muted);
      }
      @media (max-width: 900px) {
        .shell { grid-template-columns: 1fr; }
        .sidebar { border-right: 0; border-bottom: 1px solid rgba(255,255,255,0.08); }
      }
    </style>
  </head>
  <body>
    <div class="shell">
      <aside class="sidebar">
        <h1>Alembic Viz</h1>
        <div id="source" class="muted"></div>
        <div class="stats">
          <div class="card"><span class="muted">Migrations</span><strong id="count">0</strong></div>
          <div class="card"><span class="muted">Heads</span><strong id="headsCount">0</strong></div>
          <div class="card"><span class="muted">Orphans</span><strong id="orphansCount">0</strong></div>
          <div class="card"><span class="muted">Cycles</span><strong id="cyclesCount">0</strong></div>
        </div>
        <section>
          <div class="muted">Heads</div>
          <div id="heads" class="list"></div>
        </section>
        <section style="margin-top:20px">
          <div class="muted">Orphans</div>
          <div id="orphans" class="list"></div>
        </section>
        <section class="panel">
          <h2>Selected Node</h2>
          <div id="selectedNode" class="details-grid">
            <div class="muted">Click a node to inspect or detach its parent.</div>
          </div>
          <div class="controls" style="margin-top:12px">
            <button id="detachButton" class="danger" type="button" disabled>Detach Parent</button>
            <button id="clearSelectionButton" class="secondary" type="button" disabled>Clear Selection</button>
          </div>
        </section>
        <section class="legend">
          <div class="muted">Legend</div>
          <div class="legend-item"><span class="dot" style="background: var(--node-border)"></span>Regular revision</div>
          <div class="legend-item"><span class="dot" style="background: var(--head)"></span>Head revision</div>
          <div class="legend-item"><span class="dot" style="background: var(--orphan)"></span>Missing parent reference</div>
          <div class="legend-item"><span class="dot" style="background: var(--cycle)"></span>Cycle member</div>
          <div class="legend-item"><span class="dot" style="background: var(--handle)"></span>Reparent handle</div>
        </section>
        <div class="controls">
          <button id="applyButton" type="button">Apply To Repo</button>
          <button id="exportButton" type="button">Export Graph</button>
          <button id="resetButton" class="secondary" type="button">Reset Layout</button>
        </div>
        <div id="status" class="status"></div>
      </aside>
      <main class="graph-wrap">
        <div id="app" class="empty">Loading graph...</div>
      </main>
    </div>
    <script>
      let initialData = null;
      let currentData = null;
      let selectedRevision = null;
      let activeGesture = null;

      function clone(value) {
        return JSON.parse(JSON.stringify(value));
      }

      function setStatus(message, isError = false) {
        const status = document.getElementById('status');
        status.textContent = message;
        status.style.color = isError ? '#ff8d9d' : 'var(--muted)';
      }

      function setList(id, values) {
        const root = document.getElementById(id);
        root.innerHTML = '';
        if (!values.length) {
          const el = document.createElement('span');
          el.className = 'muted';
          el.textContent = 'None';
          root.appendChild(el);
          return;
        }
        for (const value of values) {
          const el = document.createElement('span');
          el.className = 'pill';
          el.textContent = value;
          root.appendChild(el);
        }
      }

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

      function shorten(value, maxLength) {
        if (!value) return '';
        if (value.length <= maxLength) return value;
        return `${value.slice(0, maxLength - 1)}…`;
      }

      function findNode(revision) {
        return currentData.layout.nodes.find((entry) => entry.revision === revision) || null;
      }

      function findMigration(revision) {
        return currentData.graph.migrations.find((entry) => entry.revision === revision) || null;
      }

      function currentParentLabel(migration) {
        if (!migration) return 'None';
        if (Array.isArray(migration.down_revision)) return migration.down_revision.join(', ');
        return migration.down_revision || 'root';
      }

      function setSelectedRevision(revision) {
        selectedRevision = revision;
        renderSelectedNodePanel();
        renderGraph(currentData);
      }

      function renderSelectedNodePanel() {
        const selectedNode = document.getElementById('selectedNode');
        const detachButton = document.getElementById('detachButton');
        const clearSelectionButton = document.getElementById('clearSelectionButton');
        const migration = selectedRevision ? findMigration(selectedRevision) : null;

        if (!migration) {
          selectedNode.innerHTML = '<div class="muted">Click a node to inspect or detach its parent.</div>';
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
        ].join('');
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

      async function previewGraph(message) {
        const response = await fetch('/api/preview', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(currentData.graph),
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.message || 'Preview failed');
        }
        currentData = payload;
        renderSelectedNodePanel();
        renderGraph(currentData);
        if (message) {
          setStatus(message);
        }
      }

      function resetLayout() {
        if (!initialData) return;
        currentData = clone(initialData);
        currentData.graph.ui_state.positions = {};
        selectedRevision = null;
        renderSelectedNodePanel();
        renderGraph(currentData);
        setStatus('Layout reset to auto-positioned state.');
      }

      function downloadGraph(graph) {
        const blob = new Blob([JSON.stringify(graph, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = 'graph-state.json';
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
      }

      async function exportGraph() {
        const button = document.getElementById('exportButton');
        button.disabled = true;
        setStatus('Saving graph...');

        try {
          const response = await fetch('/api/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(currentData.graph),
          });
          const payload = await response.json();
          if (!response.ok) {
            throw new Error(payload.message || 'Save failed');
          }
          if (!payload.output_file) {
            downloadGraph(currentData.graph);
            setStatus('Graph downloaded as graph-state.json');
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
        const button = document.getElementById('applyButton');
        button.disabled = true;
        setStatus('Applying graph to repository...');

        try {
          const response = await fetch('/api/apply', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(currentData.graph),
          });
          const payload = await response.json();
          if (!response.ok) {
            throw new Error(payload.message || 'Apply failed');
          }
          const changed = payload.data ? payload.data.changed_files_count : 0;
          setStatus(`Applied graph to repo. Updated ${changed} file${changed === 1 ? '' : 's'}.`);
        } catch (error) {
          setStatus(`Failed to apply graph: ${error}`, true);
        } finally {
          button.disabled = false;
        }
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

      function graphPointFromEvent(event) {
        const graphWrap = document.querySelector('.graph-wrap');
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
          type: 'move',
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
          type: 'connect',
          revision,
          pointer: graphPointFromEvent(event),
          hoverTarget: null,
        };
        setSelectedRevision(revision);
        renderGraph(currentData);
          setStatus(`Drop ${revision} onto a new parent node below it.`);
      }

      async function completeConnect(targetRevision) {
        if (!activeGesture || activeGesture.type !== 'connect') return;
        const childRevision = activeGesture.revision;
        activeGesture = null;

        if (!targetRevision) {
          renderGraph(currentData);
          setStatus(`Reparent cancelled for ${childRevision}`);
          return;
        }
        if (targetRevision === childRevision) {
          renderGraph(currentData);
          setStatus('A migration cannot depend on itself.', true);
          return;
        }

        updateParent(childRevision, targetRevision);
        try {
          await previewGraph(`Updated parent of ${childRevision} to ${targetRevision}`);
        } catch (error) {
          setStatus(`Failed to update parent: ${error}`, true);
        }
      }

      function bindInteractions() {
        const app = document.getElementById('app');

        app.addEventListener('pointerdown', (event) => {
          const handle = event.target.closest('[data-connect-revision]');
          if (handle) {
            event.preventDefault();
            event.stopPropagation();
            beginConnect(handle.dataset.connectRevision, event);
            return;
          }

          const node = event.target.closest('[data-revision]');
          if (!node || event.button !== 0) return;
          beginMove(node.dataset.revision, event);
        });

        app.addEventListener('click', (event) => {
          const node = event.target.closest('[data-revision]');
          if (node) {
            setSelectedRevision(node.dataset.revision);
          }
        });

        window.addEventListener('pointermove', (event) => {
          if (!activeGesture) return;

          if (activeGesture.type === 'move') {
            const graphWrap = document.querySelector('.graph-wrap');
            const deltaX = event.clientX - activeGesture.startPointerX + graphWrap.scrollLeft;
            const deltaY = event.clientY - activeGesture.startPointerY + graphWrap.scrollTop;
            syncNodePosition(
              activeGesture.revision,
              Math.max(20, Math.round(activeGesture.startX + deltaX)),
              Math.max(20, Math.round(activeGesture.startY + deltaY)),
            );
            renderGraph(currentData);
            return;
          }

          if (activeGesture.type === 'connect') {
            activeGesture.pointer = graphPointFromEvent(event);
            const target = event.target.closest ? event.target.closest('[data-revision]') : null;
            activeGesture.hoverTarget = target ? target.dataset.revision : null;
            renderGraph(currentData);
          }
        });

        window.addEventListener('pointerup', async (event) => {
          if (!activeGesture) return;

          if (activeGesture.type === 'move') {
            const revision = activeGesture.revision;
            activeGesture = null;
            setStatus(`Position saved for ${revision}`);
            return;
          }

          if (activeGesture.type === 'connect') {
            const target = event.target.closest ? event.target.closest('[data-revision]') : null;
            await completeConnect(target ? target.dataset.revision : null);
          }
        });
      }

      function renderGraph(data) {
        document.getElementById('source').textContent = data.graph.source_directory;
        document.getElementById('count').textContent = String(data.summary.migrations_count);
        document.getElementById('headsCount').textContent = String(data.summary.heads.length);
        document.getElementById('orphansCount').textContent = String(data.summary.orphans.length);
        document.getElementById('cyclesCount').textContent = String(data.summary.cycles.length);
        setList('heads', data.summary.heads);
        setList('orphans', data.summary.orphans);

        if (!data.layout.nodes.length) {
          document.getElementById('app').textContent = 'No migrations found.';
          return;
        }

        const nodeWidth = data.layout.node_width;
        const nodeHeight = data.layout.node_height;
        const nodes = new Map(data.layout.nodes.map((node) => [node.revision, node]));
        const svg = [];

        svg.push(`<svg width="${data.layout.canvas.width}" height="${data.layout.canvas.height}" viewBox="0 0 ${data.layout.canvas.width} ${data.layout.canvas.height}" xmlns="http://www.w3.org/2000/svg">`);
        for (const edge of data.layout.edges) {
          const from = nodes.get(edge.from);
          const to = nodes.get(edge.to);
          if (!from || !to) continue;
          svg.push(`<path class="edge" d="${edgePath(from, to, nodeWidth, nodeHeight)}" />`);
        }

        if (activeGesture && activeGesture.type === 'connect') {
          const from = nodes.get(activeGesture.revision);
          if (from) {
            svg.push(`<path class="edge temp" d="${tempEdgePath(from, activeGesture.pointer, nodeWidth, nodeHeight)}" />`);
          }
        }

        for (const node of data.layout.nodes) {
          const classes = ['node'];
          if (node.is_head) classes.push('head');
          if (node.is_orphan) classes.push('orphan');
          if (node.in_cycle) classes.push('cycle');
          if (selectedRevision === node.revision) classes.push('selected');
          if (activeGesture && activeGesture.type === 'connect' && activeGesture.hoverTarget === node.revision && activeGesture.revision !== node.revision) {
            classes.push('drop-target');
          }

          const description = shorten(node.description || node.path, 28);
          const revision = shorten(node.revision, 22);
          const parentText = Array.isArray(node.down_revision)
            ? node.down_revision.join(', ')
            : (node.down_revision || 'root');

          svg.push(`<g class="${classes.join(' ')}" data-revision="${node.revision}" style="cursor: grab" transform="translate(${node.x}, ${node.y})">`);
          svg.push(`<title>${node.revision}\n${node.description || node.path}\nparent: ${parentText}</title>`);
          svg.push(`<rect width="${nodeWidth}" height="${nodeHeight}" />`);
          svg.push(`<circle class="connect-handle" data-connect-revision="${node.revision}" cx="${Math.round(nodeWidth / 2)}" cy="${nodeHeight - 8}" r="7" />`);
          svg.push(`<text class="node-title" x="14" y="28">${revision}</text>`);
          svg.push(`<text class="node-subtitle" x="14" y="50">${description}</text>`);
          svg.push(`<text class="node-subtitle" x="14" y="64">${shorten(node.path, 28)}</text>`);
          svg.push(`</g>`);
        }
        svg.push('</svg>');
        document.getElementById('app').innerHTML = svg.join('');
      }

      document.getElementById('exportButton').addEventListener('click', exportGraph);
      document.getElementById('applyButton').addEventListener('click', applyGraph);
      document.getElementById('resetButton').addEventListener('click', resetLayout);
      document.getElementById('detachButton').addEventListener('click', detachSelectedParent);
      document.getElementById('clearSelectionButton').addEventListener('click', () => setSelectedRevision(null));
      bindInteractions();

      fetch('/api/graph')
        .then((response) => response.json())
        .then((payload) => {
          initialData = clone(payload);
          currentData = clone(payload);
          renderSelectedNodePanel();
          renderGraph(currentData);
          setStatus('Drag nodes to move them. Drag the gold bottom handle onto another node to reparent.');
        })
        .catch((error) => {
          document.getElementById('app').textContent = `Failed to load graph: ${error}`;
          setStatus(`Failed to load graph: ${error}`, true);
        });
    </script>
  </body>
</html>
"""


def serve_graph(
    graph: GraphState,
    host: str = "127.0.0.1",
    port: int = 0,
    open_browser: bool = True,
    output_path: Optional[str] = None,
    apply_directory: Optional[str] = None,
) -> str:
    """Serve a graph locally until interrupted."""
    html = _html_page().encode("utf-8")
    current_graph = graph.model_copy(deep=True)

    class ViewerHandler(BaseHTTPRequestHandler):
        def _write_json(self, status_code: int, payload: Dict[str, Any]) -> None:
            response = json.dumps(payload).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)

        def do_GET(self) -> None:  # noqa: N802
            if self.path in {"/", "/index.html"}:
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(html)))
                self.end_headers()
                self.wfile.write(html)
                return

            if self.path == "/api/graph":
                self._write_json(200, preview_graph_state(current_graph))
                return

            self.send_response(404)
            self.end_headers()

        def do_POST(self) -> None:  # noqa: N802
            nonlocal current_graph

            content_length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(content_length)

            try:
                proposed_graph = GraphState.model_validate_json(body)
            except Exception as exc:
                self._write_json(400, {"status": "error", "message": f"Invalid GraphState payload: {exc}"})
                return

            if self.path == "/api/preview":
                current_graph = proposed_graph
                self._write_json(200, preview_graph_state(current_graph))
                return

            if self.path == "/api/save":
                current_graph = proposed_graph
                saved_output = save_graph_state(current_graph, output_path)
                self._write_json(
                    200,
                    {
                        "status": "success",
                        "output_file": saved_output,
                        "migrations_count": len(current_graph.migrations),
                    },
                )
                return

            if self.path == "/api/apply":
                current_graph = proposed_graph
                try:
                    result = apply_graph_to_repo(current_graph, apply_directory)
                    self._write_json(200, result)
                except ValidationFailure as exc:
                    self._write_json(400, {"status": "error", "message": str(exc)})
                except ConflictFailure as exc:
                    self._write_json(409, {"status": "error", "message": str(exc)})
                except WriterError as exc:
                    self._write_json(500, {"status": "error", "message": str(exc)})
                return

            self.send_response(404)
            self.end_headers()

        def log_message(self, format: str, *args: Any) -> None:
            return

    server = ThreadingHTTPServer((host, port), ViewerHandler)
    url = f"http://{host}:{server.server_address[1]}"

    if open_browser:
        threading.Timer(0.2, lambda: webbrowser.open(url)).start()

    try:
        print(f"Viewer running at {url}")
        print("Press Ctrl+C to stop the server.")
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

    return url
