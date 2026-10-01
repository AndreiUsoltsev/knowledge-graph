"""Read-only graph validation, lexical search and navigation shared by CLI and GUI."""
from collections import deque
import json
from pathlib import Path, PurePosixPath
import re

NODE_TYPES = ("system", "concept", "workflow", "tool", "reference")
RELATIONS = ("contains", "explains", "requires", "related")
LANGUAGES = ("en", "ru")
ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9._-]*\Z")
NODE_FIELDS = ("id", "title", "type", "summary", "tags", "content")
EDGE_FIELDS = ("source", "target", "type", "label")


class GraphError(Exception):
    def __init__(self, code, message, details=None):
        super().__init__(message)
        self.code = code
        self.details = details

    def response(self):
        result = {"success": False, "code": self.code, "message": str(self)}
        if self.details is not None:
            result["details"] = self.details
        return result


def inspect_database(database, lang="en"):
    """Return (report, graph); validate every translation before publishing any data."""
    if lang not in LANGUAGES:
        raise GraphError("INVALID_LANGUAGE", "Supported languages are en and ru.")
    database = Path(database).resolve()
    errors, warnings = [], []

    def issue(code, message):
        errors.append({"code": code, "message": message})

    def report():
        return {"valid": not errors, "database": str(database), "errors": errors, "warnings": warnings}

    def text_fields(value, fields, name, code):
        if not isinstance(value, dict):
            issue(code, f"{name} must be an object.")
            return False
        valid = True
        for field in fields:
            if not isinstance(value.get(field), str) or not value[field].strip():
                issue(code, f"{name}.{field} must be a nonempty string.")
                valid = False
        return valid

    def tags(value, name):
        if (not isinstance(value.get("tags"), list)
                or any(not isinstance(tag, str) or not tag.strip() for tag in value["tags"])):
            issue("INVALID_TAGS", f"{name}.tags must be an array of nonempty strings.")

    def document(relative_path, name):
        relative = PurePosixPath(relative_path)
        try:
            path = (database / relative_path).resolve()
        except (OSError, ValueError, RuntimeError) as exc:
            issue("UNSAFE_CONTENT_PATH", f"{name}: invalid document path: {exc}")
            return ""
        if (relative.is_absolute() or "\\" in relative_path or ":" in relative_path
                or any(ord(character) < 32 for character in relative_path)
                or ".." in relative.parts or not path.is_relative_to(database)
                or path.suffix.lower() != ".md"):
            issue("UNSAFE_CONTENT_PATH", f"{name}: content must be a relative Markdown path inside the database.")
            return ""
        try:
            body = path.read_text(encoding="utf-8-sig")
            if not body.strip():
                issue("EMPTY_DOCUMENT", f"Document for {name} is empty.")
            return body
        except (OSError, UnicodeError, ValueError) as exc:
            issue("INVALID_DOCUMENT", f"Cannot read document for {name}: {exc}")
            return ""

    def translations(value, fields, name):
        variants = value.get("translations", {})
        if not isinstance(variants, dict):
            issue("INVALID_TRANSLATION", f"{name}.translations must be an object.")
            return {}
        valid_variants = {}
        for language, variant in variants.items():
            if language != "ru":
                issue("INVALID_TRANSLATION", f"{name}: only ru translations are supported; English uses the main fields.")
            elif text_fields(variant, fields, f"{name}.translations.ru", "INVALID_TRANSLATION"):
                valid_variants[language] = variant
        return valid_variants

    try:
        raw = json.loads((database / "graph.json").read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, ValueError) as exc:
        issue("INVALID_MANIFEST", f"Cannot read graph.json: {exc}")
        return report(), None
    if not isinstance(raw, dict):
        issue("INVALID_MANIFEST", "graph.json must contain an object.")
        return report(), None
    if type(raw.get("version")) is not int or raw["version"] != 1:
        issue("UNSUPPORTED_VERSION", "Supported graph version is 1.")
    for key in ("entry_points", "nodes", "edges"):
        if not isinstance(raw.get(key), list):
            issue("INVALID_MANIFEST", f"{key} must be an array.")
    if errors:
        return report(), None

    nodes, contents = {}, {}
    for index, node in enumerate(raw["nodes"]):
        name = f"nodes[{index}]"
        if not text_fields(node, ("id", "title", "type", "summary", "content"), name, "INVALID_NODE"):
            continue
        identifier = node["id"]
        if not ID_PATTERN.fullmatch(identifier):
            issue("INVALID_ID", f"Invalid node ID: {identifier!r}.")
        if identifier in nodes:
            issue("DUPLICATE_ID", f"Duplicate node ID: {identifier}.")
            continue
        if node["type"] not in NODE_TYPES:
            issue("INVALID_NODE_TYPE", f"Unknown node type for {identifier}: {node['type']}.")
        tags(node, identifier)
        variants = translations(node, ("title", "summary", "content"), identifier)
        contents[identifier] = {"en": document(node["content"], identifier)}
        for language, variant in variants.items():
            tags(variant, f"{identifier} ({language})")
            contents[identifier][language] = document(variant["content"], f"{identifier} ({language})")
        nodes[identifier] = {field: node[field] for field in NODE_FIELDS if field in node}
        nodes[identifier]["translations"] = variants

    if not nodes:
        issue("EMPTY_GRAPH", "At least one node is required.")
    if not raw["entry_points"]:
        issue("MISSING_ENTRY_POINT", "At least one entry point is required.")
    seen_entries = set()
    for identifier in raw["entry_points"]:
        if not isinstance(identifier, str) or identifier not in nodes:
            issue("INVALID_ENTRY_POINT", f"Unknown entry point: {identifier!r}.")
        elif identifier in seen_entries:
            issue("DUPLICATE_ENTRY_POINT", f"Duplicate entry point: {identifier}.")
        else:
            seen_entries.add(identifier)

    edges, seen_edges = [], set()
    for index, edge in enumerate(raw["edges"]):
        if not text_fields(edge, EDGE_FIELDS, f"edges[{index}]", "INVALID_EDGE"):
            continue
        if edge["source"] not in nodes or edge["target"] not in nodes:
            issue("DANGLING_EDGE", f"Unknown endpoint in {edge['source']} -> {edge['target']}.")
        if edge["type"] not in RELATIONS:
            issue("INVALID_RELATION", f"Unknown relation: {edge['type']}.")
        key = (edge["source"], edge["target"], edge["type"])
        if key in seen_edges:
            issue("DUPLICATE_EDGE", f"Duplicate edge: {key}.")
        seen_edges.add(key)
        item = {field: edge[field] for field in EDGE_FIELDS}
        item["translations"] = translations(edge, ("label",), f"edges[{index}]")
        edges.append(item)
    if errors:
        return report(), None
    graph = Graph(database, nodes, contents, edges, raw["entry_points"], lang)
    reachable = set()
    for identifier in graph.entry_points:
        reachable.update(item["id"] for item in graph.walk(identifier, depth=len(nodes), max_nodes=len(nodes))["nodes"])
    for identifier in sorted(set(nodes) - reachable):
        warnings.append({"code": "UNREACHABLE_NODE", "message": f"Node {identifier} is unreachable from entry points (both directions)."})
    return report(), graph


