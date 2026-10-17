"""同run/targetの相談取り違えとtrusted時間境界を検証する。"""
from codex_worktree_exec.adviser_capture import AdviceCaptureError, ORIGIN_FIELDS, capture_advice
from codex_worktree_exec.adviser_request import request_digest, validate_adviser_request
from tests.unit import test_codex_initial_binding as fixtures


class AdviserOriginBudgetTests(fixtures.InitialBindingTests):
    def response(self, request):
        return {**{key: request[key] for key in ORIGIN_FIELDS},
                "request_digest": request_digest(request), "status": "complete", "answer": "助言"}

    def meter(self, **changes):
        return dict(status="success", tokens=1, cost_microusd=1, elapsed_seconds=1, **changes)

    def test_origin_schema_and_role_phase(self):
        request = self.request()
        for key in ("phase", "work_unit", "max_seconds", "seconds_used", "reserve_seconds"):
            missing = dict(request)
            del missing[key]
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_adviser_request(missing, self.root, self.oid)
        for changes in ({"phase": "implementation"}, {"work_unit": ""}, {"clock": 0}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate_adviser_request({**request, **changes}, self.root, self.oid)
        for role, phase in (("issue-investigator", "investigation"),
                            ("ac-designer", "verification_design"),
                            ("change-planner", "solution_planning")):
            early = {**request, "caller_role": role, "phase": phase, "work_unit": "phase-task"}
            validate_adviser_request(early, self.root, self.oid)
            self.assertEqual(capture_advice(early, self.response(early), self.meter())["phase"], phase)

    def test_different_phase_or_unit_cannot_reuse_answer(self):
        request = {**self.request(), "caller_role": "plan-reviewer", "phase": "verification_design"}
        answer = self.response(request)
        for changes in ({"phase": "solution_planning"}, {"work_unit": "WU-2"}):
            other = {**request, **changes}
            validate_adviser_request(other, self.root, self.oid)
            with self.subTest(changes=changes), self.assertRaises(AdviceCaptureError) as failure:
                capture_advice(other, answer, self.meter())
            self.assertEqual(failure.exception.record["work_unit"], other["work_unit"])
            forged = {**answer, "request_digest": request_digest(other)}
            with self.assertRaises(AdviceCaptureError):
                capture_advice(other, forged, self.meter())

    def test_time_input_and_capture_boundaries(self):
        request = self.request()
        for value in (-1, float("nan"), float("inf"), True, None, "1", 10 ** 1000):
            for key in ("max_seconds", "seconds_used", "reserve_seconds"):
                with self.subTest(value=value, key=key), self.assertRaises(ValueError):
                    validate_adviser_request({**request, key: value}, self.root, self.oid)
            with self.subTest(value=value), self.assertRaises(AdviceCaptureError):
                capture_advice(request, self.response(request), {**self.meter(), "elapsed_seconds": value})
        exhausted = {**request, "seconds_used": 60}
        with self.assertRaises(ValueError):
            validate_adviser_request(exhausted, self.root, self.oid)
        boundary = {**request, "seconds_used": 50}
        validate_adviser_request(boundary, self.root, self.oid)
        for meter in ({**self.meter(), "elapsed_seconds": 10}, {**self.meter(), "started_at": 0},
                      {"status": "success", "tokens": 1, "cost_microusd": 1}):
            with self.subTest(meter=meter), self.assertRaises(AdviceCaptureError) as failure:
                capture_advice(boundary, self.response(boundary), meter)
            self.assertEqual(failure.exception.record["status"], "failed")
            self.assertEqual(failure.exception.record["metrics"], meter)
        result = capture_advice(boundary, self.response(boundary), self.meter())
        self.assertEqual((result["seconds_used"], result["calls_used"]), (51, 1))
        self.assertEqual(result["adoption"], "pending")

    def test_failures_preserve_origin_partial_status_and_unknown_usage(self):
        request = self.request()
        for response, meter in (({**self.response(request), "status": "partial"}, self.meter()),
                                (self.response(request), {**self.meter(), "cost_microusd": None}),
                                (self.response(request), {**self.meter(), "status": "failure"})):
            with self.subTest(response=response, meter=meter), self.assertRaises(AdviceCaptureError) as failure:
                capture_advice(request, response, meter)
            record = failure.exception.record
            self.assertEqual(record["output_status"], response["status"])
            self.assertEqual(record["metrics"], meter)
            self.assertEqual(record["budget"]["max_seconds"], 60)
            self.assertEqual(record["input_refs"], request["input_refs"])
            self.assertTrue(record["failure_reason"])
