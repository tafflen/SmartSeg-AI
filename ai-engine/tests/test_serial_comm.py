"""Regression tests for protocol-level serial safety."""
from __future__ import annotations

import queue
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from serial_comm import MockSerial, SerialCommunicator  # noqa: E402


class DuplicateEventTest(unittest.TestCase):
    def test_duplicate_event_is_acked_twice_but_queued_once(self) -> None:
        communicator = SerialCommunicator(mock_mode=True)
        communicator.transport = MockSerial()
        acknowledgements: list[str] = []
        original_write = communicator._write

        def capture_write(frame: str) -> bool:
            acknowledgements.append(frame)
            return original_write(frame)

        communicator._write = capture_write  # type: ignore[method-assign]
        communicator._handle_line("EVT:41:IR_TRIGGERED:PROX=512,RAIN=720")
        communicator._handle_line("EVT:41:IR_TRIGGERED:PROX=512,RAIN=720")

        event = communicator.events.get_nowait()
        self.assertEqual((event.event_id, event.name), (41, "IR_TRIGGERED"))
        with self.assertRaises(queue.Empty):
            communicator.events.get_nowait()
        self.assertEqual(acknowledgements, ["ACK:41", "ACK:41"])


if __name__ == "__main__":
    unittest.main()
