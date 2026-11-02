"""live PR 一覧から単独性を保守的に判定する。"""


def identity(pr):
    base, head = pr['base'], pr['head']
    return (pr['number'], pr['state'], base['repo']['full_name'], base['ref'],
            base['sha'], head['repo']['full_name'], head['ref'], head['sha'])


def classify(pulls, number, repository, default):
    try:
        rows = [identity(pr) for pr in pulls]
        if any(row[1] != 'open' or not all(row) for row in rows):
            return None, 'PR 情報が不完全', []
        matches = [row for row in rows if row[0] == number]
        if len(matches) != 1:
            return None, '対象 PR が存在しないか重複', []
        target = matches[0]
        _, _, base_repo, base_ref, _, head_repo, head_ref, _ = target
        children = [row[0] for row in rows if row[0] != number
                    and row[2] == repository and row[3] == head_ref]
        same_head = [row[0] for row in rows if row[0] != number
                     and row[5] == head_repo and row[6] == head_ref]
        parents = [row[0] for row in rows if row[0] != number
                   and row[5] == repository and row[6] == base_ref]
        related = sorted(set(children + same_head + parents))
        if base_repo != repository or head_repo != repository:
            return None, 'fork または別 repository', related
        if base_ref != default or children:
            return None, 'stacked PR', related
        if same_head or head_ref == default or head_ref == base_ref:
            return None, 'head branch が曖昧', related
        return target, '単独 PR', related
    except (KeyError, TypeError, ValueError):
        return None, 'PR 情報が不完全', []
