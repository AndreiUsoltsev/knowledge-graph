import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from knowledge_graph.core import Graph, GraphError, inspect_database
from knowledge_graph.database import install_database, resolve_database


class InstallationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def test_install_and_discover_from_nested_directory(self):
        instructions = self.root / "AGENTS.md"
        instructions.write_text("existing instructions", encoding="utf-8")
        result = install_database(self.root)
        database = self.root / ".knowledge-graph"
        self.assertEqual(Path(result["database"]), database)
        self.assertEqual(instructions.read_text(), "existing instructions")
        self.assertEqual(set(self.root.iterdir()), {instructions, database})
        nested = self.root / "src" / "nested"
        nested.mkdir(parents=True)
        self.assertEqual(resolve_database(cwd=nested), database)
        self.assertEqual(resolve_database(database, cwd=nested), database)
        report, graph = inspect_database(database)
        self.assertTrue(report["valid"], report)
        self.assertEqual(len(graph.nodes), 7)
        self.assertEqual(len(graph.edges), 15)
        self.assertEqual(report["warnings"], [])

    def test_existing_database_not_overwritten(self):
        database = Path(install_database(self.root)["database"])
        manifest = database / "graph.json"
        manifest.write_text("user content", encoding="utf-8")
        with self.assertRaises(GraphError) as error:
            install_database(self.root)
        self.assertEqual(error.exception.code, "DATABASE_EXISTS")
        self.assertEqual(manifest.read_text(), "user content")

    def test_existing_file_rejected(self):
        target = self.root / ".knowledge-graph"
        target.write_text("keep", encoding="utf-8")
        with self.assertRaises(GraphError) as error:
            install_database(self.root)
        self.assertEqual(error.exception.code, "DATABASE_EXISTS")
        self.assertEqual(target.read_text(), "keep")

    def test_failed_copy_leaves_no_partial_database(self):
        with patch("knowledge_graph.database._copy_resources", side_effect=OSError("read failed")):
            with self.assertRaises(OSError):
                install_database(self.root)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_invalid_template_is_not_installed(self):
        with patch("knowledge_graph.database.inspect_database", return_value=({"valid": False, "errors": [], "warnings": []}, None)):
            with self.assertRaises(GraphError) as error:
                install_database(self.root)
        self.assertEqual(error.exception.code, "INVALID_SEED")
        self.assertEqual(list(self.root.iterdir()), [])

    def test_nearest_broken_database_does_not_fall_back(self):
        install_database(self.root)
        child = self.root / "child"
        (child / ".knowledge-graph").mkdir(parents=True)
        nearest = resolve_database(cwd=child)
        self.assertEqual(nearest, child / ".knowledge-graph")
        self.assertFalse(inspect_database(nearest)[0]["valid"])

    def test_missing_database_hint(self):
        with self.assertRaises(GraphError) as error:
            resolve_database(cwd=self.root)
        self.assertEqual(error.exception.code, "DATABASE_NOT_FOUND")
        self.assertIn("install", str(error.exception))

    def test_explicit_missing_database_hint(self):
        with self.assertRaises(GraphError) as error:
            resolve_database(self.root / "missing")
        self.assertEqual(error.exception.code, "DATABASE_NOT_FOUND")
        self.assertIn("install", str(error.exception))

    def cli(self, *args, cwd=None):
        return subprocess.run([sys.executable, "-m", "knowledge_graph", *args], cwd=cwd or self.root, capture_output=True, timeout=10)

    def test_cli_default_install_and_nested_discovery(self):
        result = self.cli("install")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(Path(json.loads(result.stdout)["data"]["database"]), self.root / ".knowledge-graph")
        child = self.root / "child"
        child.mkdir()
        result = self.cli("entry", cwd=child)
        self.assertEqual(json.loads(result.stdout)["data"][0]["title"], "Documentation system")
        result = self.cli("install")
        self.assertEqual(json.loads(result.stderr)["code"], "DATABASE_EXISTS")


class TranslationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.database = Path(install_database(self.temp.name)["database"])

    def test_all_seed_translations_and_english_default(self):
        en, ru = Graph.load(self.database), Graph.load(self.database, "ru")
        self.assertEqual(en.node("system.agent")["title"], "AI agent workflow")
        self.assertEqual(ru.node("system.agent")["title"], "Работа ИИ-агента")
        self.assertIn("# AI agent workflow", en.node("system.agent")["body"])
        self.assertIn("# Работа ИИ-агента", ru.node("system.agent")["body"])
        for identifier in en.nodes:
            self.assertNotEqual(en.metadata(identifier)["title"], ru.metadata(identifier)["title"])
            self.assertNotEqual(en.node(identifier)["body"], ru.node(identifier)["body"])
            self.assertEqual(en.metadata(identifier)["id"], ru.metadata(identifier)["id"])
        for a, b in zip(en.edges, ru.edges):
            self.assertNotEqual(a["label"], b["label"])
            self.assertEqual(a["type"], b["type"])
        self.assertTrue(ru.search("недостижимых")["nodes"])
        self.assertFalse(en.search("недостижимых")["nodes"])
        self.assertTrue(en.search("navigation")["nodes"])

    def test_untranslated_nodes_and_edges_use_original(self):
        path = self.database / "graph.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        for item in manifest["nodes"] + manifest["edges"]:
            item.pop("translations", None)
        path.write_text(json.dumps(manifest), encoding="utf-8")
        en, ru = Graph.load(self.database), Graph.load(self.database, "ru")
        self.assertEqual(en.node("system.agent"), ru.node("system.agent"))
        self.assertEqual(en.search("workflow"), ru.search("workflow"))

    def test_all_languages_validated_even_when_reading_english(self):
        path = self.database / "graph.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        for change in (lambda n: n["translations"]["ru"].update(content="../outside.md"),
                       lambda n: n["translations"]["ru"].pop("tags"),
                       lambda n: n["translations"]["ru"].update(title="")):
            modified = json.loads(json.dumps(manifest))
            change(modified["nodes"][0])
            path.write_text(json.dumps(modified), encoding="utf-8")
            self.assertFalse(inspect_database(self.database, "en")[0]["valid"])

    def test_unknown_language(self):
        with self.assertRaises(GraphError) as error:
            Graph.load(self.database, "de")
        self.assertEqual(error.exception.code, "INVALID_LANGUAGE")


if __name__ == "__main__":
    unittest.main()
