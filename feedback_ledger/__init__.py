"""オーナー判断フィードバック台帳（`.ai/feedback/`）の CLI 専用書込みと機械 lint（Issue #522）。

オーナーが AI の推奨を曲げた判断を、**改ざん検知可能な形**で版管理下に蓄積するための土台。
3つの文書型（台帳エントリ／改訂案／週次棚卸し記録）を TOML で持ち、書込み経路を
``python3 -m feedback_ledger`` の1本に絞る。

区分: どちらのシステム（doc_system / review_system）にも含有されない汎用開発ハーネス
（`.claude/rules/02-decision-process.md`「起票先はプロジェクト区分で決める」）。

モジュール構成:
  ``schema``     3種のスキーマ宣言（キー集合・並び・型・語彙の正本）
  ``tomlwrite``  canonical TOML の最小シリアライザ（読みは標準 :mod:`tomllib`）
  ``model``      読み込み・正規化・単体検証（L1／L4／L5）
  ``store``      `.ai/feedback/` の読み書き（ラウンドトリップ自己検証つき）
  ``check``      文書をまたぐ検査（L2／L3／L6／L7／P1〜P4／T1）
  ``status``     導出状態と滞留（台帳側に status を保存しない＝PR5）
  ``routing``    起票先の判定表の機械可読な写し（P4）
  ``paths``      パスガード（fail-close）と writer lock
  ``allowlist``  語彙 lint の既知 false positive を理由付きで抑制する
  ``cli``        verb・終了コード（0 / 2 / 4）

設計判断・既知の限界は ``feedback_ledger/README.md``。
"""

from __future__ import annotations

__all__ = ["cli"]
