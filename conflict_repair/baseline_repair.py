"""baseline 競合を既存値から解き、統合ソースとの一致を検査する。"""
import json

from maintainability_lint.scanner import build_baseline, scan

from . import git
from .baseline_evidence import describe
from .baseline_merge import merge_baselines
from .baseline_schema import SECTIONS, parse_baseline
from .repair import regular_path

PATH = 'maintainability_lint/baseline.json'


def resolve(repo, base, head, result):
    conflicted = PATH in git.conflicts(repo)
    changed = git.run(repo, 'diff', '--name-only', base, head, '--', PATH).stdout
    if not conflicted and not changed:
        return None
    if conflicted and git.run(repo, 'rev-parse', '--verify', 'MERGE_HEAD').stdout.strip() != base:
        raise ValueError('baseline 修復時の merge 状態が不正')
    ancestors = git.run(repo, 'merge-base', '--all', base, head).stdout.splitlines()
    if len(ancestors) != 1:
        raise ValueError('baseline merge-base が一意ではありません')
    ancestor = ancestors[0]
    versions = [git.run(repo, 'show', f'{oid}:{PATH}').stdout
                for oid in (ancestor, base, head)]
    result['baseline 3版の証跡'] = describe(versions)
    merged = merge_baselines(*versions)
    result['baseline 3版の証跡']['状態'] = '統合済み'
    regular_path(repo, PATH)
    if conflicted:
        (repo / PATH).write_text(json.dumps(merged, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        git.run(repo, 'add', '--', PATH)
    elif parse_baseline((repo / PATH).read_bytes()) != merged:
        raise ValueError('Git の baseline 統合結果が意味的統合と不一致')
    before = parse_baseline(versions[2])
    changes = {}
    for section in SECTIONS:
        old, new = before[section], merged[section]
        changes[section] = {'追加': sorted(new.keys() - old.keys()),
                            '削除': sorted(old.keys() - new.keys()),
                            '更新': sorted(k for k in new.keys() & old.keys() if new[k] != old[k])}
    return {'merge-base OID': [ancestor], 'baseline 変更キー': changes, 'merged': merged, 'conflicted': conflicted}


def read_worktree(repo):
    regular_path(repo, PATH)
    return parse_baseline((repo / PATH).read_bytes())


def verify(repo, merged):
    actual = build_baseline(repo)
    if any(actual[section] != merged[section] for section in SECTIONS):
        raise ValueError('baseline と統合ソースの違反集合が不一致')
    if any(finding.status == 'violation' for finding in scan(repo, merged).findings):
        raise ValueError('統合ソースの maintainability lint に失敗')
    staged = git.run(repo, 'show', f':{PATH}').stdout
    working = (repo / PATH).read_text(encoding='utf-8')
    if staged != working:
        raise ValueError('stage 後の baseline が作業ファイルと不一致')
