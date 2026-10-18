"""GraphQL query文書の拒否境界と既存collectorの互換性。"""

import ast
from pathlib import Path
from unittest.mock import patch

from blocker_gate import github
from tests.unit.blocker_gate_transport_fixtures import GRAPHQL, REST, FakeResponse, ReadTransportCase, body


class GraphQLReadTransportTests(ReadTransportCase):
    def test_unsafe_graphql_documents_never_reach_network(self):
        documents = [
            "mutation { updateIssue(input:{id:\"x\"}) { clientMutationId } }",
            "subscription { viewer { login } }", "{ viewer { login } }", "",
            "query { viewer { login } } mutation Write { x }",
            "query A { viewer { login } } query B { viewer { login } }",
            "query { viewer { login } } fragment F on User { login }",
            "query @skip(if:true) { viewer { login } }", "query { viewer { login }",
            "query { f(arg:[1,2}) }", 'query { f(arg:"unterminated) }',
            'query { f(arg:"""mutation { x }""") }',
            "# query\nmutation { x }", "query { viewer { login } } !",
            'query($x:Input={name:"ok"}) mutation { x }',
        ]
        for document in documents:
            with self.subTest(document=document):
                self.assert_rejected(payload=body(document))


    def test_query_strings_comments_variables_and_defaults_are_not_operations(self):
        documents = [
            '# mutation { write }\nquery mutation($mutation:String="mutation { x }") '
            '{ search(query:$mutation,type:ISSUE,first:1) { issueCount } } # mutation',
            'query($x:Input={nested:{names:["mutation", "}"]}}) { viewer { login } }',
            'query { search(query:"escaped \\\" mutation }",type:ISSUE) { issueCount } }',
        ]
        with patch("blocker_gate.transport.urlopen", return_value=FakeResponse()) as opener:
            for document in documents:
                self.transport.post(GRAPHQL, {}, body(document, variables={"mutation": "mutation { write }"}))
            self.assertEqual(opener.call_count, len(documents))


    def test_invalid_or_ambiguous_json_never_reaches_network(self):
        payloads = [
            b'[]', b'null', b'{}', b'{"query":42}', b'{"query":null}',
            b'{"query":"query { x }","query":"mutation { x }"}',
            b'{"query":"mutation { x }","query":"query { x }"}',
            b'{"query":"query { x }","variables":{"x":1,"x":2}}',
            b'{"query":"query { x }"} {"query":"mutation { x }"}',
            b'{"query":"query { x }","variables":{"x":NaN}}',
            b'{"query":"query { x }","variables":{"x":1e999}}',
            b'{"query":"query { x }","\\u0071uery":"mutation { x }"}',
            b'\xff', b'{"query":"query { x }"', "not bytes",
            body(variables=[]), body(variables=None), body(operationName="Write"),
            body(extensions={"persistedQuery": {"sha256Hash": "x"}}),
            b'{"query":"query { x }","variables":' + b'[' * 1100 + b']' * 1100 + b'}',
        ]
        for payload in payloads:
            with self.subTest(payload=repr(payload)[:100]):
                self.assert_rejected(payload=payload)


    def test_all_three_collector_query_documents_use_real_transport(self):
        tree = ast.parse(Path(github.__file__).read_text())
        queries = [node.value for node in ast.walk(tree) if isinstance(node, ast.Constant)
                   and isinstance(node.value, str) and node.value.lstrip().startswith("query")
                   and "{" in node.value]
        self.assertEqual(len(queries), 3)
        collector = github.GitHubCollector("token", self.transport)
        with patch("blocker_gate.transport.urlopen", return_value=FakeResponse(b'{"data":{}}')) as opener:
            for query in queries:
                self.assertEqual(collector._graphql(query, {"owner": "example", "name": "repo"}), {})
        self.assertEqual(opener.call_count, 3)
        self.assertTrue(any("... on Commit" in query for query in queries))


    def test_collector_follows_rest_pagination_with_real_transport(self):
        page_two = REST + "/issues?per_page=100&page=2"
        first = FakeResponse(b'[{"number":1}]')
        first.headers = {"Link": f'<{page_two}>; rel="next"'}
        collector = github.GitHubCollector("token", self.transport)
        with patch("blocker_gate.transport.urlopen", side_effect=[first, FakeResponse(b'[{"number":2}]')]) as opener:
            self.assertEqual(collector._list("/repos/example/repo/issues"), [{"number": 1}, {"number": 2}])
        self.assertEqual([call.args[0].full_url for call in opener.call_args_list],
                         [REST + "/issues?per_page=100", page_two])
