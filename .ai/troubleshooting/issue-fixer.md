# issue-fixer — 回復手順（非規範）

issue-start-gate の deny、binding marker 欠落、worktree 不一致、karte の hand-off 欠落で停止した場合は、是正者側で gate を迂回せず dispatch 契約を主文脈へ返す。対象 issue、round、branch、repository、expected OID、handoff path の実値を再確認してから再 dispatch する。

adopt-branch や close-attempt の対象が不明、または diff が空の場合は、既存 PR ブランチや prior attempt を推測しない。karte の観測結果を保持し、`--base` と outcome の指定を確認したうえで owner に判断を求める。
