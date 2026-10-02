"""Install narrowly scoped rules and portable skills without changing databases."""
from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files
import json
import os
from pathlib import Path
import shutil

from . import __version__
from .core import GraphError

TARGETS = ('codex', 'cursor', 'claude', 'opencode')
START = '<!-- KNOWLEDGE_GRAPH_START -->'
END = '<!-- KNOWLEDGE_GRAPH_END -->'
SKILL_MARKER = 'KNOWLEDGE_GRAPH_MANAGED_SKILL'
REGISTRY = '.agents/knowledge-graph-integrations.json'


@dataclass(frozen=True)
class Artifact:
    path: Path
    root: Path
    kind: str
    text: str
    targets: tuple[str, ...]


def _template(name):
    return files('knowledge_graph').joinpath('agent_templates', name).read_text(encoding='utf-8').rstrip() + '\n'


def _paths(home, environ):
    return {'codex': Path(environ.get('CODEX_HOME') or home / '.codex').expanduser().resolve(),
            'opencode': Path(environ.get('XDG_CONFIG_HOME') or home / '.config').expanduser().resolve() / 'opencode'}


def _read(path):
    if not path.exists():
        return None
    if not path.is_file():
        raise GraphError('AGENT_CONFIG_CONFLICT', f'Expected a file: {path}')
    raw = path.read_bytes()
    try:
        raw.decode('utf-8-sig')
    except UnicodeDecodeError as exc:
        raise GraphError('AGENT_CONFIG_CONFLICT', f'Instructions must be UTF-8: {path}') from exc
    return raw


def _safe(path, root):
    resolved = path.resolve()
    if resolved != root and root not in resolved.parents:
        raise GraphError('AGENT_CONFIG_CONFLICT', f'Integration path escapes its configured root: {path}')
    # Refuse links even when they point within the root: changing shared files
    # through a linked customization directory can affect unrelated projects.
    current = path
    while current != root:
        if current.is_symlink() or getattr(current, 'is_junction', lambda: False)():
            raise GraphError('AGENT_CONFIG_CONFLICT', f'Linked integration path requires manual setup: {current}')
        current = current.parent


def _state(path):
    raw = _read(path)
    if raw is None:
        return {'version': 1, 'targets': []}
    try:
        value = json.loads(raw.decode('utf-8-sig'))
        targets = value['targets']
        if value['version'] != 1 or not isinstance(targets, list) or any(t not in TARGETS for t in targets):
            raise ValueError('Unsupported integration registry')
        return value
    except (ValueError, KeyError, TypeError) as exc:
        raise GraphError('AGENT_CONFIG_CONFLICT', f'Invalid integration registry: {path}') from exc


def _select(target, scope, home, environ, state):
    if target == 'all':
        return list(TARGETS)
    if target == 'auto':
        paths = _paths(home, environ)
        detected = {t for t in TARGETS if shutil.which(t)} | set(state['targets'])
        for t, directory in {'codex': paths['codex'], 'cursor': home / '.cursor',
                             'claude': home / '.claude', 'opencode': paths['opencode']}.items():
            if directory.is_dir():
                detected.add(t)
        return [t for t in TARGETS if t in detected]
    selected = target.split(',')
    if not selected or any(t not in TARGETS for t in selected):
        raise GraphError('USAGE_ERROR', 'Use --target auto, all, or comma-separated codex,cursor,claude,opencode.')
    return list(dict.fromkeys(selected))


def _artifacts(scope, root, home, environ):
    rule = START + '\n## Knowledge Graph\n\n' + _template('rule.md').rstrip() + '\n' + END
    skill = _template('SKILL.md')
    metadata = _template('openai.yaml')
    if scope == 'project':
        rules = [(root / 'AGENTS.md', root, ('codex', 'opencode')),
                 (root / 'CLAUDE.md', root, ('claude',)),
                 (root / '.cursor/rules/knowledge-graph.mdc', root, ('cursor',))]
        cursor_text = '---\ndescription: Use the project documentation graph when project context is needed\nalwaysApply: true\n---\n\n' + rule + '\n'
    else:
        paths = _paths(home, environ)
        rules = [(paths['codex'] / 'AGENTS.md', paths['codex'], ('codex',)),
                 (paths['opencode'] / 'AGENTS.md', paths['opencode'], ('opencode',)),
                 (home / '.claude/CLAUDE.md', home, ('claude',))]
    result = [Artifact(p, allowed, 'cursor_rule' if owners == ('cursor',) else 'rule',
                       cursor_text if owners == ('cursor',) else rule, owners) for p, allowed, owners in rules]
    for directory, owners in [(root / '.agents/skills/knowledge-graph', ('codex', 'cursor', 'opencode')),
                              (root / '.claude/skills/knowledge-graph', ('claude',))]:
        result.append(Artifact(directory / 'SKILL.md', root, 'skill', skill, owners))
        # Only Codex uses this optional metadata, but it shares the skill folder.
        if 'codex' in owners:
            result.append(Artifact(directory / 'agents/openai.yaml', root, 'skill', metadata, owners))
    return result


def _replace_rule(raw, block, remove=False):
    if raw is None:
        return None if remove else (block + '\n').encode('utf-8')
    bom = raw.startswith(b'\xef\xbb\xbf')
    text = raw.decode('utf-8-sig')
    newline = '\r\n' if '\r\n' in text else '\n'
    starts, ends = text.count(START), text.count(END)
    if (starts, ends) not in ((0, 0), (1, 1)) or (starts and text.index(START) > text.index(END)):
        raise GraphError('AGENT_CONFIG_CONFLICT', 'Malformed or duplicated knowledge-graph instruction markers.')
    if starts:
        before = text[:text.index(START)]
        after = text[text.index(END) + len(END):]
        text = before + ('' if remove else block.replace('\n', newline)) + after
    elif remove:
        return raw
    else:
        separator = '' if not text else (newline if text.endswith(newline) else newline * 2)
        text += separator + block.replace('\n', newline) + newline
    if remove and not text.strip():
        return None
    return (b'\xef\xbb\xbf' if bom else b'') + text.encode('utf-8')


