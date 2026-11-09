import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ldm.ai import evidence_packet, investigate, parse_response, request_model
from ldm.common import read_json
from ldm.pipeline import run
from ldm.synthetic import generate


class OptionalAI(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        workspace = Path(self.temp.name) / "lab"
        generate(workspace, policies=5)
        self.result = run(workspace)
        self.run_dir = self.result["run_dir"]
        self.packet = evidence_packet(read_json(self.run_dir / "ai_incidents.json")[0])

    def response(self, proposal=None):
        proposal = proposal or {"policy_id": "P0001", "hypothesis": "Possible allocation across the original 12 installments; inspect the implementation.", "evidence_ids": ["variance", "affected", "endorsements"], "next_steps": ["The reviewer must confirm the allocation rule."], "limitations": "Hypothesis based on synthetic data; not an approved correction.", "needs_human_review": True}
        return {"id": "TEST-ONLY", "model": "TEST-MODEL", "status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(proposal)}]}]}

    def test_missing_key_performs_no_network_call(self):
        with patch.dict("os.environ", {}, clear=True), patch("urllib.request.urlopen") as call:
            with self.assertRaisesRegex(ValueError, "OPENAI_API_KEY"):
                investigate(self.run_dir, "explicit-model")
            call.assert_not_called()

    def test_real_request_contract_and_minimized_packet(self):
        captured = []
        def transport(payload):
            captured.append(payload)
            return self.response()
        output = request_model(self.packet, "explicit-model", "TEST-KEY", transport)
        payload = captured[0]
        self.assertFalse(payload["store"])
        self.assertEqual(payload["text"]["format"]["type"], "json_schema")
        self.assertTrue(payload["text"]["format"]["strict"])
        self.assertNotIn("Maria", payload["input"])
        self.assertNotIn("TEST-KEY", json.dumps(payload))
        self.assertTrue(output["proposal"]["needs_human_review"])

    def test_advisory_output_does_not_change_release_or_sources(self):
        before = (self.run_dir / "summary.json").read_bytes()
        path, results = investigate(self.run_dir, "test-model", transport=lambda _: self.response())
        self.assertTrue(path.exists())
        self.assertFalse(results[0]["is_live_model"])
        self.assertEqual(results[0]["provider"], "test_transport")
        self.assertEqual((self.run_dir / "summary.json").read_bytes(), before)
        self.assertFalse((self.run_dir / "published").exists())

    def test_api_failure_is_nonblocking(self):
        def unavailable(_):
            raise TimeoutError("simulated")
        _, results = investigate(self.run_dir, "test-model", transport=unavailable)
        self.assertEqual(results[0]["status"], "unavailable")
        self.assertEqual(read_json(self.run_dir / "summary.json")["release_status"], "BLOCKED")

    def test_unsafe_proposals_are_rejected(self):
        base = json.loads(self.response()["output"][0]["content"][0]["text"])
        cases = [{**base, "needs_human_review": False}, {**base, "policy_id": "P-OTHER"}, {**base, "evidence_ids": ["fabricated"]}, {**base, "execute_sql": "UPDATE"}, {**base, "hypothesis": ""}]
        for proposal in cases:
            with self.subTest(proposal=proposal), self.assertRaises(ValueError):
                parse_response(self.response(proposal), self.packet)

    def test_refusal_and_incomplete_are_not_treated_as_analysis(self):
        refusal = {"status": "completed", "output": [{"content": [{"type": "refusal"}]}]}
        with self.assertRaises(ValueError):
            parse_response(refusal, self.packet)
        with self.assertRaises(ValueError):
            parse_response({"status": "incomplete"}, self.packet)

    def test_api_error_body_is_not_persisted(self):
        import urllib.error
        import io
        error = urllib.error.HTTPError("https://api.openai.com/v1/responses", 401, "Unauthorized", {}, io.BytesIO(b"SECRET-BODY"))
        with patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaisesRegex(ValueError, "HTTP 401") as context:
                request_model(self.packet, "test-model", "TEST-KEY")
        self.assertNotIn("SECRET", str(context.exception))


if __name__ == "__main__":
    unittest.main()
