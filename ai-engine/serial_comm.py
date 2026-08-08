"""Threaded implementation of the SmartSeg v1 newline-framed serial protocol."""
from __future__ import annotations

import logging
import queue
import random
import threading
import time
from dataclasses import dataclass
from typing import Any

import config

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class SerialEvent:
    event_id: int
    name: str
    argument: str | None = None


class MockSerial:
    """In-memory pyserial-like transport used by MockSerialCommunicator."""
    def __init__(self) -> None:
        self.incoming: queue.Queue[bytes] = queue.Queue()
        self.closed = False

    def readline(self) -> bytes:
        try:
            return self.incoming.get(timeout=0.2)
        except queue.Empty:
            return b""

    def write(self, data: bytes) -> int:
        return len(data)

    def close(self) -> None:
        self.closed = True


class SerialCommunicator:
    def __init__(self, mock_mode: bool = config.MOCK_MODE) -> None:
        self.mock_mode = mock_mode
        self.transport: Any | None = None
        self.events: queue.Queue[SerialEvent] = queue.Queue()
        self._deferred_events: list[SerialEvent] = []
        self._seen_event_ids: dict[int, float] = {}
        self._ack_waiters: dict[int, threading.Event] = {}
        self._lock = threading.Lock()
        self._next_id = 100
        self._running = threading.Event()
        self._listener: threading.Thread | None = None

    def start(self) -> None:
        if self.mock_mode:
            self.transport = MockSerial()
        self._running.set()
        self._listener = threading.Thread(target=self._listen, name="arduino-serial", daemon=True)
        self._listener.start()
        if self.mock_mode:
            self._inject("HELLO:ARDUINO:1")
            threading.Thread(target=self._mock_ir_loop, name="mock-ir", daemon=True).start()

    def close(self) -> None:
        self._running.clear()
        if self.transport:
            self.transport.close()

    def wait_for_event(self, event_name: str, timeout: float | None = None) -> SerialEvent | None:
        # Preserve out-of-order sensor context for the next consumer instead of losing it.
        for index, event in enumerate(self._deferred_events):
            if event.name == event_name:
                return self._deferred_events.pop(index)
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            remaining = None if deadline is None else max(0, deadline - time.monotonic())
            if remaining == 0:
                return None
            try:
                event = self.events.get(timeout=remaining)
            except queue.Empty:
                return None
            if event.name == event_name:
                return event
            LOGGER.debug("Deferred serial event %s", event)
            self._deferred_events.append(event)

    def classify_and_wait(self, category: str) -> bool:
        # Command ACK follows v1's 3-send reliability rule. Servo completion gets one safe resend.
        command_id = self.send_command("CLASSIFY", category)
        if command_id is None:
            return False
        for attempt in range(2):
            done = self.wait_for_event("SERVO_DONE", config.SERVO_DONE_TIMEOUT_SECONDS)
            if done and done.argument == category:
                return True
            if attempt == 0:
                LOGGER.warning("SERVO_DONE timeout; retrying identical CLASSIFY frame once")
                self._send_command_with_id(command_id, "CLASSIFY", category)
        LOGGER.error("No SERVO_DONE for CLASSIFY:%s", category)
        return False

    def send_command(self, command: str, argument: str | None = None) -> int | None:
        with self._lock:
            command_id = self._next_id
            self._next_id += 1
        return command_id if self._send_command_with_id(command_id, command, argument) else None

    def _send_command_with_id(self, command_id: int, command: str, argument: str | None) -> bool:
        suffix = f":{argument}" if argument else ""
        frame = f"CMD:{command_id}:{command}{suffix}"
        waiter = self._ack_waiters.setdefault(command_id, threading.Event())
        for send_number in range(3):
            self._write(frame)
            if waiter.wait(config.SERIAL_TIMEOUT_SECONDS):
                self._ack_waiters.pop(command_id, None)
                return True
            LOGGER.warning("No ACK for %s (send %s/3)", frame, send_number + 1)
        self._ack_waiters.pop(command_id, None)
        LOGGER.error("Serial link unhealthy after command ACK failure: %s", frame)
        return False

    def _listen(self) -> None:
        while self._running.is_set():
            if self.transport is None:
                try:
                    import serial
                    self.transport = serial.Serial(config.SERIAL_PORT, config.SERIAL_BAUD_RATE, timeout=0.2)
                    LOGGER.info("Connected to Arduino serial port %s", config.SERIAL_PORT)
                except Exception as error:
                    LOGGER.error("Arduino serial unavailable (%s); retrying in %ss", error, config.SERIAL_RECONNECT_SECONDS)
                    time.sleep(config.SERIAL_RECONNECT_SECONDS)
                    continue
            try:
                raw = self.transport.readline()
                if raw:
                    self._handle_line(raw.decode("utf-8", errors="replace").strip())
            except Exception as error:
                LOGGER.error("Arduino serial disconnected (%s); retrying in %ss", error, config.SERIAL_RECONNECT_SECONDS)
                try: self.transport.close()
                except Exception: pass
                self.transport = None
                time.sleep(config.SERIAL_RECONNECT_SECONDS)

    def _handle_line(self, line: str) -> None:
        if not line or len(line) > 95:
            LOGGER.warning("Discarded malformed serial frame: %r", line)
            return
        parts = line.split(":")
        if parts[:2] == ["HELLO", "ARDUINO"]:
            self._write("HELLO:LAPTOP:1")
            return
        if parts[0] == "ACK" and len(parts) == 2 and parts[1].isdigit():
            waiter = self._ack_waiters.get(int(parts[1]))
            if waiter:
                waiter.set()
            return
        if parts[0] == "EVT" and len(parts) >= 3 and parts[1].isdigit():
            event = SerialEvent(int(parts[1]), parts[2], ":".join(parts[3:]) or None)
            self._expire_seen_events()
            self._write(f"ACK:{event.event_id}")
            if event.event_id in self._seen_event_ids:
                LOGGER.debug("Deduplicated retransmitted Arduino event %s", event.event_id)
                return
            self._seen_event_ids[event.event_id] = time.monotonic()
            self.events.put(event)
            return
        if parts[0] == "ERROR":
            LOGGER.error("Arduino error: %s", line)
            return
        LOGGER.warning("Unknown serial frame: %s", line)

    def _expire_seen_events(self) -> None:
        cutoff = time.monotonic() - 30
        self._seen_event_ids = {event_id: seen_at for event_id, seen_at in self._seen_event_ids.items() if seen_at >= cutoff}

    def _write(self, frame: str) -> bool:
        if self.transport is None:
            LOGGER.error("Cannot send %s: Arduino serial is disconnected", frame)
            return False
        LOGGER.debug("Serial TX %s", frame)
        try:
            self.transport.write((frame + "\n").encode("ascii"))
        except Exception as error:
            LOGGER.error("Arduino write failed (%s); reconnecting", error)
            try: self.transport.close()
            except Exception: pass
            self.transport = None
            return False
        if self.mock_mode and frame.startswith("CMD:"):
            parts = frame.split(":")
            self._inject(f"ACK:{parts[1]}")
            if len(parts) == 4 and parts[2] == "CLASSIFY":
                threading.Timer(0.4, self._inject, args=(f"EVT:{self._new_mock_id()}:SERVO_DONE:{parts[3]}",)).start()
        return True

    def _inject(self, frame: str) -> None:
        if self.transport and isinstance(self.transport, MockSerial):
            self.transport.incoming.put((frame + "\n").encode("ascii"))

    def _new_mock_id(self) -> int:
        return random.randint(1000, 9999)

    def _mock_ir_loop(self) -> None:
        time.sleep(1)
        while self._running.is_set():
            # Standard v1 contexts are independent events; main also supports legacy combined suffixes.
            self._inject(f"EVT:{self._new_mock_id()}:PROXIMITY:NEAR")
            self._inject(f"EVT:{self._new_mock_id()}:RAINDROP:WET")
            self._inject(f"EVT:{self._new_mock_id()}:IR_TRIGGERED")
            time.sleep(config.MOCK_IR_INTERVAL_SECONDS)