def _plan(artifact, remove):
    _safe(artifact.path, artifact.root)
    before = _read(artifact.path)
    if artifact.kind == 'rule':
        after = _replace_rule(before, artifact.text, remove)
    else:
        # Dedicated generated files are owned as a whole, unlike shared rules.
        marker = SKILL_MARKER if artifact.kind == 'skill' else START
        if before is not None and marker not in before.decode('utf-8-sig'):
            if remove:
                return artifact.path, before, before, 'unmanaged'
            raise GraphError('AGENT_CONFIG_CONFLICT', f'Refusing to overwrite custom agent file: {artifact.path}')
        if artifact.kind == 'cursor_rule' and before is not None:
            # Check markers before replacing even a dedicated rule.
            _replace_rule(before, artifact.text, True)
        after = None if remove else artifact.text.encode('utf-8')
    action = 'unchanged' if after == before else ('removed' if after is None else ('created' if before is None else 'updated'))
    return artifact.path, before, after, action


def _commit(plans):
    applied = []
    try:
        for path, before, after, action in plans:
            if before == after:
                continue
            # Check again to avoid overwriting a customization edited during planning.
            if _read(path) != before:
                raise GraphError('AGENT_CONFIG_CONFLICT', f'Agent file changed during installation: {path}')
            path.parent.mkdir(parents=True, exist_ok=True)
            applied.append((path, before))
            if after is None:
                path.unlink()
            else:
                path.write_bytes(after)
    except (OSError, GraphError):
        for path, before in reversed(applied):
            if before is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(before)
        raise


def manage_agents(operation, *, directory=None, scope='project', target='auto', dry_run=False,
                  home=None, environ=None):
    if operation not in ('install', 'uninstall', 'doctor') or scope not in ('project', 'user'):
        raise GraphError('USAGE_ERROR', 'Unknown agent operation or scope.')
    home = Path(home or Path.home()).expanduser().resolve()
    environ = os.environ if environ is None else environ
    if scope == 'user' and directory is not None:
        raise GraphError('USAGE_ERROR', '--dir applies to project scope only.')
    root = home if scope == 'user' else Path(directory or Path.cwd()).expanduser().resolve()
    if not root.is_dir():
        raise GraphError('AGENT_PROJECT_NOT_FOUND', f'Integration root is not a directory: {root}')
    registry = root / REGISTRY
    _safe(registry, root)
    state = _state(registry)
    selected = _select(target, scope, home, environ, state)
    warnings = []
    if not selected:
        warnings.append('No agents detected. Select --target explicitly to install rules and skills.')
    if scope == 'user' and 'cursor' in selected:
        warnings.append('Cursor user scope installs the skill only. Install project scope for its always-applied rule.')
    artifacts = _artifacts(scope, root, home, environ)
    relevant = [a for a in artifacts if set(a.targets) & set(selected)]
    if operation == 'doctor':
        checks = []
        for a in relevant:
            _safe(a.path, a.root)
            raw = _read(a.path)
            if raw is None:
                status = 'missing'
            else:
                try:
                    _, before, after, _ = _plan(a, False)
                    status = 'installed' if before == after else 'outdated'
                except GraphError:
                    status = 'conflict'
                if a.kind == 'rule' and START not in raw.decode('utf-8-sig'):
                    status = 'missing_managed_block'
            checks.append({'path': str(a.path), 'kind': a.kind, 'targets': sorted(set(a.targets) & set(selected)), 'status': status})
        for a in relevant:
            if a.kind == 'rule' and 'codex' in a.targets:
                override = a.path.with_name('AGENTS.override.md')
                if override.is_file() and override.read_bytes().strip():
                    warnings.append(f'Codex may load {override} instead of {a.path}; integrate the rule into the active override manually.')
        from .database import resolve_database
        try:
            database = str(resolve_database(cwd=Path(directory or Path.cwd())))
        except GraphError:
            database = None
        return {'operation': operation, 'scope': scope, 'root': str(root), 'targets': selected,
                'ready': bool(selected) and all(c['status'] == 'installed' for c in checks) and not warnings,
                'files': checks, 'warnings': warnings, 'database': database,
                'cli': shutil.which('knowledge-graph'), 'version': __version__}
    remaining = set(state['targets']) - set(selected) if operation == 'uninstall' else set(state['targets']) | set(selected)
    plans = []
    for artifact in relevant:
        if operation == 'uninstall' and set(artifact.targets) & remaining:
            # The portable skill or AGENTS block is still needed by another target.
            continue
        plans.append(_plan(artifact, operation == 'uninstall'))
    before = _read(registry)
    after = (json.dumps({'version': 1, 'package_version': __version__, 'targets': sorted(remaining)}, indent=2) + '\n').encode('utf-8') if remaining else None
    action = 'unchanged' if before == after else ('removed' if after is None else ('created' if before is None else 'updated'))
    plans.append((registry, before, after, action))
    if not dry_run:
        _commit(plans)
    return {'operation': operation, 'scope': scope, 'root': str(root), 'targets': selected,
            'dry_run': dry_run, 'files': [{'path': str(p), 'action': action} for p, _, _, action in plans],
            'warnings': warnings, 'restart_required': operation == 'install' and any(b != a for _, b, a, _ in plans)}
