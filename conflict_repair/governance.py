"""人手管理の governance 写しの同期状態を観測する。"""
import hashlib
import re

from .repair import regular_path


def governance_status(repo):
    copy = '.claude/hooks/governance-directives.md'
    try:
        paths = (['CLAUDE.md'] + sorted(str(p.relative_to(repo)) for p in (repo / '.claude/rules').glob('*.md'))
                 + ['.ai/guidance/common.md']
                 + sorted(str(p.relative_to(repo)) for p in (repo / '.claude/main-context').glob('*.md')))
        digest = hashlib.sha256()
        for path in paths:
            regular_path(repo, path)
            digest.update(path.encode() + b'\0' + (repo / path).read_bytes() + b'\0')
        regular_path(repo, copy)
        text = (repo / copy).read_text(encoding='utf-8')
        marker = re.search(r'<!--\s*synced-from:\s*CLAUDE\.md@([0-9a-f]{12})\s*-->', text)
        if marker is None:
            return '不一致: marker なし'
        expected = digest.hexdigest()[:12]
        return '一致' if marker.group(1) == expected else f'不一致: {marker.group(1)} != {expected}'
    except (OSError, UnicodeError, ValueError) as exc:
        return f'判定不能: {exc}'
