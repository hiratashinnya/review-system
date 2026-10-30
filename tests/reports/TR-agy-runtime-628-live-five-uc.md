# TR: agy 1.4.8 通常wrapper実機5UC

AI agent: Codex（runtime_628）。判定は観測した限定cohortに限る。

| 実測 | source HEAD | 結果 | 安全OBS |
|---|---|---|---|
| 初回校正＋影響分析 | edda08220ef5060e38685f39af8fcfdbb37a5640 | 成功、当時usage未保持 | OBS-agy-runtime-628-edda082-single.json |
| 校正＋通常4UC | 1e6594bbadb8455d241491fd01a5b7310daf650e | 影響分析・草案・外部調査・画像生成成功 | OBS-agy-runtime-628-1e6594b-four-uc.json |
| 子2校正＋通常parallel2 | 01cc08066dda3f1e62d932e9134d34436ad7125f | 2job成功、外部observerで実生存重複 | OBS-agy-runtime-628-01cc080-parallel.json／OBS-agy-runtime-628-01cc080-parallel-observer.json |

後2実測のpackageはfb11ab2と同一、SHA256 05ccaf419f31373e268369a230787e0ada71b1fbf73c87fcd95ca488a56f328f。HEADの差は報告専用commitである。初回実測は旧sourceであり後2実測と同一source扱いしない。各live manifest SHA・実行HEAD・元private command記録SHA・byte exactコピー元はOBS-agy-runtime-628-live-provenance.jsonにある。公開provenanceは個人の絶対pathを省略したentry／環境変数名の提示であり、実command全文とは称さない。

4UCは通常runner.runによるsuccess_candidate／SUCCESS／exit0／reason0／version1.4.8。影響分析はprompt非収載fixture suffixとcaller、草案は読取fixtureのmarkerとPurpose／Risks／Verification、外部調査は公式Python unittest URLと本文assertLogsのformatter／3.15追加を照合した。外部web toolの直接呼出し観測はfalseであり、調査成果の内容検証と区別する。

画像はimages=Trueの本番wrapperが返却会話の新規brain artifactを回収した1件。ラスターmagic確認、270217bytes、SHA256 49dd7f541188de858c85f7f2242b8985515dd6d6fa6d5ece94c642e9fe3d5a12。native prompt起動は校正1＋通常4の5件、画像内部subagent／model数はunknown。旧画像・別connector・SVGで代用していない。

parallelは固定許可W配下の非重複A/Bを使用し、共有logical templateをbaseline前に確定した。native allow2、W/A/Bのcorpus deny3＋全command deny1、ask空。project/shared空、G1 credits false。各子相対anchorを本番WSL process adapterで観測して同snapshot／root／子cwd／template SHAへ束縛したproof2件を発行し、通常run_parallel(max_concurrency=2)で子別payloadのprompt非収載nonceを回収した。

外部Windows observerは固定native exe・unique argv marker・PID・CIMとprocess handleのnative start一致を検査し、異なる2PIDのA_alive→B_alive→A_aliveを単調時計で観測した。first／last alive intervalも約9.86秒重なる。自己申告やWSL cwdだけで同時性を推定していない。W全体before／after差分4、子外差分0、全corpusとPS3canary不変。per-job保存結果は成功のまま保持し、UC側観測から後付け再分類していない。

| native terminal | input | output | thinking | cache_read | total |
|---|---:|---:|---:|---:|---:|
| 影響分析 | 4935 | 276 | 0 | 11315 | 5211 |
| 草案 | 4921 | 617 | 0 | 11319 | 5538 |
| 外部調査 | 9285 | 533 | 0 | 19452 | 9818 |
| 画像生成 | 9430 | 951 | 0 | 37027 | 10381 |
| 子A校正 | 4850 | 198 | 0 | 11363 | 5048 |
| 子B校正 | 4859 | 206 | 0 | 11363 | 5065 |
| 子A通常 | 4921 | 151 | 0 | 11363 | 5072 |
| 子B通常 | 4933 | 153 | 0 | 11365 | 5086 |

usageは観測値をそのまま保存し、加算関係や内部モデル全体の会計は推測しない。4UCsessionの低層校正usageは未収載で、通常4件は保持した。parallelのmodel_launch_countもunverifiedを維持する。

全sessionで原4設定bytes／ACL／ownerをWindows親メモリに保持しfinally完全復元、自然終了、stderr空、exe／source不変、private output cleanup、復元後proof失効を確認した。raw設定永続化false、認証読取・恒久設定変更・追加購入・強制終了なし。proofはcommitted、durability warning false。

これは限定native file-only adapterの観測であり、全層一般merge、任意admin schema、全環境のsandbox、engine直接拒否、実行者の完全帰属、一時変更やmetadata変更の完全監査は証明しない。個人accountはowner申告に基づく。5UC成果、最終AC、独立レビュー、公開PR記録、owner手動mergeはそれぞれ区別する。
