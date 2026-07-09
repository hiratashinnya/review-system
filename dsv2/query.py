"""meta.json 上のグラフ照会（純関数）: deps / dependents / orphans / drift / prompt_coverage_gaps。

RULE-004（ドリフト）は「辺の ``ref_version``（x.y）≠ 参照先サイドカー ``version`` の x.y」。z は
伝播不問（DD-8）。drift 判定は無条件で発火する（suppress 機構は issue #118 で廃止：依存先ノードが
更新されたら自ノードへの影響確認は必須であり、それを凍結して黙らせる発想自体をオーナー方針で撤去）。
孤立（orphans）は in/out 辺がともに 0 本のノード（RULE-005）。

RULE-032（PROMPT カバレッジ欠落）は config.yml ``prompt_coverage_targets`` が宣言する対象 skill
集合のうち、対応する在グラフ PROMPT ノードが存在しない skill を報告する。

依存仕様: doc-system-v2/config.yml（RULE-004 / always_error / trace_scope / prompt_coverage_targets）・
  FORMAT.md（無名依存辺・親子も edge）・
  doc-system-v2/nodes/02-what/spec/config.yml-が-prompt-ノードカバレッジ対象-skill-集合を宣言する.yaml
  v0.1.0・
  doc-system-v2/nodes/02-what/spec/宣言された対象-skill-集合の-prompt-ノード欠落を機械検査で報告する.yaml
  v0.1.0（RULE-032）。
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .meta import DEFAULT_ROOT, index_by_id


def exact_link_count_gaps(meta: dict, rules: Iterable[dict]) -> list[dict]:
    """接続本数制約（exact count）に違反する node を列挙する。

    ``rules`` は config.yml の ``exact_link_counts`` と同形:
    ``node``（対象型）, ``direction``（incoming|outgoing）, ``peer``（相手型）, ``count``（期待本数）。
    現時点の用途は TD-TC 1:1 の機械表現で、stage activation は呼び出し側が扱う。
    """
    by_id = index_by_id(meta)
    out: list[dict] = []
    for rule in rules:
        node_type = str(rule["node"])
        direction = str(rule["direction"])
        peer_type = str(rule["peer"])
        expected = int(rule["count"])
        for node in meta["nodes"]:
            if node.get("type") != node_type:
                continue
            if direction == "outgoing":
                count = sum(1 for e in node.get("edges", []) if by_id.get(e.get("to"), {}).get("type") == peer_type)
            elif direction == "incoming":
                count = sum(
                    1
                    for src in meta["nodes"]
                    if src.get("type") == peer_type
                    for e in src.get("edges", [])
                    if e.get("to") == node.get("id")
                )
            else:
                raise ValueError(f"未知 direction: {direction!r}")
            if count != expected:
                out.append({
                    "id": node["id"],
                    "type": node_type,
                    "direction": direction,
                    "peer": peer_type,
                    "expected": expected,
                    "actual": count,
                    "reason": rule.get("reason", ""),
                })
    return out


def load_prompt_coverage_targets(root: str | Path = DEFAULT_ROOT) -> tuple[str, ...]:
    """``config.yml`` が宣言する PROMPT カバレッジ対象 skill 集合を読む（RULE-032）。"""
    config_path = Path(root) / "config.yml"
    if not config_path.is_file():
        raise ValueError(f"{config_path}: config.yml が見つかりません")
    targets: list[str] | None = None
    in_targets = False
    for raw in config_path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if stripped == "prompt_coverage_targets:":
            targets = []
            in_targets = True
            continue
        if in_targets and indent == 0:
            break
        if in_targets:
            if not stripped.startswith("- "):
                raise ValueError(f"{config_path}: prompt_coverage_targets はブロックリスト形式である必要があります")
            item = stripped[2:].split("#", 1)[0].strip().strip('"').strip("'")
            if not item:
                raise ValueError(f"{config_path}: prompt_coverage_targets に空要素があります")
            targets.append(item)
    if targets is None:
        raise ValueError(f"{config_path}: prompt_coverage_targets が見つかりません")
    if not targets:
        raise ValueError(f"{config_path}: prompt_coverage_targets は空にできません")
    return tuple(targets)


def _xy(version: str) -> str:
    """``x.y.z``（または ``x.y``）から比較単位 ``x.y`` を返す。"""
    parts = version.split(".")
    return ".".join(parts[:2]) if len(parts) >= 2 else version


def _drift(ref_version: str, target: dict | None) -> bool | None:
    """辺 ref_version（x.y）が参照先バッジ x.y と不一致なら True。判定不能なら None。"""
    if not ref_version or target is None or not target.get("version"):
        return None
    return _xy(ref_version) != _xy(target["version"])


def deps(meta: dict, node_id: str) -> list[dict] | None:
    """node の出辺（依存先）＋存在/ドリフト情報。node が無ければ None。"""
    by_id = index_by_id(meta)
    node = by_id.get(node_id)
    if node is None:
        return None
    rows: list[dict] = []
    for e in node["edges"]:
        target = by_id.get(e["to"])
        ref = e.get("ref_version", "")
        rows.append({
            "to": e["to"],
            "ref_version": ref,
            "exists": target is not None,
            "target_version": target["version"] if target else None,
            "drift": _drift(ref, target),
            "note": e.get("note", ""),
        })
    return rows


def dependents(meta: dict, node_id: str) -> list[dict]:
    """node への入辺（依存元）一覧を全ノード走査で逆引きする。"""
    rows: list[dict] = []
    by_id = index_by_id(meta)
    node = by_id.get(node_id)
    for src in meta["nodes"]:
        for e in src["edges"]:
            if e["to"] != node_id:
                continue
            ref = e.get("ref_version", "")
            rows.append({
                "from": src["id"],
                "type": src["type"],
                "ref_version": ref,
                "drift": _drift(ref, node),
                "yaml_path": src["yaml_path"],
            })
    return rows


def orphans(meta: dict) -> list[dict]:
    """in/out 辺がともに 0 本の完全孤立ノード（RULE-005 相当）。"""
    referenced: set[str] = set()
    for n in meta["nodes"]:
        for e in n["edges"]:
            referenced.add(e["to"])
    return [n for n in meta["nodes"] if not n["edges"] and n["id"] not in referenced]


def slug_collisions(
    meta: dict,
    slugs: list[str],
    update_slugs: set[str] | None = None,
) -> dict[str, str]:
    """著作 slug 群がコーパス既存 id と衝突するか／slug 群内で重複するかを返す（fail-close 用）。

    id = slug = ファイル名 stem はグローバル一意（FORMAT.md §slug）。この一意性は slugify.py でも
    validate.py（per-node）でも担保できない＝コーパス横断の照合が必要。reconciliation-validator が
    書込前に本関数（dsv2 check-slug 経由）で fail-close 判定する（DD-22・Sub-D・issue #73）。

    ``update_slugs`` は「意図的に既存ノードを更新する」として**宣言された** slug 群（issue #97・案A）。
    宣言された slug はコーパス衝突 fail-close から除外する（既存ノード更新では slug が既にコーパスに
    在るのは正常＝#92 の TERM 追記等）。ただし**バッチ内重複**（slug 群内での重複）は宣言有無に関わらず
    fail-close を維持する（同一 slug の二重著作＝タイトル衝突なので）。

    戻り値: ``{slug: reason}``（衝突分のみ）。reason は
      * ``"corpus:<yaml_path>"`` … 既存コーパスノードと id 衝突（**非宣言 slug のみ**）。
      * ``"batch(xN)"``          … 今回の著作 slug 群内で N 回重複（宣言有無に関わらず）。
    衝突が無ければ空 dict（＝一意で書込可）。

    依存仕様: doc-system-v2/FORMAT.md（§slug グローバル一意）・config.yml（id=stem）・issue #97（案A）。
    """
    by_id = index_by_id(meta)
    declared = update_slugs or set()
    counts: dict[str, int] = {}
    for s in slugs:
        counts[s] = counts.get(s, 0) + 1
    out: dict[str, str] = {}
    for s, n in counts.items():
        if s in by_id and s not in declared:
            out[s] = f"corpus:{by_id[s]['yaml_path']}"
        elif n > 1:
            out[s] = f"batch(x{n})"
    return out


def update_slugs_not_in_corpus(meta: dict, update_slugs: set[str]) -> list[str]:
    """``--update`` 宣言 slug のうちコーパスに実在しないものを返す（typo ハードニング用・情報提示のみ）。

    ``--update <slug>`` は「既存ノードを更新する」宣言だが、対象がコーパスに無ければ衝突免除は
    silent no-op になる（宣言 slug がそもそも corpus 衝突しないので除外の実効が無い＝実害はないが、
    タイプミスの可能性が高い）。fail-close には影響させず、呼び出し側（cli）が WARN を出すための
    情報だけを返す（issue #103 Part B）。

    依存仕様: issue #97（案A・``--update`` 契約）・issue #103（typo ハードニング follow-up）。
    """
    by_id = index_by_id(meta)
    return sorted(s for s in update_slugs if s not in by_id)


def prompt_coverage_gaps(
    meta: dict,
    targets: Iterable[str] | None = None,
    root: str | Path = DEFAULT_ROOT,
) -> list[str]:
    """対象 skill 集合のうち、対応する PROMPT ノードが在グラフに存在しない skill を列挙（RULE-032）。

    対応判定は「``type == 'prompt'`` かつ ``carrier`` が ``skill`` または ``agent`` なノードの
    ``id``（slug）が ``'{skill}-'`` で始まる」（design-author の既存命名慣行・PROMPT-8〜20
    で確認済み）。DD-22 の ①-C ハイブリッドに従って対象 skill の PROMPT ノードが
    ``carrier: skill`` から ``carrier: agent`` へ変わっても、RULE-032 は欠落として誤検知しない。
    carrier を持たない著作エージェント PROMPT（PROMPT-1〜7）は対象から除外される。
    戻り値は ``targets`` の宣言順を保つ（欠落 0 件なら空リスト）。
    """
    declared_targets = tuple(targets) if targets is not None else load_prompt_coverage_targets(root)
    covered: set[str] = set()
    for n in meta["nodes"]:
        if n.get("type") != "prompt" or n.get("carrier") not in {"skill", "agent"}:
            continue
        node_id = n.get("id", "")
        for skill in declared_targets:
            if node_id.startswith(f"{skill}-"):
                covered.add(skill)
    return [s for s in declared_targets if s not in covered]


def drift(meta: dict) -> list[dict]:
    """全辺を走査し、ref_version が参照先バッジ x.y とドリフトしている辺を列挙（RULE-004）。"""
    by_id = index_by_id(meta)
    out: list[dict] = []
    for src in meta["nodes"]:
        for e in src["edges"]:
            ref = e.get("ref_version", "")
            target = by_id.get(e["to"])
            if _drift(ref, target) is True:
                out.append({
                    "from": src["id"],
                    "to": e["to"],
                    "ref_version": ref,
                    "target_version": target["version"],
                })
    return out
