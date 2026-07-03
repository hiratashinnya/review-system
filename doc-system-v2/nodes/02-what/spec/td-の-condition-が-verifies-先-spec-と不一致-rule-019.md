**前提条件**: TD が SPEC に `verifies` 辺を持ち、両者に `condition` 属性がある
**入力/トリガ**: TD の `condition` が verifies 先 SPEC の `condition` と一致しない
**期待動作**: RULE-019 WARNING を報告する
