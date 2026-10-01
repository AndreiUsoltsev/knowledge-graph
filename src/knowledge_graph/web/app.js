"use strict";

const $ = id => document.getElementById(id);
let typeNames = messages[language].types;
let relationNames = messages[language].relations;
let graph = null, selected = null, searchResults = null;
let searchSequence = 0, nodeSequence = 0, loadSequence = 0;
let camera = {x: 0, y: 0, k: 1}, bounds = null, dragging = null;
let searchTimer;

function countLabel(number, forms) {
  if (language === "en") return `${number} ${forms[number === 1 ? 0 : 1]}`;
  const lastTwo = number % 100, last = number % 10;
  const form = lastTwo >= 11 && lastTwo <= 14 ? forms[2] : last === 1 ? forms[0] : last >= 2 && last <= 4 ? forms[1] : forms[2];
  return `${number} ${form}`;
}

function graphCounts(nodes, edges) {
  return `${countLabel(nodes, messages[language].nodeForms)} · ${countLabel(edges, messages[language].edgeForms)}`;
}

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function svgElement(tag, attributes = {}) {
  const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, value);
  return node;
}

async function api(path) {
  const response = await fetch(`${path}${path.includes("?") ? "&" : "?"}lang=${language}`, {cache: "no-store"});
  const result = await response.json();
  if (!response.ok || !result.success) {
    const error = new Error(messages[language].errors[result.code] || t("requestError"));
    error.code = result.code;
    error.details = result.details;
    throw error;
  }
  return result.data;
}

function showError(error) {
  const diagnostics = error.details?.errors?.map(item => `${item.code}: ${messages[language].errors[item.code] || t("requestError")}`).join("\n");
  $("error").textContent = `${error.code || "ERROR"}: ${error.message}${diagnostics ? "\n" + diagnostics + "\n" + t("diagnosticHint") : ""}`;
  $("error").hidden = false;
  document.body.classList.add("has-error");
}

function clearError() {
  $("error").hidden = true;
  document.body.classList.remove("has-error");
}

function clearDatabase() {
  graph = null;
  selected = null;
  searchResults = null;
  $("node-list").replaceChildren();
  $("graph-world").replaceChildren();
  $("document").replaceChildren(element("p", t("repair"), "no-links"));
  $("stats").textContent = t("unavailable");
  $("list-count").textContent = "0";
  $("graph-count").textContent = "";
  $("validation-status").textContent = "";
  $("copy").disabled = true;
}

function handleError(error) {
  if (error.code === "INVALID_DATABASE") {
    nodeSequence++;
    searchSequence++;
    clearDatabase();
  }
  showError(error);
}

function populateOptions(id, values, names) {
  const select = $(id), old = select.value;
  while (select.options.length > 1) select.remove(1);
  for (const value of values) {
    const option = element("option", names[value] || value);
    option.value = value;
    select.append(option);
  }
  select.value = values.includes(old) ? old : "";
}

async function loadDatabase(preserveCamera = false) {
  const previousCamera = {...camera};
  const sequence = ++loadSequence;
  nodeSequence++;
  searchSequence++;
  clearTimeout(searchTimer);
  $("reload").disabled = true;
  clearError();
  try {
    const data = await api("/api/graph");
    const report = await api("/api/validate");
    if (!report.valid) {
      const error = new Error(t("invalid"));
      error.code = "INVALID_DATABASE";
      error.details = report;
      throw error;
    }
    if (sequence !== loadSequence) return;
    graph = data;
    searchResults = null;
    populateOptions("node-type", graph.node_types, typeNames);
    populateOptions("relation", graph.relations, relationNames);
    $("stats").textContent = graphCounts(graph.nodes.length, graph.edges.length);
    $("validation-status").textContent = report.warnings.length ? t("warnings", {count: report.warnings.length}) : t("valid");
    $("validation-status").title = report.warnings.map(item => `${item.code}: ${messages[language].errors[item.code] || t("requestError")}`).join("\n");
    const hash = new URLSearchParams(location.hash.slice(1)).get("node");
    const identifier = graph.nodes.some(node => node.id === hash) ? hash : graph.entry_points[0];
    renderList();
    await selectNode(identifier, hash !== identifier ? "replace" : "none");
    if (hash && hash !== identifier) showError(new Error(t("missingNode", {id: hash})));
    if ($("search").value.trim()) await runSearch();
    if (preserveCamera === true) { camera = previousCamera; applyCamera(); }
  } catch (error) {
    if (sequence !== loadSequence) return;
    clearDatabase();
    showError(error);
  } finally {
    if (sequence === loadSequence) $("reload").disabled = false;
  }
}

