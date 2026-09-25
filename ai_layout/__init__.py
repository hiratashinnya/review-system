"""`.ai/` 直下の**非活性レコード置き場**の共通土台（Issue #522）。

`.ai/` には2種類のものが同居する。

* **loader-facing な規範本文**＝`.ai/skills/<name>/SKILL.md`・`.ai/agents/<name>.md`。
  各 PF の wrapper から参照され、実行時に読まれる。
* **非活性レコード**＝`.ai/rationale`（ADR／設計経緯）・`.ai/troubleshooting`（障害・復旧記録）・
  `.ai/schema`（共有 schema）・`.ai/feedback`（オーナー判断の捕捉台帳）。
  どれも「必要なときだけ参照する記録」であって、loader が自動で読む対象ではない。

本モジュールが持つのは**後者の集合1つだけ**（:data:`NON_ACTIVE_SHARED_DIRS`）である。
`.ai/` 直下に新しい非活性ディレクトリを足したとき、更新すべき場所をここ1箇所に収斂させる
のが目的で、以前は同種の列挙が `asset_parity` と `guidance_sync` に別々の閉じたタプルとして
存在し、追加のたびに二重更新が要った。

**利用側がこの土台に何を足し引きするかは同一ではない**（統合してはならない非対称）:

* :data:`asset_parity.inventory.NON_NORMATIVE_SHARED_DIRS` は述語が
  「**4ツリー parity の seed にならない置き場**」なので、土台に **`.ai/guidance` を足す**
  （常駐 guidance の原稿も parity seed ではないため）。
* :data:`guidance_sync.NON_GUIDANCE_SHARED_DIRS` は述語が
  「**guidance の source にしてはいけない置き場**」なので、土台に **`.ai/guidance` を足さない**
  （`guidance_sync.TARGETS` の値そのものが `.ai/guidance/platforms/*.md` であり、
  含めると自分自身を禁止することになる）。

したがって `.ai/guidance` の扱いは両者で**逆**である。ここに置くのは両者が確実に共有する
最大の集合だけで、`.ai/guidance` は含めない。差分は各利用側が理由付きで足す。

末尾スラッシュは**付けない**。付ける/付けないは利用側の使い方（`Path` 連結か
`str.startswith` か）で決まるので、土台は最も加工しやすい素の形で持つ。

区分: どちらのシステム（doc_system / review_system）にも含有されない汎用開発ハーネス
（`.claude/rules/02-decision-process.md`「起票先はプロジェクト区分で決める」）。

依存仕様（out-of-graph・版なし・補助ナビ）:
  * `.ai/README.md`「非活性文書の境界（Issue #407）」
  * `.ai/schema/asset-placement-v1.json`（配置の機械可読契約）
"""

from __future__ import annotations

NON_ACTIVE_SHARED_DIRS: tuple[str, ...] = (
    ".ai/rationale",
    ".ai/troubleshooting",
    ".ai/schema",
    ".ai/feedback",
)

__all__ = ["NON_ACTIVE_SHARED_DIRS"]
