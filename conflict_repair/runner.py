"""各 PR を評価し、修復結果を live 状態と再照合する。"""
import tempfile
from pathlib import Path

from . import git
from .baseline_repair import read_worktree, resolve, verify
from .baseline_schema import SECTIONS
from .eligibility import classify
from .governance import governance_status
from .repair import regenerate


def evaluate(api, source, number, repository, default):
    target, reason, related = classify(api.pulls(), number, repository, default)
    result = {'pr': number, '判定': reason, '単独/stacked 判定': reason, '関連 PR': related, 'push': False,
              'CI': '未検証'}
    try:
        if target is None:
            return result
        _, _, _, base, _, head, head_oid = target
        if api.default_branch() != default:
            result['判定'] = 'default branch が変更'
            return result
        base_oid = api.branch_oid(base)
        result.update({'base OID': base_oid, 'head OID': head_oid})
        if api.branch_oid(head) != head_oid:
            result['判定'] = 'head OID 不一致'
            return result
        with tempfile.TemporaryDirectory(prefix='conflict-repair-') as temp:
            repo = Path(temp) / 'work'
            merge = git.prepare(source, repo, base_oid, head_oid)
            result['governance 同期'] = governance_status(repo)
            result['merge-base OID'] = git.run(repo, 'merge-base', '--all', base_oid, head_oid, check=False).stdout.splitlines()
            if merge.returncode not in (0, 1):
                raise ValueError('git merge に失敗')
            baseline = resolve(repo, base_oid, head_oid, result)
            repaired_baseline = bool(baseline and baseline.pop('conflicted'))
            merged = baseline.pop('merged') if baseline else None
            if baseline:
                result.update(baseline)
            else:
                result['baseline 変更キー'] = {section: {'追加': [], '更新': [], '削除': []}
                                           for section in SECTIONS}
            guidance = regenerate(repo, merge, resolved=True) if repaired_baseline else regenerate(repo, merge)
            if guidance or repaired_baseline:
                verify(repo, merged if merged is not None else read_worktree(repo))
            if not guidance and not repaired_baseline:
                result['判定'] = '生成物は整合、修復不要'
                return result
            new_oid = git.commit(repo)
            current, reason, related = classify(api.pulls(), number, repository, default)
            if (current != target or api.default_branch() != default
                    or api.branch_oid(base) != base_oid or api.branch_oid(head) != head_oid):
                result.update({'判定': f'push 前に状態が変化: {reason}', '関連 PR': related})
                return result
            git.push(source, repo, head, head_oid)
            result.update({'判定': '修復完了', 'push': True, '修復後 OID': new_oid})
            try:
                api.dispatch('conflict-repair-verify.yml', default, new_oid, number)
                result['検証 dispatch'] = '要求済み（結果・required checks 未確認）'
            except Exception as exc:
                result['検証 dispatch'] = f'失敗: {exc}'
        return result
    except Exception as exc:
        result['判定'] = f'失敗: {exc}'
        exc.repair_result = result
        raise