function renderList() {
  if (!graph) return;
  const type = $("node-type").value;
  const nodes = (searchResults ?? graph.nodes).filter(node => !type || node.type === type);
  $("node-list").replaceChildren();
  $("list-count").textContent = nodes.length;
  $("list-title").textContent = searchResults === null ? t("nodes") : t("results");
  for (const node of nodes) {
    const button = element("button", undefined, `node-button${selected === node.id ? " active" : ""}`);
    button.dataset.id = node.id;
    if (selected === node.id) button.setAttribute("aria-current", "true");
    const title = element("span", node.title, "title");
    if (graph.entry_points.includes(node.id)) title.append(element("span", t("entry"), "entry-tag"));
    button.append(title, element("span", node.summary, "summary"), element("span", node.id, "node-id"));
    button.addEventListener("click", () => selectNode(node.id));
    $("node-list").append(button);
  }
  if (!nodes.length) $("node-list").append(element("p", t("noResults"), "no-links"));
}

async function runSearch() {
  const sequence = ++searchSequence;
  const query = $("search").value.trim();
  if (!graph) return;
  if (!query) {
    searchResults = null;
    renderList();
    return;
  }
  try {
    const result = await api(`/api/search?q=${encodeURIComponent(query)}&limit=200`);
    if (sequence !== searchSequence) return;
    searchResults = result.nodes;
    clearError();
    renderList();
    if (result.truncated) $("list-title").textContent = t("firstResults", {count: result.total});
  } catch (error) {
    if (sequence === searchSequence) handleError(error);
  }
}

async function selectNode(identifier, historyMode = "push") {
  if (!graph) return;
  const sequence = ++nodeSequence;
  try {
    const node = await api(`/api/node?id=${encodeURIComponent(identifier)}`);
    if (sequence !== nodeSequence) return;
    selected = identifier;
    clearError();
    const hash = `#node=${encodeURIComponent(identifier)}`;
    if (historyMode === "replace") history.replaceState({node: identifier}, "", hash);
    else if (historyMode === "push" && location.hash !== hash) history.pushState({node: identifier}, "", hash);
    renderDocument(node);
    renderList();
    drawGraph();
    $("copy").disabled = false;
  } catch (error) {
    if (sequence === nodeSequence) handleError(error);
  }
}

// Markdown is rendered with DOM nodes, never with innerHTML. Raw HTML stays text.
function inlineMarkdown(parent, source) {
  const pattern = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*|\[[^\]]+\]\([^)]+\))/g;
  let previous = 0;
  for (const match of source.matchAll(pattern)) {
    parent.append(document.createTextNode(source.slice(previous, match.index)));
    const token = match[0];
    if (token.startsWith("`")) parent.append(element("code", token.slice(1, -1)));
    else if (token.startsWith("**")) parent.append(element("strong", token.slice(2, -2)));
    else if (token.startsWith("*")) parent.append(element("em", token.slice(1, -1)));
    else {
      const parts = /^\[([^\]]+)\]\(([^)]+)\)$/.exec(token);
      const text = parts[1], target = parts[2];
      const candidates = graph?.nodes.filter(node => node.content === target || node.content.split("/").at(-1) === target) ?? [];
      const linkedNode = target.startsWith("kg:") ? target.slice(3) : candidates.length === 1 ? candidates[0].id : null;
      if (linkedNode && graph.nodes.some(node => node.id === linkedNode)) {
        const link = element("a", text);
        link.href = `#node=${encodeURIComponent(linkedNode)}`;
        link.addEventListener("click", event => { event.preventDefault(); selectNode(linkedNode); });
        parent.append(link);
      } else if (/^https?:\/\//i.test(target)) {
        const link = element("a", text);
        link.href = target;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        parent.append(link);
      } else parent.append(document.createTextNode(`${text} (${target})`));
    }
    previous = match.index + token.length;
  }
  parent.append(document.createTextNode(source.slice(previous)));
}

