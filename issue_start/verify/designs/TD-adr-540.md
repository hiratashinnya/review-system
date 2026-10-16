---
id: TD-adr-540
version: 1
condition: normal
---
# 目的

道具別ADRのスキーマ、追跡状態、永続化、参照、通知、棚卸し、Issue起票を検証する。

# 前提

標準ライブラリ、git、GitHub境界のfake runner。一時repoと2つのADR rootを使用。TCは tests/unit/test_adr.py。

# 手順と期待結果

1. alternatives欠落、status欠落、filed番号欠落、not_needed理由欠落は拒否、pendingは保存可能。
2. 複数rootのroundtrip、既存上書き・互換ID衝突・symlinkは拒否。
3. new-entry直後とPostToolUseでsystemMessage、todoでpending全件、file-issue下書きとfake起票で番号書戻し。
4. refs実在/canonical/immutability検査、pending→filedのみ更新可、supersedes導出view。
5. fake GitHubでOPENかつ閾値超過のfiledのみstaleへ列挙。
6. ADR/台帳/任意参照欄のChangePlan・VerificationDesignを同adapterで変換し、dsv2 queryでdeps/dependents/orphansを検証。永続envelopeも入力可能。
7. 全unit、asset_parity、maintainability_lintが成功し、baseline差分がない。

# #452証跡

着手時のAC対象元は0件。99d89553（#538）でarchiveへ退役済み。詳細は adr/rationale.md。
