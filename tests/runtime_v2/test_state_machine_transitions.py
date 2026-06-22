import json
import unittest
from pathlib import Path

SCHEMA_PATH = Path("schemas/runtime_v2/state_machine.schema.json")


class StateMachineTransitionTests(unittest.TestCase):
    def load_schema(self):
        return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    def test_schema_exists_and_has_required_keys(self):
        schema = self.load_schema()
        self.assertIn("states", schema)
        self.assertIn("terminal_states", schema)
        self.assertIn("transitions", schema)

    def test_required_states_exist(self):
        schema = self.load_schema()
        states = set(schema["states"])
        required = {
            "RECEIVED",
            "PLANNED",
            "READY",
            "RUNNING",
            "WAITING_APPROVAL",
            "REPAIRING",
            "TESTING",
            "COMMITTING",
            "COMPLETED",
            "FAILED_RETRYABLE",
            "FAILED_BLOCKED",
            "FAILED_FATAL",
            "CANCELLED",
        }
        self.assertTrue(required.issubset(states))

    def test_required_transitions_exist(self):
        schema = self.load_schema()
        transitions = {tuple(item) for item in schema["transitions"]}
        required = {
            ("RECEIVED", "PLANNED"),
            ("PLANNED", "READY"),
            ("READY", "RUNNING"),
            ("RUNNING", "WAITING_APPROVAL"),
            ("RUNNING", "TESTING"),
            ("RUNNING", "FAILED_RETRYABLE"),
            ("FAILED_RETRYABLE", "REPAIRING"),
            ("REPAIRING", "TESTING"),
            ("TESTING", "COMMITTING"),
            ("COMMITTING", "COMPLETED"),
            ("WAITING_APPROVAL", "RUNNING"),
            ("WAITING_APPROVAL", "FAILED_BLOCKED"),
        }
        self.assertTrue(required.issubset(transitions))

    def test_terminal_states_have_no_outgoing_transitions(self):
        schema = self.load_schema()
        terminal_states = set(schema["terminal_states"])
        transitions = {tuple(item) for item in schema["transitions"]}
        outgoing_from_terminal = [
            transition for transition in transitions if transition[0] in terminal_states
        ]
        self.assertEqual(outgoing_from_terminal, [])

    def test_every_transition_uses_declared_states(self):
        schema = self.load_schema()
        states = set(schema["states"])
        for source, target in schema["transitions"]:
            self.assertIn(source, states)
            self.assertIn(target, states)


if __name__ == "__main__":
    unittest.main()
