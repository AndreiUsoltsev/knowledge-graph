import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from knowledge_graph.agents import END, START, manage_agents
from knowledge_graph.core import GraphError
from knowledge_graph.database import install_database


class AgentIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.home = self.root / 'home'
        self.project = self.root / 'project'
        self.home.mkdir()
        self.project.mkdir()

    def manage(self, operation, **kwargs):
        return manage_agents(operation, directory=kwargs.pop('directory', self.project),
                             home=self.home, environ={}, target=kwargs.pop('target', 'all'), **kwargs)

    def test_project_install_preserves_database_and_shared_instructions(self):
        database = Path(install_database(self.project)['database'])
        database_bytes = {p.relative_to(database): p.read_bytes() for p in database.rglob('*') if p.is_file()}
        agents = self.project / 'AGENTS.md'
        agents.write_bytes(b'\xef\xbb\xbf# Existing\r\n\r\nKeep project rules.\r\n')
        claude = self.project / 'CLAUDE.md'
        claude.write_text('Keep Claude rules.\n', encoding='utf-8')
        self.manage('install')
        first = {p.relative_to(self.project): p.read_bytes() for p in self.project.rglob('*') if p.is_file()}
        result = self.manage('install')
        second = {p.relative_to(self.project): p.read_bytes() for p in self.project.rglob('*') if p.is_file()}
        self.assertEqual(first, second)
        self.assertFalse(result['restart_required'])
        self.assertTrue(agents.read_bytes().startswith(b'\xef\xbb\xbf# Existing\r\n'))
        self.assertEqual(agents.read_text(encoding='utf-8-sig').count(START), 1)
        self.assertIn('Keep Claude rules.', claude.read_text())
        self.assertEqual(database_bytes, {p.relative_to(database): p.read_bytes() for p in database.rglob('*') if p.is_file()})
        self.assertTrue(self.manage('doctor')['ready'])

    def test_dry_run_has_no_filesystem_effects(self):
        result = self.manage('install', dry_run=True)
        self.assertTrue(any(f['action'] == 'created' for f in result['files']))
        self.assertEqual(list(self.project.iterdir()), [])

    def test_custom_skill_conflict_is_preflighted_before_any_write(self):
        skill = self.project / '.claude/skills/knowledge-graph/SKILL.md'
        skill.parent.mkdir(parents=True)
        skill.write_text('Custom skill', encoding='utf-8')
        with self.assertRaises(GraphError) as failure:
            self.manage('install')
        self.assertEqual(failure.exception.code, 'AGENT_CONFIG_CONFLICT')
        self.assertFalse((self.project / 'AGENTS.md').exists())
        self.assertFalse((self.project / '.agents').exists())
        self.assertEqual(skill.read_text(), 'Custom skill')

    def test_uninstall_preserves_unmanaged_text_and_shared_targets(self):
        agents = self.project / 'AGENTS.md'
        agents.write_text('Keep before.\n', encoding='utf-8')
        self.manage('install', target='codex,opencode')
        agents.write_text(agents.read_text() + '\nKeep after.\n', encoding='utf-8')
        self.manage('uninstall', target='codex')
        self.assertIn(START, agents.read_text())
        self.assertTrue((self.project / '.agents/skills/knowledge-graph/SKILL.md').is_file())
        self.manage('uninstall', target='opencode')
        self.assertNotIn(START, agents.read_text())
        self.assertIn('Keep before.', agents.read_text())
        self.assertIn('Keep after.', agents.read_text())
        self.assertFalse((self.project / '.agents/skills/knowledge-graph/SKILL.md').exists())
        self.assertFalse((self.project / '.agents/knowledge-graph-integrations.json').exists())
        self.manage('uninstall', target='opencode')
        self.assertIn('Keep before.', agents.read_text())

    def test_uninstall_leaves_custom_empty_rule_and_custom_skill(self):
        rule = self.project / 'AGENTS.md'
        rule.write_bytes(b'\r\n')
        skill = self.project / '.agents/skills/knowledge-graph/SKILL.md'
        skill.parent.mkdir(parents=True)
        skill.write_text('Custom', encoding='utf-8')
        self.manage('uninstall', target='codex')
        self.assertEqual(rule.read_bytes(), b'\r\n')
        self.assertEqual(skill.read_text(), 'Custom')

    def test_malformed_markers_are_rejected_without_changes(self):
        rule = self.project / 'AGENTS.md'
        for text in [START, END + START, START + END + START + END]:
            with self.subTest(text=text):
                rule.write_text(text, encoding='utf-8')
                with self.assertRaises(GraphError):
                    self.manage('install')
                self.assertEqual(rule.read_text(), text)

    def test_user_scope_honors_config_roots_and_cursor_has_no_global_rule(self):
        codex = self.home / 'custom-codex'
        xdg = self.home / 'custom-config'
        result = manage_agents('install', scope='user', target='all', home=self.home,
                               environ={'CODEX_HOME': str(codex), 'XDG_CONFIG_HOME': str(xdg)})
        self.assertTrue((codex / 'AGENTS.md').exists())
        self.assertTrue((xdg / 'opencode/AGENTS.md').exists())
        self.assertTrue((self.home / '.claude/CLAUDE.md').exists())
        self.assertTrue((self.home / '.agents/skills/knowledge-graph/SKILL.md').exists())
        self.assertFalse((self.home / '.cursor/rules').exists())
        self.assertTrue(any('Cursor user scope' in w for w in result['warnings']))

    def test_auto_detects_only_existing_agents(self):
        (self.home / '.codex').mkdir()
        with patch('knowledge_graph.agents.shutil.which', return_value=None):
            result = self.manage('install', target='auto')
        self.assertEqual(result['targets'], ['codex'])
        self.assertFalse((self.project / 'CLAUDE.md').exists())
        self.assertFalse((self.project / '.cursor').exists())

    def test_doctor_detects_missing_changed_files_and_codex_override(self):
        self.manage('install', target='codex,cursor')
        self.assertTrue(self.manage('doctor', target='codex,cursor')['ready'])
        cursor = self.project / '.cursor/rules/knowledge-graph.mdc'
        cursor.write_text(cursor.read_text().replace('alwaysApply: true', 'alwaysApply: false'))
        self.assertFalse(self.manage('doctor', target='cursor')['ready'])
        self.assertIn('outdated', [f['status'] for f in self.manage('doctor', target='cursor')['files']])
        (self.project / 'AGENTS.override.md').write_text('Override rules')
        self.assertTrue(self.manage('doctor', target='codex')['warnings'])
        (self.project / '.agents/skills/knowledge-graph/SKILL.md').unlink()
        self.assertIn('missing', [f['status'] for f in self.manage('doctor', target='codex')['files']])

    def test_linked_customization_directory_is_rejected(self):
        outside = self.root / 'outside'
        outside.mkdir()
        try:
            (self.project / '.agents').symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest('Symlink privilege unavailable')
        with self.assertRaises(GraphError):
            self.manage('install')
        self.assertEqual(list(outside.iterdir()), [])

    def test_invalid_arguments_and_registry_are_preserved(self):
        with self.assertRaises(GraphError):
            self.manage('install', target='unknown')
        with self.assertRaises(GraphError):
            self.manage('install', scope='user')
        path = self.project / '.agents/knowledge-graph-integrations.json'
        path.parent.mkdir()
        path.write_text('custom malformed state')
        with self.assertRaises(GraphError):
            self.manage('install')
        self.assertEqual(path.read_text(), 'custom malformed state')

    def test_partial_io_failure_restores_previously_changed_files(self):
        rule = self.project / 'AGENTS.md'
        rule.write_text('Original', encoding='utf-8')
        write = Path.write_bytes
        def fail_claude(path, data):
            if path == self.project / 'CLAUDE.md':
                raise OSError('simulated write failure')
            return write(path, data)
        with patch.object(Path, 'write_bytes', fail_claude):
            with self.assertRaises(OSError):
                self.manage('install')
        self.assertEqual(rule.read_text(), 'Original')
        self.assertFalse((self.project / 'CLAUDE.md').exists())
        self.assertFalse((self.project / '.agents/knowledge-graph-integrations.json').exists())

    def test_cli_works_without_a_database_and_reports_doctor_exit_status(self):
        def cli(*args):
            return subprocess.run([sys.executable, '-m', 'knowledge_graph', *args], cwd=self.project,
                                  capture_output=True, encoding='utf-8', timeout=10)
        before = cli('agents', 'doctor', '--target', 'all')
        self.assertEqual(before.returncode, 1)
        self.assertFalse(json.loads(before.stdout)['data']['ready'])
        result = cli('agents', 'install', '--target', 'all')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.project / '.knowledge-graph').exists())
        after = cli('agents', 'doctor', '--target', 'all')
        self.assertEqual(after.returncode, 0, after.stdout)
        self.assertTrue(json.loads(after.stdout)['data']['ready'])
        invalid = cli('--db', 'anything', 'agents', 'install')
        self.assertEqual(json.loads(invalid.stderr)['code'], 'USAGE_ERROR')


if __name__ == '__main__':
    unittest.main()
