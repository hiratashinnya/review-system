# 全444 Issue の参照先状態・初回横断検査

- Open: 139 / Closed: 305 / 重複番号: 0
- PR と Issue は区別している。406 PR の索引と突合した。
- PR状態の古い断言（機械候補）: 26 Issue。closed Issue の blocker と推定される記述: 46 Issue。
- 優先候補 23 Issue（**誤検出あり**）。未記載でも実装による解消済みを否定できない。

## 検出候補（Open Issue）

| Issue | 優先 | 要確認の根拠（歴史的記述の可能性あり） |
|---|---|---|
| [#375](https://github.com/hiratashinnya/review-system/issues/375) /p/r/-/r/e/v/i/e/w/e/r/ /の/ /f/i/n/d/i/n/g/ /を/フ/ァ/イ/ル/ハ/ン/ド/オ/フ/化/す/る/（/主/文/脈/の/コ/ン/テ/キ/ス/ト/通/過/を/止/め/る/）/ | high | PR #697 はmergedだが旧状態記載候補 / #800 closed but prerequisite mentioned / #800 closed but prerequisite mentioned / #800 closed but prerequisite mentioned / #800 closed but prerequisite mentioned / #797 closed but pre |
| [#691](https://github.com/hiratashinnya/review-system/issues/691) /[/ト/ラ/ッ/キ/ン/グ/]/ /レ/ビ/ュ/ー/指/摘/の/自/動/仕/分/け/と/A/d/v/i/s/o/r/y/中/央/台/帳/を/導/入/す/る/ | high | PR #696 はmergedだが旧状態記載候補 / #781 closed but prerequisite mentioned / #782 closed but prerequisite mentioned / #523 closed but prerequisite mentioned / #683 closed but prerequisite mentioned / #614 closed but pre |
| [#745](https://github.com/hiratashinnya/review-system/issues/745) /[/T/r/a/c/k/i/n/g/ /// /R/e/f/a/c/t/o/r/]/ /m/a/i/n/t/a/i/n/a/b/i/l/i/t/y/_/l/i/n/t/ /既/存/負/債/7/5/件/を/全/解/消/す/る/（/3/ | high | PR #696 はmergedだが旧状態記載候補 / PR #697 はmergedだが旧状態記載候補 / PR #740 はmergedだが旧状態記載候補 / PR #741 はmergedだが旧状態記載候補 |
| [#273](https://github.com/hiratashinnya/review-system/issues/273) /P/R/ /#/2/5/9///#/2/6/0///#/2/6/8/ /レ/ビ/ュ/ー/指/摘/・/残/課/題/の/処/置/ト/ラ/ッ/キ/ン/グ/ | high | PR #260 はclosed-unmergedだが旧状態記載候補 / #270 closed but prerequisite mentioned |
| [#803](https://github.com/hiratashinnya/review-system/issues/803) /[/#/3/7/5/ /子/4/]/ /p/r/-/r/e/v/i/e/w/e/r/ /の/権/限/分/離/を/機/械/で/強/制/す/る/（/P/R/ /コ/メ/ン/ト/投/稿/経/路/・/w/o/r/k/t/r/e/e/ /隔/ | high | PR #697 はmergedだが旧状態記載候補 / PR #479 はmergedだが旧状態記載候補 |
| [#802](https://github.com/hiratashinnya/review-system/issues/802) /[/#/3/7/5/ /子/3/]/ /C/l/a/u/d/e/ /p/r/-/r/e/v/i/e/w/e/r/ /実/機/で/ /f/i/n/d/i/n/g/ /が/欠/落/な/く/ /k/a/r/t/e/ /へ/取/り/込/ま/ | high | PR #697 はmergedだが旧状態記載候補 / #800 closed but prerequisite mentioned |
| [#606](https://github.com/hiratashinnya/review-system/issues/606) /a/g/y/-/d/e/l/e/g/a/t/e/ /を/ /a/g/y/ /直/接/実/行/ラ/ッ/パ/ー/へ/移/行/し/、/許/可/ル/ー/ル/検/査/と/規/範/を/整/備/す/る/（/#/5/7/5/ /の/子/ /S/1/ | high | PR #680 はmergedだが旧状態記載候補 / #605 closed but prerequisite mentioned |
| [#547](https://github.com/hiratashinnya/review-system/issues/547) /b/l/o/c/k/e/r/_/g/a/t/e/ /に/非/ブ/ロ/ッ/キ/ン/グ/診/断/チ/ャ/ネ/ル/を/追/加/し/、/機/械/可/読/レ/ポ/ー/ト/と/し/て/ /p/u/b/l/i/s/h/ /す/る/ | high | PR #479 はmergedだが旧状態記載候補 / #461 closed but prerequisite mentioned |
| [#652](https://github.com/hiratashinnya/review-system/issues/652) /#/3/7/1/ /導/入/後/の/工/程/分/離/・/新/ロ/ー/ル/権/限/・/a/d/v/i/s/e/r/を/初/回/実/d/i/s/p/a/t/c/h/で/検/証/す/る/ | high | #371 closed but prerequisite mentioned / #371 closed but prerequisite mentioned |
| [#578](https://github.com/hiratashinnya/review-system/issues/578) /h/a/r/n/e/s/s/ /と/ /d/s/v/2/ /の/既/存/テ/ス/ト/コ/ー/ド/を/ /t/e/s/t/s///道/具/名/// /へ/移/設/す/る/ | high | #542 closed but prerequisite mentioned / #538 closed but prerequisite mentioned |
| [#576](https://github.com/hiratashinnya/review-system/issues/576) /P/R/ /#/2/3/3/ /の/公/開/前/ /r/e/m/o/t/e/ /検/証/要/件/を/ /#/5/3/8/／/g/i/t/g/a/t/e/ /の/複/数/ロ/ー/ル/ /p/u/s/h/ /設/計/へ/引/き/渡/す/ | high | #538 closed but prerequisite mentioned |
| [#575](https://github.com/hiratashinnya/review-system/issues/575) /a/g/y/-/d/e/l/e/g/a/t/e/／/s/i/l/e/n/t/-/f/a/i/l/u/r/e/-/d/i/a/g/n/o/s/i/s/ /を/ /./a/i/ /正/本/構/成/で/作/り/直/し/、/a/g/y/ / | high | #605 closed but prerequisite mentioned |
| [#310](https://github.com/hiratashinnya/review-system/issues/310) /r/e/f/a/c/t/o/r/(/i/s/s/u/e/-/p/i/p/e/l/i/n/e/)/:/ /是/正/ル/ー/プ/ /②/-/c/ /を/カ/ル/テ/機/構/へ/書/き/換/え/実/害/基/準/と/エ/ス/カ/レ/ー/シ/ | high | #308 closed but prerequisite mentioned / #309 closed but prerequisite mentioned |
| [#290](https://github.com/hiratashinnya/review-system/issues/290) /P/R/ /#/2/5/9/:/ /a/g/y/-/d/e/l/e/g/a/t/e/ /の/ /w/o/r/k/s/p/a/c/e/ /// /f/a/i/l/-/c/l/o/s/e/ /g/a/t/e/ /を/安/全/に/成/立/ | high | #270 closed but prerequisite mentioned |
| [#679](https://github.com/hiratashinnya/review-system/issues/679) /a/g/y/-/d/e/l/e/g/a/t/e/:/ /会/話/記/録/・/結/果/フ/ァ/イ/ル/の/確/定/と/ /C/L/I/ /返/却/の/一/致/（/二/重/故/障/の/窓/）/ | medium | PR #627 はmergedだが旧状態記載候補 |
| [#333](https://github.com/hiratashinnya/review-system/issues/333) /F/N/D/「/検/査/対/象/探/索/の/欠/陥/」/と/「/ミ/ラ/ー/未/同/期/」/を/1/件/に/統/合/す/べ/き/か/（/双/方/ /E/R/R/O/R/・/同/じ/下/流/損/害/）/ | medium | PR #326 はmergedだが旧状態記載候補 |
| [#832](https://github.com/hiratashinnya/review-system/issues/832) /i/m/p/r/o/v/e/m/e/n/t/(/t/r/i/a/g/e/)/:/ /t/r/i/a/g/e/r/ /が/ /r/e/v/i/e/w/e/r/ /の/到/達/経/路/・/前/提/脅/威/の/根/拠/を/独/立/評/価/ | medium | #830 closed but prerequisite mentioned |
| [#805](https://github.com/hiratashinnya/review-system/issues/805) /d/o/c/s/(/k/a/r/t/e/)/:/ /m/o/d/e/l/./p/y/ /入/口/の/ /d/o/c/s/t/r/i/n/g/ /要/約/化/後/、/同/「/改/ざ/ん/防/止/の/機/械/的/裏/付/け/と/既/知/ | medium | #747 closed but prerequisite mentioned |
| [#752](https://github.com/hiratashinnya/review-system/issues/752) /[/M/a/i/n/t/a/i/n/a/b/i/l/i/t/y/ /I/-/0/1/]/ /S/u/b/a/g/e/n/t/S/t/o/p/判/定/・/進/行/ポ/イ/ン/タ/を/分/離/ | medium | #722 closed but prerequisite mentioned |
| [#580](https://github.com/hiratashinnya/review-system/issues/580) /J/e/v/:/ /s/h/a/d/o/w/評/価/に/基/づ/く/ル/ー/ル/別/e/n/f/o/r/c/e/移/行/ | medium | #572 closed but prerequisite mentioned |
| [#565](https://github.com/hiratashinnya/review-system/issues/565) /素/の/ /C/o/d/e/x/ /起/動/で/、/A/G/E/N/T/S/./m/d/ /の/「/実/装/は/ /s/u/b/a/g/e/n/t/ /に/委/譲/す/る/」/が/実/装/担/当/へ/の/指/示/と/相/反/し/、/ | medium | #583 closed but prerequisite mentioned |
| [#336](https://github.com/hiratashinnya/review-system/issues/336) /C/o/d/e/x/に/も/C/o/n/t/e/x/t/-/m/o/d/e/を/導/入/す/る/。/ | medium | #306 closed but prerequisite mentioned |
| [#291](https://github.com/hiratashinnya/review-system/issues/291) /P/R/ /#/2/6/0/:/ /s/i/l/e/n/t/-/f/a/i/l/u/r/e/ /診/断/資/産/と/ /c/o/d/e/x/-/r/e/v/i/e/w/ /の/安/全/な/実/行/契/約/を/確/立/す/る/ | medium |  |

## 留意
- 同じPRの履歴的な記述（過去はDraftだった、等）は誤りではない。Issue作成後の追記が古い場合の更新のみ対象。
- Closed Issue は原則歴史的な証跡として保持。Open IssueのACや完了判定は独立証拠を要する。
- 語彙抽出の限界があるため、重要候補は最新本文、コメント、mainコードを別途実査する。
