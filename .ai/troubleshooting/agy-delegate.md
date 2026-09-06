# agy-delegate — 回復手順（非規範）

agy status が OK でない場合は ask、continue、swarm、image を試さず、その status とエラー全文を呼び出し元へ返す。クラウド／ヘッドレス環境での推測実行や別 transport への無断切替はしない。

WSL から Windows の agy CLI を呼ぶ場合、workspace は Windows 形式へ変換する。`/mnt/c/Users/foo/bar` は `C:\Users\foo\bar` とし、変換後にも `[WinError 267]` が出るなら workspace の存在・ディレクトリ種別・認証を確認して停止する。agy が返した素案やレポートを正本へ直接書き込まず、型別 author、validator、reconciliation の経路へ戻す。
