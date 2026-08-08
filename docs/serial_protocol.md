# USB Serial protocol (SmartSeg v1)

This is the authoritative laptop/Arduino contract. The laptop is the protocol coordinator and category decision-maker; the Arduino is a sensor and actuator executor.

## Transport and framing

- USB serial configuration: **115200 baud, 8N1**, UTF-8/ASCII text.
- Each frame is one non-empty line terminated by `\n` (LF). An optional preceding `\r` is ignored.
- Frames must be no longer than 96 bytes including the newline. A receiver discards an overlong or malformed frame and emits `ERROR:FRAME` when possible.
- Reserved separators are `:` and newline. Ordinary values must use uppercase ASCII letters, digits, `_`, `-`, and `.` only; no spaces or colons in values. The sole v1 structured-argument exception is the IR context payload `PROX=<0-1023>,RAIN=<0-1023>`.
- Device starts each session by emitting `HELLO:ARDUINO:1`. The laptop responds `HELLO:LAPTOP:1`. No cycle command is accepted until this exchange completes.

## Message grammar

Every command or event has a positive decimal correlation ID unique among outstanding frames for that sender:

```text
Laptop -> Arduino:  CMD:<id>:<command>[:<argument>]\n
Arduino -> Laptop:  EVT:<id>:<event>[:<argument>]\n
Either direction:   ACK:<id>\n
Arduino -> Laptop:  ERROR:<code>[:<id>]\n
Handshake only:     HELLO:<peer>:1\n
```

`ACK:<id>` confirms the receiver accepted and queued/handled the frame with that ID; it does **not** mean a motor movement is complete. Completion is reported by a separate `EVT` message.

## Arduino to laptop events

| Frame example | Meaning |
| --- | --- |
| `EVT:41:IR_TRIGGERED:PROX=512,RAIN=720` | Item detected at the conveyor entry; laptop should begin its classification window and may use the raw proximity/raindrop readings as secondary context. |
| `EVT:42:CONVEYOR_READY` | Conveyor is ready to accept a cycle. |
| `EVT:43:SERVO_DONE:PLASTIC` | Servo routing for the category completed. |
| `EVT:44:CONVEYOR_STOPPED` | Conveyor is confirmed stopped. |
| `EVT:45:PROXIMITY:NEAR` | Context sensor state update. |
| `EVT:46:RAINDROP:WET` | Context sensor state update. |
| `ERROR:SENSOR_IR:41` | Sensor or executor error; the optional final ID identifies the related command/event when known. |

The laptop must send `ACK:<id>` for every valid `EVT` after it has recorded or queued the event. `ERROR` frames are logged by the laptop; they do not require an ACK.

## Laptop to Arduino commands

| Frame example | Meaning |
| --- | --- |
| `CMD:101:CONVEYOR_START` | Start the conveyor for the current eligible cycle. |
| `CMD:102:CONVEYOR_STOP` | Stop the conveyor immediately. |
| `CMD:103:CLASSIFY:PLASTIC` | Route the current item as plastic. |
| `CMD:104:CLASSIFY:ORGANIC` | Route the current item as organic. |
| `CMD:105:CLASSIFY:METAL` | Route the current item as metal. |
| `CMD:106:CLASSIFY:OTHER` | Route the current item as other. |

The Arduino must return `ACK:<id>` for every valid `CMD` as soon as it accepts it. A `CLASSIFY` command causes exactly one later `EVT:<event-id>:SERVO_DONE:<category>` on success. Unsupported, unsafe, or malformed input emits `ERROR:UNKNOWN_CMD[:<id>]`, `ERROR:BUSY[:<id>]`, `ERROR:NOT_READY:<id>`, or `ERROR:FRAME[:<id>]`; a lost event-ACK window emits `ERROR:LINK:<event-id>` and the firmware stops the conveyor.

## Timing, retry, and safety rules

1. Sender retains each unacknowledged `CMD` or `EVT` for **1 second**. If its ACK is absent, it retransmits the identical frame (same ID) up to **3 total sends**.
2. Receiver must de-duplicate a retransmitted ID for at least **30 seconds**: it re-sends the ACK but must not start the conveyor, route an item, or re-record an event twice.
3. After three failed sends, the laptop marks the serial link unhealthy, stops issuing new cycles, records the failure locally, and requires a fresh `HELLO` exchange after reconnect. Arduino must stop the conveyor and return to a safe idle state when it cannot communicate for **5 seconds** during an active cycle.
4. The laptop must not send `CLASSIFY` until it has received `IR_TRIGGERED` for the active cycle, and must wait for `SERVO_DONE` before treating the disposal event as complete.
5. On `ERROR`, timeout, or unexpected disconnect, the laptop must issue `CONVEYOR_STOP` if the link is still available and must not grant a reward until a completed event is reconciled.

Category tokens are exactly `PLASTIC`, `ORGANIC`, `METAL`, and `OTHER` in v1. Future additions require a protocol-version increment.
