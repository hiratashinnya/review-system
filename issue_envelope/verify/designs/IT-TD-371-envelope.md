# IT-TD-371-envelope

対象は同型TOMLの包含木全体復元と独立した実行順DAG、共通ref索引である。

TC: `tests/issue_envelope_tests/test_graph.py` と `tests/issue_envelope_tests/test_trace.py`。単一対象のroot+leaf、およびroot+中間group+leafを復元する。parent/childrenの相互不整合、包含循環、unit DAG循環/欠落を拒否し、deps/dependents/orphansで同じ索引を照会する。canonical roundtripと既存artifactの上書き拒否も確認する。CP/VDの複数対象・中間グループ8ノードの全体復元と、任意名refフィールドの宣言駆動、孤立検出を検査する。

TR: `../reports/IT-TR-371-envelope.md`。
