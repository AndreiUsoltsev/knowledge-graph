import copy
from http.client import HTTPConnection
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest

from knowledge_graph.core import Graph, GraphError, inspect_database
from knowledge_graph.database import install_database
from knowledge_graph.server import make_server


class DatabaseCase(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.database = Path(self.temporary.name) / "database"
        (self.database / "content").mkdir(parents=True)
        self.manifest = {"version": 1, "entry_points": ["a"], "nodes": [], "edges": []}
        for identifier, title, body in (
            ("a", "Обзор документации", "# Обзор\n\nОбщие правила и навигация."),
            ("b", "Навигация агента", "# Агент\n\nПереходы по связям."),
            ("c", "Проверка", "# Проверка\n\nУникальный термин целостность."),
        ):
            self.add_node(identifier, title, body)
        self.manifest["edges"] = [
            {"source": "a", "target": "b", "type": "contains", "label": "Как перейти к работе агента."},
            {"source": "b", "target": "c", "type": "requires", "label": "Проверить структуру."},
            {"source": "c", "target": "a", "type": "related", "label": "Вернуться к обзору."},
        ]
        self.save()

    def add_node(self, identifier, title="Изолированный узел", body="# Отдельная тема"):
        self.manifest["nodes"].append({"id": identifier, "title": title, "type": "concept",
            "summary": f"Описание {identifier}", "tags": ["граф"], "content": f"content/{identifier}.md"})
        (self.database / "content" / f"{identifier}.md").write_text(body, encoding="utf-8")

    def save(self):
        (self.database / "graph.json").write_text(json.dumps(self.manifest, ensure_ascii=False), encoding="utf-8")

    def assert_invalid(self, code):
        self.save()
        report, graph = inspect_database(self.database)
        self.assertFalse(report["valid"])
        self.assertIsNone(graph)
        self.assertIn(code, [item["code"] for item in report["errors"]])
        with self.assertRaises(GraphError) as failure:
            Graph.load(self.database)
        self.assertEqual(failure.exception.code, "INVALID_DATABASE")


class GraphTests(DatabaseCase):
    def test_entries_and_document(self):
        graph = Graph.load(self.database)
        self.assertEqual([node["id"] for node in graph.entries()], ["a"])
        node = graph.node("a")
        self.assertIn("Общие правила", node["body"])
        self.assertEqual(len(node["neighbors"]), 2)
        self.assertTrue(all("body" not in neighbor["node"] for neighbor in node["neighbors"]))

    def test_russian_search_and_ranking(self):
        graph = Graph.load(self.database)
        result = graph.search("НАВИГАЦИЯ")
        self.assertEqual(result["nodes"][0]["id"], "b")
        self.assertEqual(graph.search("целостность")["nodes"][0]["id"], "c")
        self.assertEqual(graph.search("неизвестно")["total"], 0)
        self.assertEqual(graph.search("агента навигация")["total"], 1)
        result = graph.search("граф", limit=1)
        self.assertEqual(result["total"], 3)
        self.assertTrue(result["truncated"])
        self.assertEqual(result["nodes"][0]["id"], "a")

    def test_neighbors_direction_and_relation(self):
        graph = Graph.load(self.database)
        outgoing = graph.neighbors("b", "out", "requires")
        self.assertEqual(outgoing[0]["node"]["id"], "c")
        incoming = graph.neighbors("b", "in")
        self.assertEqual(incoming[0]["node"]["id"], "a")
        self.assertEqual(incoming[0]["edge"]["source"], "a")
        self.assertEqual(graph.neighbors("b", relation="explains"), [])

    def test_cycle_depth_and_node_limit(self):
        graph = Graph.load(self.database)
        result = graph.walk("a", depth=100)
        self.assertEqual(len(result["nodes"]), 3)
        self.assertFalse(result["truncated"])
        self.assertEqual(graph.walk("a", depth=0)["nodes"][0]["distance"], 0)
        self.assertEqual(len(graph.walk("a", depth=0)["nodes"]), 1)
        result = graph.walk("a", depth=10, max_nodes=2)
        self.assertEqual(len(result["nodes"]), 2)
        self.assertTrue(result["truncated"])
        result = graph.walk("a", depth=1, direction="out")
        self.assertEqual([node["id"] for node in result["nodes"]], ["a", "b"])
        self.assertEqual(result["nodes"][1]["distance"], 1)
        self.assertEqual(graph.walk("b", depth=3, relation="requires")["nodes"][1]["id"], "c")

    def test_shortest_path_and_reverse_steps(self):
        graph = Graph.load(self.database)
        result = graph.path("a", "c", direction="out")
        self.assertEqual([node["id"] for node in result["nodes"]], ["a", "b", "c"])
        result = graph.path("a", "c")
        self.assertEqual(len(result["steps"]), 1)
        self.assertEqual(result["steps"][0]["direction"], "in")
        self.assertEqual(result["steps"][0]["edge"]["source"], "c")
        self.assertEqual(graph.path("a", "a")["steps"], [])

    def test_disconnected_nodes_warn_and_no_path_errors(self):
        self.add_node("d")
        self.save()
        report, graph = inspect_database(self.database)
        self.assertTrue(report["valid"])
        self.assertEqual(report["warnings"][0]["code"], "UNREACHABLE_NODE")
        with self.assertRaises(GraphError) as failure:
            graph.path("a", "d")
        self.assertEqual(failure.exception.code, "NO_PATH")

    def test_reachability_beyond_one_hop(self):
        self.manifest["edges"] = self.manifest["edges"][:2]
        self.save()
        report, _ = inspect_database(self.database)
        self.assertEqual(report["warnings"], [])

    def test_self_loop_does_not_repeat_node(self):
        self.manifest["edges"].append({"source": "a", "target": "a", "type": "related", "label": "Самоссылка"})
        self.save()
        self.assertEqual(len(Graph.load(self.database).walk("a", 20)["nodes"]), 3)

    def test_unknown_node_and_invalid_arguments(self):
        graph = Graph.load(self.database)
        with self.assertRaises(GraphError) as failure:
            graph.node("missing")
        self.assertEqual(failure.exception.code, "UNKNOWN_NODE")
        for action in (lambda: graph.walk("a", -1), lambda: graph.walk("a", max_nodes=0),
                       lambda: graph.search(" "), lambda: graph.search("граф", 0),
                       lambda: graph.neighbors("a", "sideways"), lambda: graph.neighbors("a", relation="unknown")):
            with self.assertRaises(GraphError) as failure:
                action()
            self.assertEqual(failure.exception.code, "INVALID_ARGUMENT")

    def test_snapshot_omits_document_bodies(self):
        snapshot = Graph.load(self.database).snapshot()
        self.assertTrue(all("body" not in node for node in snapshot["nodes"]))
        self.assertEqual(len(snapshot["edges"]), 3)

    def test_seed_database(self):
        installed = install_database(Path(self.temporary.name) / "seed-project")
        report, graph = inspect_database(installed["database"])
        self.assertTrue(report["valid"], report)
        self.assertEqual(report["warnings"], [])
        self.assertEqual(len(graph.nodes), 7)
        self.assertEqual(len(graph.walk("system.overview", depth=10)["nodes"]), 7)


class ValidationTests(DatabaseCase):
    def test_duplicate_id(self):
        self.manifest["nodes"].append(copy.deepcopy(self.manifest["nodes"][0]))
        self.assert_invalid("DUPLICATE_ID")

    def test_invalid_fields(self):
        original = copy.deepcopy(self.manifest)
        cases = [("title", "", "INVALID_NODE"), ("id", "Invalid ID", "INVALID_ID"),
                 ("type", "unknown", "INVALID_NODE_TYPE"), ("tags", "graph", "INVALID_TAGS"),
                 ("tags", [1], "INVALID_TAGS")]
        for key, value, code in cases:
            with self.subTest(field=key, value=value):
                self.manifest = copy.deepcopy(original)
                self.manifest["nodes"][0][key] = value
                self.assert_invalid(code)

    def test_versions_and_array_fields(self):
        original = copy.deepcopy(self.manifest)
        for version in (2, True, "1"):
            with self.subTest(version=version):
                self.manifest = copy.deepcopy(original)
                self.manifest["version"] = version
                self.assert_invalid("UNSUPPORTED_VERSION")
        for field in ("nodes", "edges", "entry_points"):
            with self.subTest(field=field):
                self.manifest = copy.deepcopy(original)
                self.manifest[field] = None
                self.assert_invalid("INVALID_MANIFEST")

    def test_entries_and_empty_graph(self):
        original = copy.deepcopy(self.manifest)
        for value, code in (([], "MISSING_ENTRY_POINT"), (["missing"], "INVALID_ENTRY_POINT"),
                            (["a", "a"], "DUPLICATE_ENTRY_POINT"), ([{}], "INVALID_ENTRY_POINT")):
            with self.subTest(value=value):
                self.manifest = copy.deepcopy(original)
                self.manifest["entry_points"] = value
                self.assert_invalid(code)
        self.manifest["nodes"] = []
        self.assert_invalid("EMPTY_GRAPH")

    def test_dangling_unknown_and_duplicate_edges(self):
        original = copy.deepcopy(self.manifest)
        self.manifest["edges"][0]["target"] = "missing"
        self.assert_invalid("DANGLING_EDGE")
        self.manifest = copy.deepcopy(original)
        self.manifest["edges"][0]["type"] = "unknown"
        self.assert_invalid("INVALID_RELATION")
        self.manifest = copy.deepcopy(original)
        self.manifest["edges"].append(copy.deepcopy(self.manifest["edges"][0]))
        self.assert_invalid("DUPLICATE_EDGE")
        self.manifest = copy.deepcopy(original)
        self.manifest["edges"][0]["label"] = ""
        self.assert_invalid("INVALID_EDGE")

    def test_documents_missing_empty_and_non_utf8(self):
        document = self.database / "content" / "a.md"
        document.unlink()
        self.assert_invalid("INVALID_DOCUMENT")
        document.write_text(" ", encoding="utf-8")
        self.assert_invalid("EMPTY_DOCUMENT")
        document.write_bytes(b"\xff\xfe\xff")
        self.assert_invalid("INVALID_DOCUMENT")

    def test_unsafe_document_paths(self):
        for path in ("../outside.md", str(Path(self.temporary.name) / "outside.md"),
                     "content\\a.md", "content/a.txt", "C:/outside.md", "content/\0.md"):
            with self.subTest(path=path):
                self.manifest["nodes"][0]["content"] = path
                self.assert_invalid("UNSAFE_CONTENT_PATH")

    def test_symlink_cannot_escape_database(self):
        outside = Path(self.temporary.name) / "outside.md"
        outside.write_text("outside", encoding="utf-8")
        link = self.database / "content" / "link.md"
        try:
            link.symlink_to(outside)
        except OSError:
            self.skipTest("Creating symlinks is unavailable on this host.")
        self.manifest["nodes"][0]["content"] = "content/link.md"
        self.assert_invalid("UNSAFE_CONTENT_PATH")

    def test_malformed_json_and_missing_manifest(self):
        manifest = self.database / "graph.json"
        for value in ("{broken", "[]"):
            manifest.write_text(value, encoding="utf-8")
            report, graph = inspect_database(self.database)
            self.assertFalse(report["valid"])
            self.assertIsNone(graph)
        manifest.unlink()
        report, _ = inspect_database(self.database)
        self.assertEqual(report["errors"][0]["code"], "INVALID_MANIFEST")

    def test_utf8_bom(self):
        (self.database / "graph.json").write_text(json.dumps(self.manifest), encoding="utf-8-sig")
        (self.database / "content" / "a.md").write_text("# Русский текст", encoding="utf-8-sig")
        self.assertIn("Русский", Graph.load(self.database).node("a")["body"])


class CliTests(DatabaseCase):
    def run_cli(self, *args, custom_database=True):
        prefix = [sys.executable, "-m", "knowledge_graph"]
        if custom_database:
            prefix += ["--db", str(self.database)]
        return subprocess.run(prefix + list(args), cwd=self.temporary.name, capture_output=True, timeout=10)

    def test_every_data_command_from_another_directory(self):
        for args in (("entry",), ("search", "НАВИГАЦИЯ"), ("node", "a"),
                     ("neighbors", "a"), ("walk", "a", "--depth", "2"), ("path", "a", "c"), ("validate",)):
            with self.subTest(command=args):
                result = self.run_cli(*args)
                self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8"))
                self.assertTrue(json.loads(result.stdout.decode("utf-8"))["success"])
                self.assertEqual(result.stderr, b"")
        install_database(self.temporary.name)
        result = self.run_cli("entry", custom_database=False)
        self.assertEqual(json.loads(result.stdout)["data"][0]["id"], "system.overview")

    def test_error_envelopes_and_exit_codes(self):
        result = self.run_cli("node", "unknown")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, b"")
        self.assertEqual(json.loads(result.stderr)["code"], "UNKNOWN_NODE")
        for args in (("walk", "a", "--depth", "-1"), ("search", "text", "--limit", "0"),
                     ("entry", "--unknown"), ("serve", "--port", "65536")):
            with self.subTest(args=args):
                result = self.run_cli(*args)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(json.loads(result.stderr)["success"])
        self.manifest["edges"][0]["target"] = "missing"
        self.save()
        result = self.run_cli("validate")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["code"], "INVALID_DATABASE")


