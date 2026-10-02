"""Verify built wheel and sdist, then exercise an isolated wheel installation."""
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from knowledge_graph import __version__

ROOT = Path(__file__).resolve().parents[1]


def run(*args, cwd=None):
    result = subprocess.run(args, cwd=cwd or ROOT, capture_output=True, encoding="utf-8", timeout=120)
    if result.returncode:
        raise RuntimeError(f"Command failed: {args!r}\n{result.stdout}\n{result.stderr}")
    return result.stdout


def main():
    wheel, = (ROOT / "dist").glob(f"knowledge_graph-{__version__}-*.whl")
    sdist, = (ROOT / "dist").glob(f"knowledge_graph-{__version__}.tar.gz")
    resources = [f"knowledge_graph/web/{name}" for name in ("index.html", "app.js", "i18n.js", "style.css")]
    resources += ["knowledge_graph/seed/graph.json", "knowledge_graph/seed/README.md"]
    resources += [f"knowledge_graph/agent_templates/{name}" for name in ("SKILL.md", "rule.md", "openai.yaml")]
    for name in ("overview", "format", "links", "agent", "human", "viewer", "validation"):
        resources += [f"knowledge_graph/seed/content/system.{name}.md", f"knowledge_graph/seed/content/ru/system.{name}.md"]
    with zipfile.ZipFile(wheel) as archive:
        missing = set(resources) - set(archive.namelist())
        assert not missing, missing
    with tarfile.open(sdist) as archive:
        members = archive.getnames()
        for resource in resources:
            assert any(name.endswith("/src/" + resource) for name in members), resource

    with tempfile.TemporaryDirectory(prefix="knowledge-graph-distribution-") as folder:
        outside = Path(folder)
        env = outside / "env"
        run("uv", "venv", str(env), "--python", sys.executable)
        python = env / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        cli = env / ("Scripts/knowledge-graph.exe" if sys.platform == "win32" else "bin/knowledge-graph")
        run("uv", "pip", "install", "--python", str(python), str(wheel))
        project = outside / "project"
        result = json.loads(run(str(cli), "install", str(project), cwd=outside))
        assert result["data"]["nodes"] == 7
        assert result["data"]["edges"] == 15
        nested = project / "src" / "nested"
        nested.mkdir(parents=True)
        entry = json.loads(run(str(cli), "entry", cwd=nested))
        assert entry["data"][0]["title"] == "Documentation system"
        russian = json.loads(run(str(python), "-m", "knowledge_graph", "--lang", "ru", "node", "system.agent", cwd=nested))
        assert russian["data"]["title"] == "Работа ИИ-агента"
        assert json.loads(run(str(cli), "validate", cwd=project))["data"]["valid"]
        database = project / ".knowledge-graph"
        installed = json.loads(run(str(cli), "agents", "install", "--dir", str(project), "--target", "all", cwd=outside))
        assert installed["success"]
        assert json.loads(run(str(cli), "agents", "doctor", "--dir", str(project), "--target", "all", cwd=outside))["data"]["ready"]
        assert "name: knowledge-graph" in (project / ".agents/skills/knowledge-graph/SKILL.md").read_text(encoding="utf-8")
        assert "alwaysApply: true" in (project / ".cursor/rules/knowledge-graph.mdc").read_text(encoding="utf-8")
        assert json.loads(run(str(cli), "validate", cwd=project))["data"]["valid"]
        assert json.loads(run(str(cli), "agents", "uninstall", "--dir", str(project), "--target", "all", cwd=outside))["success"]
        assert not (project / ".agents/skills/knowledge-graph/SKILL.md").exists()
        smoke = '''
import json, sys, threading
from urllib.request import urlopen
from knowledge_graph.server import make_server
server = make_server(sys.argv[1], 0)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
try:
    base = f"http://127.0.0.1:{server.server_port}"
    for path in ("/", "/app.js", "/i18n.js", "/style.css"):
        with urlopen(base + path, timeout=5) as response:
            assert response.status == 200 and response.read()
    with urlopen(base + "/api/node?id=system.agent&lang=ru", timeout=5) as response:
        assert json.load(response)["data"]["title"] == "Работа ИИ-агента"
finally:
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)
print("Installed wheel: CLI, discovery, translations and GUI resources passed.")
'''
        print(run(str(python), "-c", smoke, str(database), cwd=outside).strip())
    print("Wheel and sdist include all browser and bilingual seed resources.")


if __name__ == "__main__":
    main()
