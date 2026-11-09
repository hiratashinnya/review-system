# Branch source policy decomposition (#761)

Issue #317: new-branch の分岐元を fresh remote evidence で検証する。

blocker dependency の判定とは材料も失敗理由も異なるため、`blocker_gate`
には混ぜない。通常 branch は fresh `origin/<default>`、stacked branch は
明示された same-repository OPEN PR の exact head OID だけを許可する。

## Public leaf validators and original constraints

--- 公開 leaf validator（Issue #354 PR-2） -----------------------------------
`gitgate/adopt.py`（adopt-branch）は「既存ブランチを exact OID で checkout する」流れであり、
`verify_branch_source`/`create_branch`（新規ブランチ作成・default-branch/stacked-PR の二分岐）
とは分岐点が異なる。フロー全体をコピー流用せず**必要な部分だけ薄く再実装**する方針を採ったが、
leaf 値の検証規則まで二重定義すると「片方だけ緩い」というズレが生まれる。よって leaf validator
だけを公開名で共有する（実体は上の private 実装のまま＝既存呼び出しは無改修）。

**公開するのは repository と branch だけ**（Issue #354 F-354-05）。OID は adopt 側が
40hex ちょうど（`gitgate/adopt.py::_ADOPT_OID`）に**意図的に厳格化**していて共有できない
——`_validate_oid` は 40hex/64hex の両方を受けるので、共有すると adopt の目的（掴む commit を
一意に固定する）が緩む。呼び出し元の無い `validate_oid` を「共有済み」の顔で置いておくと、
読み手が「OID も共有されている」と誤読するため公開しない。

## Responsibility ownership

- policy.py: public facade and orchestration, with unchanged exposed contracts
- model.py: BranchSourceResult and BranchApi protocol
- github_client.py: REST client, token usage and fail-close error mapping
- source_git.py: remote URL and fixed-argv git subprocess boundary
- source_pr.py: OPEN/same-repository/exact PR head verification
- source_default.py: fresh default branch fetch and exact OID validation
- source_stacked.py: PR head read before and after fetch to reject races

No new allow path, changed return code, network fallback, or write side-effect is intended.
