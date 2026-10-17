# #371 実装と実測の境界

Codex（AI）、2026-10-16。

profileは `origin/main:.codex/config.toml` との完全一致を維持する。
新profileを含む未merge PRではCODEX_EXEC_PROFILE_DRIFTによる拒否が正しい。
unit検証、拒否検証、artifact検証は製品の実dispatch成功を代替しない。

merge後一回の検証は [Issue #652](https://github.com/hiratashinnya/review-system/issues/652) で追跡する。
native parentは #368 であり、対象版・開始条件・AC・証拠の契約は [検証計画](../designs/post-merge-verification-371.md) に保存する。
低/中/高経路、各実行先の許可と拒否、低tierから上位adviserへの要求・返却・検証、
失敗/部分出力/予算到達、権限越境拒否、モデル実使用と費用を確認する。
起票とrelationは作成後に取得して確認済みである。製品経路の実dispatchは未実測であり、実測AC完了とは報告しない。

ownerは各roleのisolated worktreeへ同一branchのremote exact OIDを継承する方式を選択した。
使用中branchの拒否を維持し、同一worktreeの所有権移管は新設しない。
判断原本は `.ai/feedback/ledger/FBK-20261017-工程別worktreeへ同一branchを継承する.toml`。

agyは#606/#628の成立とロール別実測まで無効。
#375のcapture原本性本体、#310のkarte配線、#409のAgentRun、#543のreview_system側レベル導入、
#578の既存TC移設は本Issueで再実装しない。
#632の起票専用subagentは現mainに存在するため、owner起票判断は主文脈、実行は既存専用経路を使う。

ProjectのIn progress更新はGitHub側のResource not accessible by integrationで未完了。
コード/PRの権限をProject書込権限の成功に読み替えない。

## 判断と起票の履歴

2026-10-16時点では外部verification Issueは未起票で、同一worktree/adopt衝突について
A（role別worktreeへremote exact OIDを継承）とB（同一worktree所有権移管）を比較しowner判断を待っていた。
2026-10-17にownerがAと検証Issueの起票・relationを認可し、#652およびparent #368の接続を確認した。
起票前の本文案やfixture到達はlive成功の証拠に扱わない。
