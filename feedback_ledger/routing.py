"""改訂案の ``routing`` と「起票先の判定表」を突き合わせる（P4 の一部）。

判定表の正本は `.claude/rules/02-decision-process.md`「起票先はプロジェクト区分で決める
（ハーネス開発は Issue 運用）」で、判定軸は「そのハーネスが doc_system / review_system に
**含有されるか**」である。含有されるもの＝FND/Q/DD ノード起票（``routing = "node"``）、
どちらにも含有されない汎用開発ハーネス＝Issue 運用（``routing = "issue"``）。

ここに置くのは**その表の機械可読な写し**であって表そのものではない。判定表が変わったら
本モジュールも同じ PR で直す（写しが古くなると、改訂案の routing を誤って通す）。

**列挙されていないものは ``issue`` 側に落ちる**。理由は判定表の構造どおりで、
「含有される」側が有限の列挙（著作・検証エージェント／仕様策定スキル14件／コーパス操作ツール
``dsv2``／``review_system`` 本体と ``tests/``／両システムの正本ディレクトリ）であり、
それ以外は定義上「どちらの成果物でもない」ため。

依存仕様: `.claude/rules/02-decision-process.md`「起票先はプロジェクト区分で決める」。
"""

from __future__ import annotations

NODE = "node"
ISSUE = "issue"

# 両システムの成果物そのもの（ディレクトリ前方一致）。
NODE_ROUTED_PREFIXES: tuple[str, ...] = (
    "doc-system-v2/",   # doc_system のノードグラフ（正本）
    "docs/",            # review_system の正本＋ docs/doc-system/（doc_system の機械定義）
    "review_system/",   # review_system 本体の実装
    "tests/",           # 両システムのテスト
    "dsv2/",            # コーパスを操作するツール（doc_system に含有される）
)

# 仕様策定・実装設計スキル14件（`doc-system-v2/config.yml` の prompt_coverage_targets）。
NODE_ROUTED_SKILLS: frozenset[str] = frozenset({
    "align", "value-trace", "mvp-scope", "schema-design", "domain-model",
    "architecture-design", "orchestration-design", "prompt-design",
    "test-strategy", "spec-principles", "spec-pipeline", "impl-design-pipeline",
    "asset-pipeline", "docidx",
})

# 著作・検証エージェント（両システムの生産機構）。
NODE_ROUTED_AGENTS: frozenset[str] = frozenset({
    "requirements-author", "spec-author", "analysis-author", "design-author",
    "verification-author", "reconciliation", "reconciliation-validator",
    "spec-inspector", "structured-analysis", "dsv2-lookup", "authoring-fanout",
    "doc-system-v2-authoring",
})

_ASSET_ROOTS = (".ai/", ".claude/", ".github/", ".agents/", ".codex/")


def route_for(path: str) -> str:
    """1つの資産パスの起票先（``node`` / ``issue``）を判定する。"""
    normalized = path.strip().lstrip("./") if path.startswith("./") else path.strip()
    for prefix in NODE_ROUTED_PREFIXES:
        if normalized.startswith(prefix):
            return NODE
    for root in _ASSET_ROOTS:
        if not normalized.startswith(root):
            continue
        rest = normalized[len(root):]
        if rest.startswith("skills/"):
            name = rest[len("skills/"):].split("/", 1)[0]
            return NODE if name in NODE_ROUTED_SKILLS else ISSUE
        if rest.startswith("agents/"):
            name = rest[len("agents/"):].split("/", 1)[0]
            for suffix in (".md", ".toml", ".agent.md"):
                if name.endswith(suffix):
                    name = name[: -len(suffix)]
                    break
            return NODE if name in NODE_ROUTED_AGENTS else ISSUE
    return ISSUE


def expected_routing(paths) -> tuple[str | None, list[str], list[str]]:
    """対象資産すべての起票先を判定する。

    戻り値は ``(expected, node_paths, issue_paths)``。両区分が混ざっている場合は
    ``expected`` を ``None`` にして呼び出し側に「改訂案を分割せよ」と言わせる
    （1つの改訂案が2つの起票先を持つことはない＝PR1「もの＋発生源で分ける」）。
    """
    node_paths = [path for path in paths if route_for(path) == NODE]
    issue_paths = [path for path in paths if route_for(path) == ISSUE]
    if node_paths and issue_paths:
        return None, node_paths, issue_paths
    if node_paths:
        return NODE, node_paths, issue_paths
    if issue_paths:
        return ISSUE, node_paths, issue_paths
    return None, node_paths, issue_paths
