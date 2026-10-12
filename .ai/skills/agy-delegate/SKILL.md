# agy 直接実行への作業移譲

ユーザーが明示起動する入口。影響調査・参照調査・ノード素案・外部調査・スクラッチコード・画像・独立タスクを、`agy-delegate` 担当へ委譲する。共通手順と UC 表は [agent 正本](../../agents/agy-delegate.md)、診断一般則は [silent-failure-diagnosis](../silent-failure-diagnosis/SKILL.md) に置く。両方を必ず読む。

## 呼び出し契約

呼出元はタスク、workspace、実行ファイル、適用設定の根拠、有限の timeout、期待する成果、変更してよい範囲、既存停止条件を担当へ渡す。画像では brain 保存領域も特定する。リポジトリ依存の依頼では非機密アンカーの期待値を呼出元で保持し、期待値自体を prompt に渡さない。

担当はラッパー `python3 -m agy_delegate` だけで起動する。実行ファイルと実在 workspace/cwd、当該実行の許可設定、呼出元の実行権限と停止条件を確認できなければ子プロセスを起動しない。設定検査は省略不可で設定を変更しない。実行不可能な環境で別経路へ自動切替しない。

agy の設定上の書込許可は workspace 全体、`doc-system-v2/nodes` の再帰 `write_file` deny で corpus を除外する。書ける範囲を個々の依頼の変更範囲と混同しない。corpus の確定反映は author → validator → reconciliation に限る。その他のファイルも正本・生成物・レビュー規約に従う。

## 現在の利用制約

直接実行への接続は配置済み。agy 1.3.3 の成功・拒否・print-timeout・クォータERRORの実測JSONを型契約とfixtureへ反映し、`output_contract_unverified` を解除した。global/projectの場所とproject優先、共有userのpermissions merge参加には公式根拠がある。projectファイル名/スキーマ、共有userの場所/スキーマ、adminの適用有無/優先、permissions配列合成とWSL→Windows変換は未特定のため、通常 `run` は層別の未特定理由・`settings_permission_merge_unverified` / `launch_environment_unverified` で停止し、agy を起動しない。全層のread-only監査を用意したが、保守的集約は実効mergeの証明ではない。解除条件と根拠は [CLI文書](../../../agy_delegate/README.md) に従う。偽プロセスの CI 合格は実機 UC 動作の証拠ではない。解消案と #607 への引渡し条件は [rationale](../../rationale/agy-delegate.md) を参照する。

## done

- 事前検査・実行結果と、依頼の達成を別々に確認した。
- 拒否・異常・アンカー不一致・前置きだけの回答・成果物欠落を完了として返していない。
- 実行 ID、会話 ID、検証済み成果、未完了箇所、失敗時に残った変更と秘匿済み理由を返した。
- 実機未確認・設定合成未確認・呼出元停止の未強制範囲を保証済みと説明していない。