function markdown(source) {
  const container = element("div", undefined, "markdown");
  const lines = source.replace(/\r\n?/g, "\n").split("\n");
  for (let index = 0; index < lines.length;) {
    const line = lines[index];
    if (!line.trim()) { index++; continue; }
    if (/^\s*```/.test(line)) {
      const code = [];
      index++;
      while (index < lines.length && !/^\s*```/.test(lines[index])) code.push(lines[index++]);
      index++;
      const pre = element("pre");
      pre.append(element("code", code.join("\n")));
      container.append(pre);
      continue;
    }
    const heading = /^(#{1,6})\s+(.+)$/.exec(line);
    if (heading) {
      const block = element(`h${heading[1].length}`);
      inlineMarkdown(block, heading[2]);
      container.append(block);
      index++;
      continue;
    }
    if (line.includes("|") && index + 1 < lines.length && /^\s*\|?\s*:?-{3,}/.test(lines[index + 1])) {
      const table = element("table");
      let header = true;
      const row = text => {
        const tr = element("tr");
        const cells = text.trim().replace(/^\|/, "").replace(/\|$/, "").split("|");
        for (const cell of cells) {
          const td = element(header ? "th" : "td");
          inlineMarkdown(td, cell.trim());
          tr.append(td);
        }
        table.append(tr);
      };
      row(line);
      header = false;
      index += 2;
      while (index < lines.length && lines[index].trim() && lines[index].includes("|")) row(lines[index++]);
      container.append(table);
      continue;
    }
    const list = /^\s*([-*]|\d+\.)\s+/.exec(line);
    if (list) {
      const ordered = /\d/.test(list[1]);
      const block = element(ordered ? "ol" : "ul");
      const pattern = ordered ? /^\s*\d+\.\s+(.+)$/ : /^\s*[-*]\s+(.+)$/;
      while (index < lines.length && pattern.test(lines[index])) {
        const li = element("li");
        inlineMarkdown(li, pattern.exec(lines[index++])[1]);
        block.append(li);
      }
      container.append(block);
      continue;
    }
    if (/^>\s?/.test(line)) {
      const block = element("blockquote");
      inlineMarkdown(block, line.replace(/^>\s?/, ""));
      container.append(block);
      index++;
      continue;
    }
    const paragraph = [line];
    index++;
    while (index < lines.length && lines[index].trim() && !/^(#{1,6}\s|\s*```|\s*[-*]\s|\s*\d+\.\s|>)/.test(lines[index])) {
      if (index + 1 < lines.length && lines[index].includes("|") && /^\s*\|?\s*:?-{3,}/.test(lines[index + 1])) break;
      paragraph.push(lines[index++]);
    }
    const block = element("p");
    inlineMarkdown(block, paragraph.join(" "));
    container.append(block);
  }
  return container;
}

function renderDocument(node) {
  const documentPanel = $("document");
  documentPanel.replaceChildren(element("span", (typeNames[node.type] || node.type).toUpperCase(), "eyebrow"),
    element("h1", node.title, "doc-title"), element("p", node.summary, "doc-summary"), element("div", node.id, "doc-id"));
  const tags = element("div", undefined, "tags");
  node.tags.forEach(tag => tags.append(element("span", tag, "tag")));
  documentPanel.append(tags, markdown(node.body), element("h2", t("next"), "links-title"));
  for (const direction of ["out", "in"]) {
    documentPanel.append(element("h3", direction === "out" ? t("outgoing") : t("incoming"), "link-group-title"));
    const neighbors = node.neighbors.filter(item => item.direction === direction);
    if (!neighbors.length) documentPanel.append(element("p", t("noLinks"), "no-links"));
    for (const neighbor of neighbors) {
      const button = element("button", undefined, "edge-button");
      button.append(element("strong", neighbor.node.title), element("small", neighbor.edge.label),
        element("span", `${relationNames[neighbor.edge.type] || neighbor.edge.type} · ${neighbor.node.id}`, "edge-type"));
      button.addEventListener("click", () => selectNode(neighbor.node.id));
      documentPanel.append(button);
    }
  }
  documentPanel.scrollTop = 0;
}

function visibleGraph() {
  const relation = $("relation").value;
  const edges = graph.edges.filter(edge => !relation || edge.type === relation);
  let ids;
  if ($("view-mode").value === "all") ids = new Set(graph.nodes.map(node => node.id));
  else {
    ids = new Set([selected]);
    let frontier = [selected];
    for (let distance = 0; distance < Number($("depth").value); distance++) {
      const next = [];
      for (const id of frontier) for (const edge of edges) {
        const neighbor = edge.source === id ? edge.target : edge.target === id ? edge.source : null;
        if (neighbor && !ids.has(neighbor)) { ids.add(neighbor); next.push(neighbor); }
      }
      frontier = next;
    }
  }
  const type = $("node-type").value;
  const nodes = graph.nodes.filter(node => ids.has(node.id) && (!type || node.type === type));
  ids = new Set(nodes.map(node => node.id));
  return {nodes, edges: edges.filter(edge => ids.has(edge.source) && ids.has(edge.target))};
}

function graphLayout(nodes, edges) {
  const root = nodes.some(node => node.id === selected) ? selected : nodes[0].id;
  const distances = new Map([[root, 0]]), queue = [root];
  for (let cursor = 0; cursor < queue.length; cursor++) {
    const id = queue[cursor];
    for (const edge of edges) {
      const target = edge.source === id ? edge.target : edge.target === id ? edge.source : null;
      if (target && !distances.has(target)) { distances.set(target, distances.get(id) + 1); queue.push(target); }
    }
  }
  const disconnectedDistance = Math.max(...distances.values()) + 1;
  const layers = new Map();
  for (const node of nodes) {
    const distance = distances.get(node.id) ?? disconnectedDistance;
    if (!layers.has(distance)) layers.set(distance, []);
    layers.get(distance).push(node.id);
  }
  const positions = new Map();
  let previousRadius = 0;
  for (const [distance, layer] of [...layers.entries()].sort((a, b) => a[0] - b[0])) {
    layer.sort();
    const radius = distance === 0 ? 0 : Math.max(previousRadius + 235, layer.length * 210 / (2 * Math.PI));
    layer.forEach((id, index) => {
      const angle = -Math.PI / 2 + index * 2 * Math.PI / layer.length;
      positions.set(id, {x: Math.cos(angle) * radius, y: Math.sin(angle) * radius});
    });
    previousRadius = radius;
  }
  return positions;
}

function clippedPoint(from, to, margin = 0) {
  const dx = to.x - from.x, dy = to.y - from.y;
  const ratio = Math.min((91 + margin) / Math.max(Math.abs(dx), .001), (42 + margin) / Math.max(Math.abs(dy), .001));
  return {x: from.x + dx * ratio, y: from.y + dy * ratio};
}

function drawGraph() {
  if (!graph || !selected) return;
  const {nodes, edges} = visibleGraph();
  const world = $("graph-world");
  world.replaceChildren();
  $("depth").disabled = $("view-mode").value === "all";
  $("graph-empty").hidden = Boolean(nodes.length);
  $("graph-count").textContent = t("inView", {counts: graphCounts(nodes.length, edges.length)});
  if (!nodes.length) { bounds = null; return; }
  const positions = graphLayout(nodes, edges);
  const edgeGroup = svgElement("g");
  for (const edge of edges) {
    const from = positions.get(edge.source), to = positions.get(edge.target);
    let path;
    if (edge.source === edge.target) {
      path = `M ${from.x + 55} ${from.y - 42} C ${from.x + 160} ${from.y - 150}, ${from.x - 160} ${from.y - 150}, ${from.x - 55} ${from.y - 46}`;
    } else {
      const start = clippedPoint(from, to), end = clippedPoint(to, from, 5);
      // A small curve separates opposite-direction links without hiding direction.
      const bend = 18;
      const dx = end.x - start.x, dy = end.y - start.y, length = Math.hypot(dx, dy) || 1;
      path = `M ${start.x} ${start.y} Q ${(start.x + end.x) / 2 - dy / length * bend} ${(start.y + end.y) / 2 + dx / length * bend} ${end.x} ${end.y}`;
    }
    const link = svgElement("path", {d: path, class: "graph-edge", "marker-end": "url(#arrow)"});
    const title = svgElement("title");
    title.textContent = `${edge.source} → ${edge.target}\n${relationNames[edge.type] || edge.type}: ${edge.label}`;
    link.append(title);
    edgeGroup.append(link);
  }
  world.append(edgeGroup);
  for (const node of nodes) {
    const position = positions.get(node.id);
    const group = svgElement("g", {transform: `translate(${position.x},${position.y})`,
      class: `graph-node ${node.type}${selected === node.id ? " selected" : ""}`, tabindex: "0", role: "button", "aria-label": node.title});
    group.dataset.id = node.id;
    const title = svgElement("title");
    title.textContent = `${node.title}\n${node.summary}\n${node.id}`;
    group.append(title, svgElement("rect", {x: -91, y: -42, width: 182, height: 84, rx: 9}));
    const words = node.title.split(" "), lines = [""];
    for (const word of words) {
      if ((lines.at(-1) + " " + word).trim().length > 24 && lines.at(-1) && lines.length < 2) lines.push(word);
      else lines[lines.length - 1] = (lines.at(-1) + " " + word).trim();
    }
    lines.slice(0, 2).forEach((line, index) => {
      const text = svgElement("text", {x: 0, y: -12 + index * 17, "text-anchor": "middle"});
      text.textContent = line.length > 26 ? line.slice(0, 25) + "…" : line;
      group.append(text);
    });
    const identifier = svgElement("text", {x: 0, y: 27, "text-anchor": "middle", class: "graph-id"});
    identifier.textContent = node.id.length > 26 ? node.id.slice(0, 25) + "…" : node.id;
    group.append(identifier);
    group.addEventListener("click", () => selectNode(node.id));
    group.addEventListener("keydown", event => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); selectNode(node.id); } });
    world.append(group);
  }
  const values = [...positions.values()];
  bounds = {left: Math.min(...values.map(p => p.x)) - 115, right: Math.max(...values.map(p => p.x)) + 115,
    top: Math.min(...values.map(p => p.y)) - 130, bottom: Math.max(...values.map(p => p.y)) + 65};
  fitGraph();
}

