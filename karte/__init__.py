"""karte — 是正ループの診断カルテ CLI（Issue #307）。

背景:
  ``/issue-pipeline`` の ②-c「是正 → 再レビュー」が収束せず長引く原因は運用の緩みではなく
  **設計上ループ状態を持っていないこと**にある。是正ラウンドは毎回新しい subagent
  コンテキストで走るため、前ラウンドの診断・試行・失敗は主文脈のチャットと PR コメントに
  しか残らず、次のラウンドが同じアプローチを再発明する。

方針:
  ループ状態の実体＝**診断カルテ**（``tmp/_karte/issue-{N}.md``）をファイルとして持ち、
  「どの指摘（finding ID）に対して・どう診断し（root_cause）・どこを触り（targets）・
  結果どうなったか（Result）」を ID で結合する。そのうえで **同じアプローチの無駄連打だけ**を
  機械判定で止める（``append`` が3件目の類似 Attempt の書き込み自体を拒否する）。
  **ラウンド上限は設けない**ので、毎回違う角度で攻めている限り作業は妨げられない。

呼ばれないと進まないように作る（Issue #315・K-02/K-13/K-14/K-15）:
  「呼び忘れ」でゲートが無効化できる余地を残さない。``check`` は**カルテ上の全 Attempt** が
  クローズ済み（実測 touched-set が供給済み）でなければ落ちるので、``close-attempt`` を
  飛ばすと是正エージェントが停止できない（先のラウンドを名乗った Attempt も逃げ道に
  ならない）。``ingest-review`` は ``--from -`` で stdin を読め、``render`` / ``check`` /
  ``status`` は ``--issue``（``check`` は ``--round`` も）を進行ポインタから補完できるので、
  フック（SubagentStop / SubagentStart / PostToolUse）が人手の中継なしに直接呼べる。
  ``status`` は PostToolUse フックが ``pr-reviewer`` 呼び出し完了直後に実行して
  エスカレーション判定をコンテキストへ注入する（K-15。ただし PostToolUse はツール呼び出しを
  ブロックできないため、役割は「判定を必ず実行し可視化する」まで）。

構成:
  * :mod:`karte.paths`      — カルテ置き場のパス解決とガード（実体解決・repo-root 配下・
    symlink 拒否・``..`` traversal 拒否・fail-close）。様式は ``dsv2/cleantmp.py`` に倣う。
  * :mod:`karte.model`      — カルテ書式（``## Findings`` / ``### Attempt k`` / ``### Result k``）の
    データモデル・パーサ・シリアライザ・バリデータ。
  * :mod:`karte.similarity` — 類似判定（宣言信号＋実測 touched-set 信号の OR）と転換指令の生成。
    ``append`` のゲートと ``render``/``status`` の表示は**同じ判定関数を同じ入力集合**
    （候補の finding_ids でスコープした priors）に適用する（K-09）。
  * :mod:`karte.cli`        — 6 verb（``ingest-review`` / ``render`` / ``append`` /
    ``close-attempt`` / ``check`` / ``status``）。

標準ライブラリのみ（外部依存なし）。

スコープ外指摘を別経路にしない（Issue #495）:
  「スコープ外」と分類された指摘が finding の列に入らないと、実害判定（``harm``）・カルテ記録・
  ``status`` の verdict をまとめて迂回でき、実害ありの指摘が未処置のまま ``clean`` を通過する
  （PR #490 で実際に起き、Issue #493 が merge 後に流出した）。``## Findings`` を
  **スコープの内外を問わない単一の列**とし、``scope``（``in``/``out``・必須・免除力なし）と
  ``disposition``（``fix-here``/``deferred``/``waived``＝オーナー判断の記録）を持たせ、
  **``harm: real`` かつ ``disposition`` 未決定の finding が残る間は verdict を ``clean`` に
  しない**。``deferred``/``waived`` は ``status: open`` のまま verdict の上でだけ clean を
  妨げなくする二層（``resolved`` に倒すと「別 Issue へ移したと書くだけで指摘が消える」
  経路が生まれる）。書式と移行措置の詳細は ``karte/README.md``。

依存仕様:
  * Issue #307「是正ループの診断カルテ CLI を追加し『類似アプローチの反復』を機械判定する」
    （提案挙動・受入基準の一次アンカー）。
  * Issue #315「karte レビュー残指摘の全件処置」（K-02/K-04〜K-07/K-09/K-11〜K-15）。
  * Issue #495「レビューのスコープ外指摘が実害判定とカルテを迂回でき、実害ありの指摘が
    未処置のまま merge される」（提案挙動 1〜6・受入基準）。
  * ``dsv2/cleantmp.py`` docstring（パスガードの様式・削除直前の再検査の考え方）。
    ※ ``karte.paths`` 側の再検査は best-effort であり原子的ではない（K-04・Issue #318 で厳密化）。
  * CLAUDE.md「戻り値のハンドオフ規約」（``tmp/_handoff/`` はハンドオフ＝1回の戻り値。
    カルテはループ状態なので **別ディレクトリ** ``tmp/_karte/`` に置く）。
    ※ CLAUDE.md は out-of-graph（版なし）のため補助ナビ。
"""

from .cli import main
from .model import Karte, KarteFormatError
from .paths import KartePathError

__all__ = ["Karte", "KarteFormatError", "KartePathError", "main"]
