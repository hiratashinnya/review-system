# 主文脈専用の規範と毎ターン注入の経緯（非活性・どのフックも注入しない）

注入されるコンテキスト（`.claude/main-context/*.md` の本文と `.claude/hooks/governance-directives.md` の
注入本文＝項1〜12）には経緯・出典（Issue 番号・日付・「〜で導入」等）を載せない。
本ファイルはそこから外した経緯・出典の置き場である（`.claude/rules/01-principles.md`
「PR8「消さない」の適用範囲」区分1＝経緯は消さず移設）。規範の意味は移設元で変えていない。

## `.claude/main-context/01-owner-communication.md` の出典

- 節「オーナーへの報告はチャットが正本（副次記録との分離）」：2026-08-20・Issue #379 で
  `.claude/rules/02-decision-process.md` に新設。中核規範12（写し）もこのとき追加。
- 項「報告のタイミングは「実行前」」：Issue #484（2026-09-06・セッション記憶にしか無かった作業規則を
  正本へ移設した棚卸し）で追加。
- 項「質問・承認依頼は `AskUserQuestion` ツールで行う（Claude Code 固有）」：Issue #585（2026-10-08）で
  新設。非対話ロールが `AskUserQuestion` を持たない根拠は DD-22（3ロールとも非対話＝曖昧は STOP 報告・
  対話判断は `/issue-pipeline` 主文脈が担う）。
- 節全体の移設：Issue #585（2026-10-08）で `.claude/rules/02-decision-process.md` から
  `.claude/main-context/01-owner-communication.md` へ移した。rules は `@` import の有無に関わらず
  サブエージェントにも配送されるため、主文脈にしか当てはまらない規範を rules に置けない。

## `governance-directives.md` 注入本文から外した出典

- 項3「「スコープ外」も処置不要の言い換えにしない」：Issue #495（2026-09-07）。
  「機械が強制するのは許可者と理由の記録まで」の一文は Issue #495 是正ラウンド1（PR #496 F-495-04）。
- 項11「PR8「消さない」の適用範囲は区分で決める」：Issue #357（2026-08-18）。参照先の節見出しは
  `.claude/rules/01-principles.md`「PR8「消さない」の適用範囲（2026-08-18・Issue #357）」。
- 項12「オーナーへの報告・質問の仕方（主文脈専用）」：Issue #379 で追加、Issue #484 でタイミング要素を
  追記、Issue #585 で正本を main-context へ移して要約の写しに改めた（下記）。

## 主文脈専用の規範の配送方式（Issue #585・オーナー決定 2026-10-09）

- PR #586 round 1 の当初案（案 a）は、`inject-governance.sh`（UserPromptSubmit）が
  `.claude/main-context/*.md` の全文を写しの後ろへ毎ターン連結する方式で、「写しを作らないので追従検査が
  要らない」ことを利点としていた。レビュー（F-585-07）で、毎ターン約1.5k字の全文が積み上がり旧項12
  （約0.4k字）よりトークン消費と圧縮頻度が増えることが指摘された。
- オーナー決定（案 b）：毎ターンは写しの項12に簡潔な要約だけを置き、全文は既存の
  `orchestrator-context.sh`（SessionStart の startup/clear/compact）が委譲ルールに続けて注入する。
  新しいフックや `settings.json` の変更はしない。要約は写しになるので、`.claude/main-context/*.md` を
  追従検知の正本集合（`check-governance-drift.sh` と `tests/unit/test_governance_sync.py`）へ加えた。
- 読込失敗の扱い（F-585-02）：当初案の読込ループは `OSError` しか捕捉せず、UTF-8 として不正な
  ファイルが1つあると `UnicodeDecodeError` で注入全体が落ちた。main-context を読む
  `orchestrator-context.sh` で `UnicodeDecodeError` も捕捉して当該ファイルだけを飛ばし、
  `tests/unit/test_main_context_injection.py` で固定した。
- 出典の移設（F-585-08）：レビューで AskUserQuestion の項にだけ出典が無いと指摘され、オーナー決定により
  出典を足すのではなく、注入されるコンテキストから経緯・出典を外して本ファイルへ移した。

## 本ファイルの置き場（F-585-11・オーナー決定 2026-10-09）

- 当初は `.claude/rationale/main-context-injection.md` に実体を置いたが、非活性レコード（rationale）の
  正本置き場は `.ai/rationale/` で、配置契約（`.ai/schema/asset-placement-v1.json`）も rationale の path を
  `.ai/rationale/` 直下に限定している。既存の `.claude/rationale/*.md` は `.ai/rationale/` への1行の案内である。
  そのため実体を本ファイルへ移し、`.claude/rationale/main-context-injection.md` を同じ形の案内にした。
