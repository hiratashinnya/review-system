# UT-TD-371-envelope

対象は型付きartifact、producer/phase/Issue/run/入力digest/OID束縛、STOP/未決owner decision/AC欠落のfail-closeである。

TC: `tests/issue_envelope_tests/test_contract.py`。各束縛キーの不一致、producer/phaseの語彙外、VDのAC/TC欠落、STOP、未解消finding、未決owner decisionを入力し、ValueErrorを期待する。全4種の正常artifactは正規化成功する。

TR: `../reports/UT-TR-371-envelope.md`。
