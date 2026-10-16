# #371 実装と実測の境界

Codex（AI）、2026-10-16。

profileは `origin/main:.codex/config.toml` との完全一致を維持する。
新profileを含む未merge PRではCODEX_EXEC_PROFILE_DRIFTによる拒否が正しい。
unit検証、拒否検証、artifact検証は製品の実dispatch成功を代替しない。

merge後一回の検証案は主文脈が準備した [起票本文案](../designs/post-merge-verification-371.md)。
低/中/高経路、各実行先の許可と拒否、低tierから上位adviserへの要求・返却・検証、
失敗/部分出力/予算到達、権限越境拒否、モデル実使用と費用を確認する。
現在は外部Issue未起票であり、実測AC完了・#371 close可能とは報告しない。

同一worktreeのadoptは現行の使用中branch拒否と衝突するためownerへ比較案を提示中。
Aは各roleのisolated worktreeへ同一branchのremote exact OIDを継承する方式、
Bは安全な同一worktree所有権移管を新設する方式。Aを推奨するがowner決定前に有効化しない。

agyは#606/#628の成立とロール別実測まで無効。
#375のcapture原本性本体、#310のkarte配線、#409のAgentRun、#543のreview_system側レベル導入、
#578の既存TC移設は本Issueで再実装しない。
#632の起票専用subagentは現mainに存在するため、owner起票判断は主文脈、実行は既存専用経路を使う。

ProjectのIn progress更新はGitHub側のResource not accessible by integrationで未完了。
コード/PRの権限をProject書込権限の成功に読み替えない。
