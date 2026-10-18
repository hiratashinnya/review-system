# Issue #469: GitHub読み取りtransportの契約

## 判断

`ReadTransport`と`UrlLibReadTransport`の名前を保ち、実装を読み取りだけに制限する。`get`は`https://api.github.com`の`/repos/`配下、`post`は完全一致する`https://api.github.com/graphql`への単一の明示`query`だけを許可する。HTTPメソッドだけではGraphQL mutationを防げないため、POST本文を送信前に検査する。契約違反はネットワークに到達する前に`ValueError`にし、GitHub応答や接続障害の既存`GitHubReadError`契約には新しいreasonを増やさない。

JSONはUTF-8の単一objectとし、`query`と任意のobject型`variables`だけを許可する。全階層の重複key、batch、`operationName`、`extensions`、persisted query、非有限数、余剰データを拒否する。HTTPヘッダは既存collectorの5種類だけを大文字小文字を区別せず許可し、重複と改行を拒否する。POSTのContent-Typeは`application/json`に固定し、Host、Content-Encoding、Content-Length等による別解釈を持ち込ませない。GETはdot segment、encoded traversal、backslashを拒否し、通常のbranch名の`%2F`とpaginationのquery stringは維持する。

GraphQL全文法を実装せず、既存collectorの3系統のqueryとinline fragmentを含む狭いsubsetを受理する。字句を全文消費し、コメント・JSON互換の通常文字列・変数default objectを区別して、単一queryのselection setの後にtokenが残らないことを確認する。文字列や変数名の`mutation`は操作として扱わない。mutation、subscription、複数operation、shorthand query、fragment定義、block string、operation directiveは拒否する。block stringは内容の解釈に入る前に拒否する。queryのfieldや引数の完全な文法・schema検証はGitHubに任せ、不正なqueryをmutationへ変換する経路は持たない。

## 比較と分割

docstringだけの訂正では読み取り専用という名前の誤契約が残る。汎用transportへの改名案は既存の長いcaller moduleのexact fingerprintを変え、Issue対応PRでbaseline更新を必要としたため却下した。PR #657でtransport抽出とそのbaseline変更を先に分離している。この抽出を活かし、Issue対応PR #659ではcallerとbaselineをマージ済みmainと同一に保ち、100行以内の小moduleへ検査責務を分ける。追加の負債登録やlintの緩和は行わない。

## `project_status_sync`との関係

`project_status_sync/github.py`の`Transport`と`UrlLibTransport`は独立したまま維持する。同moduleはProjects V2の認証要件、project固有の応答検証、意図的な`updateProjectV2ItemFieldValue` mutationを担う。読み取りtransportのquery制限を共有すると意図的な更新ができなくなる。両adapterの小さな標準ライブラリによるHTTP処理をそれぞれのdomainに置き、読み取りと書き込みの契約を分離する。