class Graph:
    @classmethod
    def load(cls, database, lang="en"):
        report, graph = inspect_database(database, lang)
        if not report["valid"]:
            raise GraphError("INVALID_DATABASE", "The database failed validation.", report)
        return graph

    def __init__(self, database, nodes, contents, edges, entry_points, lang="en"):
        self.database, self.lang = database, lang
        self.nodes = {}
        self.contents = {}
        for identifier, node in nodes.items():
            localized = {field: node[field] for field in NODE_FIELDS}
            variant = node.get("translations", {}).get(lang)
            if variant:
                localized.update({field: variant[field] for field in ("title", "summary", "tags", "content")})
            self.nodes[identifier] = localized
            self.contents[identifier] = contents[identifier].get(lang, contents[identifier]["en"])
        self.edges = []
        for edge in sorted(edges, key=lambda item: (item["source"], item["target"], item["type"])):
            localized = {field: edge[field] for field in EDGE_FIELDS}
            localized["label"] = edge.get("translations", {}).get(lang, {}).get("label", edge["label"])
            self.edges.append(localized)
        self.entry_points = sorted(entry_points)
        self.outgoing = {identifier: [] for identifier in nodes}
        self.incoming = {identifier: [] for identifier in nodes}
        for edge in self.edges:
            self.outgoing[edge["source"]].append(edge)
            self.incoming[edge["target"]].append(edge)

    def metadata(self, identifier):
        if identifier not in self.nodes:
            raise GraphError("UNKNOWN_NODE", f"Unknown node: {identifier}.")
        return dict(self.nodes[identifier])

    def entries(self):
        return [self.metadata(identifier) for identifier in self.entry_points]

    def snapshot(self):
        return {"version": 1, "language": self.lang, "languages": LANGUAGES,
                "entry_points": self.entry_points,
                "nodes": [self.metadata(identifier) for identifier in sorted(self.nodes)],
                "edges": self.edges, "node_types": NODE_TYPES, "relations": RELATIONS}

    def node(self, identifier):
        return {**self.metadata(identifier), "body": self.contents[identifier], "neighbors": self.neighbors(identifier)}

    def neighbors(self, identifier, direction="both", relation=None):
        self.metadata(identifier)
        self._options(direction, relation)
        result = []
        for traversal, adjacency, target_field in (("out", self.outgoing, "target"), ("in", self.incoming, "source")):
            if direction not in ("both", traversal):
                continue
            for edge in adjacency[identifier]:
                if relation is None or edge["type"] == relation:
                    result.append({"direction": traversal, "edge": edge, "node": self.metadata(edge[target_field])})
        return sorted(result, key=lambda item: (item["node"]["id"], item["direction"], item["edge"]["type"]))

    @staticmethod
    def _options(direction, relation=None):
        if direction not in ("in", "out", "both"):
            raise GraphError("INVALID_ARGUMENT", "direction must be in, out or both.")
        if relation is not None and relation not in RELATIONS:
            raise GraphError("INVALID_ARGUMENT", f"Unknown relation: {relation}.")

    def search(self, query, limit=20):
        if not isinstance(query, str) or not query.strip() or type(limit) is not int or limit < 1:
            raise GraphError("INVALID_ARGUMENT", "Search requires a nonempty query and positive limit.")
        terms, phrase = query.casefold().split(), query.strip().casefold()
        matches = []
        for identifier, node in self.nodes.items():
            fields = [("id", identifier, 100), ("title", node["title"], 60), ("summary", node["summary"], 20),
                      ("tags", " ".join(node["tags"]), 20), ("body", self.contents[identifier], 5)]
            if not all(any(term in value.casefold() for _, value, _ in fields) for term in terms):
                continue
            matched = [name for name, value, _ in fields if any(term in value.casefold() for term in terms)]
            score = sum(weight for _, value, weight in fields for term in terms if term in value.casefold())
            score += 200 if phrase == identifier.casefold() else 0
            score += 120 if phrase == node["title"].casefold() else 0
            matches.append({**self.metadata(identifier), "score": score, "matched_fields": matched})
        matches.sort(key=lambda item: (-item["score"], item["id"]))
        return {"query": query, "total": len(matches), "truncated": len(matches) > limit, "nodes": matches[:limit]}

    def walk(self, identifier, depth=1, max_nodes=50, direction="both", relation=None):
        self.metadata(identifier)
        self._options(direction, relation)
        if type(depth) is not int or depth < 0 or type(max_nodes) is not int or max_nodes < 1:
            raise GraphError("INVALID_ARGUMENT", "depth must be nonnegative; max_nodes must be positive.")
        visited, queue, truncated = {identifier: 0}, deque([identifier]), False
        while queue:
            current = queue.popleft()
            if visited[current] >= depth:
                continue
            for neighbor in self.neighbors(current, direction, relation):
                target = neighbor["node"]["id"]
                if target in visited:
                    continue
                if len(visited) >= max_nodes:
                    truncated = True
                    continue
                visited[target] = visited[current] + 1
                queue.append(target)
        edges = [edge for edge in self.edges if edge["source"] in visited and edge["target"] in visited
                 and (relation is None or edge["type"] == relation)]
        return {"start": identifier, "depth": depth, "direction": direction, "truncated": truncated,
                "nodes": [{**self.metadata(node_id), "distance": distance} for node_id, distance in visited.items()], "edges": edges}

    def path(self, source, target, direction="both"):
        self.metadata(source)
        self.metadata(target)
        self._options(direction)
        parents, queue = {source: None}, deque([source])
        while queue:
            current = queue.popleft()
            if current == target:
                break
            for neighbor in self.neighbors(current, direction):
                identifier = neighbor["node"]["id"]
                if identifier not in parents:
                    parents[identifier] = (current, neighbor["edge"], neighbor["direction"])
                    queue.append(identifier)
        if target not in parents:
            raise GraphError("NO_PATH", f"No {direction} path from {source} to {target}.")
        identifiers, steps, current = [target], [], target
        while parents[current] is not None:
            previous, edge, traversal_direction = parents[current]
            steps.append({"from": previous, "to": current, "direction": traversal_direction, "edge": edge})
            identifiers.append(previous)
            current = previous
        return {"direction": direction, "nodes": [self.metadata(identifier) for identifier in reversed(identifiers)],
                "steps": list(reversed(steps))}
