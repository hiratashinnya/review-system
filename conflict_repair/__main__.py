"""default branch の更新または手動指定から単独 PR を評価する。"""
import json
import os
from pathlib import Path

from .github import GitHub
from .runner import evaluate


def main():
    repository = os.environ['GITHUB_REPOSITORY']
    api = GitHub(repository)
    default = api.default_branch()
    if os.environ['GITHUB_REF'] != f'refs/heads/{default}':
        raise RuntimeError('default branch の workflow のみ実行可能')
    requested = os.environ.get('INPUT_PR_NUMBER', '').strip()
    pulls = api.pulls()
    numbers = [int(requested)] if requested else [pr['number'] for pr in pulls]
    results = []
    for number in numbers:
        try:
            results.append(evaluate(api, Path(os.environ['GITHUB_WORKSPACE']), number,
                                    repository, default))
        except Exception as exc:
            results.append({'pr': number, '判定': f'失敗: {exc}', 'push': False,
                            'CI': '未検証'})
    report = '\n'.join(f'- {json.dumps(row, ensure_ascii=False)}' for row in results)
    print(report)
    with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as output:
        output.write('## 自動競合修復\n\n' + report + '\n')


if __name__ == '__main__':
    main()
