# agy-delegate — 回復手順

実行規範と固有判定は [agent 正本](../agents/agy-delegate.md)、一般診断は [silent-failure-diagnosis](../skills/silent-failure-diagnosis/SKILL.md) にある。

事前検査の失敗は agy 未起動として、分類と秘匿済み理由を返す。設定欠落・競合はオーナーが手で修正する。層別のbinding/schema/location/admin理由と settings_permission_merge_unverified / launch_environment_unverified は根拠不足であり、inspect 合格や fake 合格を実機実行許可に置換しない。

D0 に該当する拒否は既存の当該実行記録の確認と停止報告に限る。本資産に D0 の例外回復手順は無い。ERROR の原因未特定時も自動再試行せず、副作用・クォータ・認可・有限の上限が確認されるまで止める。クラウド/ヘッドレス非対応、認証拒否、未対応の WSL/Windows パスや cwd 引継ぎは別経路へ自動切替しない。

診断記録は自分の実行 ID・会話 ID に束縛されたものだけ読む。画像が無ければ他会話や最新画像から補わない。応答・画像・変更が残っても失敗を完了と報告しない。既存差分から影響を調べ、自動 rollback しない。報告前に秘密値と利用者名を含むパスを秘匿し、argv・環境・設定・エラー全文を無条件に露出させない。

#607 の引渡しは `tmp/codex-report-606-r2.md` の結果・未検証事項を参照する。agy 1.3.3 の4ケースのJSON型・判別は実測fixtureで固定済み。全設定層と合成規則、WSL/Windows cwd、symlink/alias、画像、各 UC の実機記録は未取得であり、bridge 撤去前の確認項目として残る。