function applyCamera() { $("graph-world").setAttribute("transform", `translate(${camera.x},${camera.y}) scale(${camera.k})`); }
function canvasSize() {
  const container = document.querySelector(".canvas-wrap");
  const size = {width: container.clientWidth, height: container.clientHeight};
  const viewBox = `0 0 ${size.width} ${size.height}`;
  if (size.width > 0 && size.height > 0 && $("graph").getAttribute("viewBox") !== viewBox) {
    $("graph").setAttribute("viewBox", viewBox);
  }
  return size;
}
function fitGraph() {
  if (!bounds) return;
  const rect = canvasSize();
  if (!rect.width || !rect.height) return;
  const k = Math.max(.02, Math.min(1.3, (rect.width - 35) / (bounds.right - bounds.left), (rect.height - 60) / (bounds.bottom - bounds.top)));
  camera = {k, x: rect.width / 2 - (bounds.left + bounds.right) / 2 * k, y: rect.height / 2 - (bounds.top + bounds.bottom) / 2 * k - 10};
  applyCamera();
}
function zoom(factor, x, y) {
  if (!bounds) return;
  const rect = canvasSize();
  x ??= rect.width / 2;
  y ??= rect.height / 2;
  const k = Math.max(.02, Math.min(4, camera.k * factor));
  camera.x = x - (x - camera.x) * k / camera.k;
  camera.y = y - (y - camera.y) * k / camera.k;
  camera.k = k;
  applyCamera();
}

