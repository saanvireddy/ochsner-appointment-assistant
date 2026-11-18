import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import Mock, patch

from cli import run
from scheduling_api import SchedulingError


class WorkflowTests(unittest.TestCase):
    def interact(self, replies, responses):
        api = Mock()
        api.request.side_effect = responses
        output = io.StringIO()
        with patch("builtins.input", side_effect=[*replies, "quit"]), redirect_stdout(output):
            run(api)
        return api.request.call_args_list, output.getvalue()

    def test_provider_lookup_needs_no_identity(self):
        calls, output = self.interact(
            ["Which primary care providers are downtown?"],
            [{"providers": [{"name": "Dr. Brooks", "locations": ["downtown"]}]}],
        )
        self.assertEqual([call[0][0] for call in calls], ["/providers"])
        self.assertIn("Dr. Brooks", output)

    def test_confirmation_controls_booking(self):
        slot = {"slotId": "slot_1", "providerId": "provider_1",
                "startTime": "2030-01-01T09:00:00-06:00",
                "location": "downtown", "available": True}
        for reply in ("no", "maybe", "yes"):
            with self.subTest(reply=reply):
                responses = [{"providers": []}, {"matches": [{"patientId": "patient_1"}]},
                             {"slots": [slot]}]
                if reply == "yes":
                    responses.append({"appointment": {**slot, "appointmentId": "appt_1"}})
                calls, output = self.interact(
                    ["Book primary care downtown", "555-0101", "1985-04-12", "1", reply],
                    responses,
                )
                paths = [call[0][0] for call in calls]
                expected = ["/providers", "/patients/search", "/availability"]
                if reply == "yes":
                    expected.append("/appointments")
                    self.assertEqual(calls[-1][1]["body"], {
                        "patientId": "patient_1", "slotId": "slot_1", "confirmed": True,
                    })
                    self.assertIn("appt_1", output)
                else:
                    self.assertIn("Booking canceled.", output)
                self.assertEqual(paths, expected)

    def test_no_match_queues_handoff_without_identifiers(self):
        calls, output = self.interact(
            ["Book primary care downtown", "555-9999", "1990-01-01",
             "555-9999", "1990-01-01"],
            [{"providers": []}, {"matches": []}, {"matches": []},
             {"handoffId": "handoff_1"}],
        )
        self.assertEqual([call[0][0] for call in calls],
                         ["/providers", "/patients/search", "/patients/search", "/handoffs"])
        body = calls[-1][1]["body"]
        self.assertEqual(body["reason"], "identity_unclear")
        for identifier in ("555-9999", "1990-01-01"):
            self.assertNotIn(identifier, str(body))
            self.assertNotIn(identifier, output)
        self.assertIn("Human handoff queued", output)

    def test_outage_gives_manual_handoff_path(self):
        calls, output = self.interact(
            ["Find primary care providers downtown"],
            [SchedulingError(503), SchedulingError(503)],
        )
        self.assertEqual([call[0][0] for call in calls], ["/providers", "/handoffs"])
        self.assertIn("contact the clinic's scheduling team directly", output)
        self.assertNotIn("Human handoff queued", output)


if __name__ == "__main__":
    unittest.main()