class HttpTests(DatabaseCase):
    def test_language_parameters_and_localized_labels(self):
        self.manifest["nodes"][0]["translations"] = {"ru": {
            "title": "Русский заголовок", "summary": "Русское описание", "tags": ["перевод"], "content": "content/a-ru.md"}}
        (self.database / "content/a-ru.md").write_text("# Переведённый документ\n\nУникальный текст перевода.", encoding="utf-8")
        self.manifest["edges"][0]["translations"] = {"ru": {"label": "Русское пояснение связи"}}
        self.save()
        english = json.loads(self.request("/api/node?id=a")[2])["data"]
        russian = json.loads(self.request("/api/node?id=a&lang=ru")[2])["data"]
        self.assertEqual(english["title"], "Обзор документации")
        self.assertEqual(russian["title"], "Русский заголовок")
        self.assertIn("Переведённый документ", russian["body"])
        self.assertEqual(russian["neighbors"][0]["edge"]["label"], "Русское пояснение связи")
        for path in ("/api/graph?lang=ru", "/api/walk?id=a&lang=ru"):
            self.assertEqual(self.request(path)[0], 200)
        from urllib.parse import quote
        query = quote("переведённый")
        self.assertTrue(json.loads(self.request(f"/api/search?q={query}&lang=ru")[2])["data"]["nodes"])
        self.assertFalse(json.loads(self.request(f"/api/search?q={query}&lang=en")[2])["data"]["nodes"])
        self.assertEqual(self.request("/api/node?id=a&lang=de")[0], 400)
        self.assertEqual(self.request("/api/graph?lang=en&lang=ru")[0], 400)

    def setUp(self):
        super().setUp()
        self.server = make_server(self.database, 0)
        self.thread = threading.Thread(target=lambda: self.server.serve_forever(poll_interval=.02), daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def request(self, path, method="GET", headers=None):
        connection = HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        try:
            connection.request(method, path, headers=headers or {})
            response = connection.getresponse()
            return response.status, response.getheader("Content-Type"), response.read()
        finally:
            connection.close()

    def test_static_files_and_api(self):
        for path in ("/", "/app.js", "/style.css", "/i18n.js"):
            status, mime, body = self.request(path)
            self.assertEqual(status, 200)
            self.assertTrue(body)
        for path in ("/api/graph", "/api/node?id=a", "/api/search?q=%D0%B3%D1%80%D0%B0%D1%84", "/api/walk?id=a&depth=2", "/api/validate"):
            with self.subTest(path=path):
                status, mime, body = self.request(path)
                self.assertEqual(status, 200)
                self.assertIn("application/json", mime)
                self.assertTrue(json.loads(body)["success"])
        self.assertEqual(self.server.server_address[0], "127.0.0.1")

    def test_rejects_writes_and_arbitrary_files(self):
        for method in ("POST", "PUT", "PATCH", "DELETE", "OPTIONS"):
            status, _, body = self.request("/api/graph", method)
            self.assertEqual(status, 405)
            self.assertEqual(json.loads(body)["code"], "READ_ONLY")
        for path in ("/graph.json", "/content/a.md", "/../AGENTS.md", "/%2e%2e/AGENTS.md"):
            self.assertEqual(self.request(path)[0], 404)

    def test_parameters_unknown_node_and_host(self):
        self.assertEqual(self.request("/api/node?id=missing")[0], 404)
        for path in ("/api/node", "/api/node?id=a&id=b", "/api/walk?id=a&depth=-1", "/api/walk?id=a&depth=nan"):
            self.assertEqual(self.request(path)[0], 400)
        self.assertEqual(self.request("/api/graph", headers={"Host": "untrusted.example"})[0], 400)

    def test_reload_reads_edits_and_never_serves_invalid_graph(self):
        self.manifest["nodes"][0]["title"] = "Новое название"
        self.save()
        status, _, body = self.request("/api/node?id=a")
        self.assertEqual(json.loads(body)["data"]["title"], "Новое название")
        self.manifest["edges"][0]["target"] = "missing"
        self.save()
        for path in ("/api/graph", "/api/node?id=a", "/api/search?q=graph", "/api/walk?id=a"):
            status, _, body = self.request(path)
            self.assertEqual(status, 422)
            result = json.loads(body)
            self.assertEqual(result["code"], "INVALID_DATABASE")
            self.assertNotIn("data", result)
        self.assertFalse(json.loads(self.request("/api/validate")[2])["data"]["valid"])
        self.assertEqual(self.request("/")[0], 200)


if __name__ == "__main__":
    unittest.main()