$("search").addEventListener("input", () => {
  searchSequence++;
  clearTimeout(searchTimer);
  searchTimer = setTimeout(runSearch, 180);
});
$("node-type").addEventListener("change", () => { renderList(); drawGraph(); });
for (const id of ["view-mode", "depth", "relation"]) $(id).addEventListener("change", drawGraph);
$("reload").addEventListener("click", loadDatabase);
$("fit").addEventListener("click", fitGraph);
$("zoom-in").addEventListener("click", () => zoom(1.2));
$("zoom-out").addEventListener("click", () => zoom(1 / 1.2));
$("back").addEventListener("click", () => history.back());
$("forward").addEventListener("click", () => history.forward());
$("copy").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(selected);
    $("copy").textContent = t("copied");
    setTimeout(() => { $("copy").textContent = t("copy"); }, 1200);
  } catch { showError(new Error(t("copyError", {id: selected}))); }
});
window.addEventListener("popstate", () => {
  if (!graph) return;
  const identifier = new URLSearchParams(location.hash.slice(1)).get("node") || graph.entry_points[0];
  selectNode(identifier, "none");
});
$("graph").addEventListener("wheel", event => {
  event.preventDefault();
  const rect = $("graph").getBoundingClientRect();
  zoom(event.deltaY < 0 ? 1.12 : 1 / 1.12, event.clientX - rect.left, event.clientY - rect.top);
}, {passive: false});
$("graph").addEventListener("pointerdown", event => {
  if (event.target.closest(".graph-node") || event.button !== 0) return;
  dragging = {x: event.clientX, y: event.clientY, cameraX: camera.x, cameraY: camera.y};
  $("graph").setPointerCapture(event.pointerId);
  $("graph").classList.add("dragging");
});
$("graph").addEventListener("pointermove", event => {
  if (!dragging) return;
  camera.x = dragging.cameraX + event.clientX - dragging.x;
  camera.y = dragging.cameraY + event.clientY - dragging.y;
  applyCamera();
});
for (const eventName of ["pointerup", "pointercancel"]) $("graph").addEventListener(eventName, () => {
  dragging = null;
  $("graph").classList.remove("dragging");
});
let lastCanvasWidth = -1, lastCanvasHeight = -1;
new ResizeObserver(([entry]) => {
  const {width, height} = entry.contentRect;
  if (width === lastCanvasWidth && height === lastCanvasHeight) return;
  lastCanvasWidth = width;
  lastCanvasHeight = height;
  fitGraph();
}).observe(document.querySelector(".canvas-wrap"));
applyLanguage();
loadDatabase();
$("language").addEventListener("change", async () => {
  language = $("language").value;
  try { localStorage.setItem("knowledge-graph-language", language); } catch { /* Optional persistence. */ }
  const address = new URL(location.href);
  if (address.searchParams.has("lang")) {
    address.searchParams.set("lang", language);
    history.replaceState(history.state, "", address);
  }
  typeNames = messages[language].types;
  relationNames = messages[language].relations;
  applyLanguage();
  await loadDatabase(true);
});
