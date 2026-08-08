/*
  SmartSeg Arduino Uno firmware
  USB serial protocol: docs/serial_protocol.md (SmartSeg v1)

  The Uno is deliberately a sensor/actuator executor. It never classifies waste;
  the laptop sends the category after camera inference.
*/
#include <Servo.h>
#include <stdlib.h>
#include <string.h>

// Pin map
const byte IR_PIN = 2;
const byte PROXIMITY_PIN = A0;
const byte RAIN_PIN = A1;
const byte SERVO_PIN = 9;
const byte MOTOR_IN1_PIN = 5;
const byte MOTOR_IN2_PIN = 6;
const byte MOTOR_ENA_PIN = 7;
const byte STATUS_LED_PIN = 13;

const unsigned long SERIAL_BAUD = 115200;
const unsigned long CLASSIFY_TIMEOUT_MS = 5000;
const unsigned long ACK_TIMEOUT_MS = 1000;
const byte MAX_EVENT_SENDS = 3;
const unsigned long DUPLICATE_WINDOW_MS = 30000;

// Set false if the installed IR module has an active-LOW digital output.
const bool IR_ACTIVE_HIGH = true;
const int SERVO_NEUTRAL_ANGLE = 70;
const int PLASTIC_ANGLE = 0;
const int ORGANIC_ANGLE = 45;
const int METAL_ANGLE = 90;
const int OTHER_ANGLE = 135;

Servo diverterServo;
char lineBuffer[97];                 // Protocol limit is 96 bytes including LF.
byte lineLength = 0;
bool lineOverflow = false;
bool sessionReady = false;
bool waitingForClassification = false;
bool previousIrPresent = false;
unsigned long triggerTime = 0;
unsigned long nextEventId = 1;

// One event is outstanding at a time. Laptop ACKs it before sending a command.
bool pendingEvent = false;
unsigned long pendingEventId = 0;
char pendingEventFrame[97];
byte pendingEventSends = 0;
unsigned long pendingEventSentAt = 0;

// The laptop retransmits an identical command ID after an ACK timeout. Do not
// actuate a duplicate command within the protocol's required 30-second window.
unsigned long lastCommandId = 0;
unsigned long lastCommandAt = 0;

unsigned long ledLastToggle = 0;
byte errorTogglesRemaining = 0;
bool ledState = true;

void conveyorControl(bool run);
void readSensors();
void handleSerialCommand(char *line);
void moveServoToCategory(const char *category);
void queueEvent(const char *eventName, const char *argument);
void servicePendingEvent();
void sendError(const char *code, unsigned long relatedId);
void updateStatusLed();
void signalError();

void setup() {
  pinMode(IR_PIN, INPUT);
  pinMode(PROXIMITY_PIN, INPUT);
  pinMode(RAIN_PIN, INPUT);
  pinMode(MOTOR_IN1_PIN, OUTPUT);
  pinMode(MOTOR_IN2_PIN, OUTPUT);
  pinMode(MOTOR_ENA_PIN, OUTPUT);
  pinMode(STATUS_LED_PIN, OUTPUT);

  diverterServo.attach(SERVO_PIN);
  diverterServo.write(SERVO_NEUTRAL_ANGLE);
  conveyorControl(false); // Always boot with the motor stopped.

  Serial.begin(SERIAL_BAUD);
  for (byte i = 0; i < 3; i++) { // Self-test: three LED blinks.
    digitalWrite(STATUS_LED_PIN, HIGH);
    delay(180);
    digitalWrite(STATUS_LED_PIN, LOW);
    delay(180);
  }
  digitalWrite(STATUS_LED_PIN, HIGH); // Solid LED means idle/ready.
  Serial.println(F("HELLO:ARDUINO:1")); // Required SmartSeg v1 handshake.
}

void loop() {
  readSerialLines();
  servicePendingEvent();
  readSensors();

  // Fail open after a missed laptop response: avoid leaving waste/motor jammed.
  if (waitingForClassification && millis() - triggerTime >= CLASSIFY_TIMEOUT_MS) {
    waitingForClassification = false;
    sendError("TIMEOUT", 0);
    conveyorControl(true);
    signalError();
  }
  updateStatusLed();
}

void readSensors() {
  bool irPresent = (digitalRead(IR_PIN) == (IR_ACTIVE_HIGH ? HIGH : LOW));
  // Rising edge into the detection state starts one cycle only.
  if (irPresent && !previousIrPresent && !waitingForClassification && sessionReady) {
    int proximity = analogRead(PROXIMITY_PIN);
    int rain = analogRead(RAIN_PIN);
    char context[40];
    // Prompt 2 sensor-fusion payload. The laptop parser accepts this combined form.
    snprintf(context, sizeof(context), "PROX=%d,RAIN=%d", proximity, rain);
    conveyorControl(false);
    waitingForClassification = true;
    triggerTime = millis();
    queueEvent("IR_TRIGGERED", context);
  }
  previousIrPresent = irPresent;
}

void readSerialLines() {
  while (Serial.available() > 0) {
    char incoming = (char)Serial.read();
    if (incoming == '\r') continue;
    if (incoming == '\n') {
      if (lineOverflow) {
        sendError("FRAME", 0);
      } else if (lineLength > 0) {
        lineBuffer[lineLength] = '\0';
        handleSerialCommand(lineBuffer);
      }
      lineLength = 0;
      lineOverflow = false;
    } else if (lineLength < sizeof(lineBuffer) - 1) {
      lineBuffer[lineLength++] = incoming;
    } else {
      lineOverflow = true;
    }
  }
}

void handleSerialCommand(char *line) {
  // Handshake is neither an event nor a correlated command.
  if (strcmp(line, "HELLO:LAPTOP:1") == 0) {
    sessionReady = true;
    queueEvent("CONVEYOR_READY", NULL);
    return;
  }

  if (strncmp(line, "ACK:", 4) == 0) {
    unsigned long ackId = strtoul(line + 4, NULL, 10);
    if (pendingEvent && ackId == pendingEventId) pendingEvent = false;
    return;
  }

  // Normal SmartSeg v1 form: CMD:<positive-id>:<command>[:argument]
  unsigned long commandId = 0;
  char *command = NULL;
  char *argument = NULL;
  bool correlated = false;
  if (strncmp(line, "CMD:", 4) == 0) {
    char *save = NULL;
    strtok_r(line, ":", &save); // CMD
    char *idText = strtok_r(NULL, ":", &save);
    command = strtok_r(NULL, ":", &save);
    argument = strtok_r(NULL, ":", &save);
    if (!idText || !command || strtoul(idText, NULL, 10) == 0) {
      sendError("FRAME", 0);
      return;
    }
    commandId = strtoul(idText, NULL, 10);
    correlated = true;
  } else {
    // Bench-only convenience: Serial Monitor can send CLASSIFY:PLASTIC directly.
    char *save = NULL;
    command = strtok_r(line, ":", &save);
    argument = strtok_r(NULL, ":", &save);
  }

  if (correlated) {
    if (!sessionReady) {
      sendError("NOT_READY", commandId);
      return;
    }
    if (commandId == lastCommandId && millis() - lastCommandAt < DUPLICATE_WINDOW_MS) {
      Serial.print(F("ACK:")); Serial.println(commandId);
      return; // Deduplicated retransmission: never move servo/motor twice.
    }
    Serial.print(F("ACK:")); Serial.println(commandId);
    lastCommandId = commandId;
    lastCommandAt = millis();
  }

  if (!command) {
    sendError("UNKNOWN_CMD", commandId);
  } else if (strcmp(command, "CONVEYOR_START") == 0 && argument == NULL) {
    conveyorControl(true);
  } else if (strcmp(command, "CONVEYOR_STOP") == 0 && argument == NULL) {
    conveyorControl(false);
  } else if (strcmp(command, "CLASSIFY") == 0 && argument != NULL) {
    if (!waitingForClassification && correlated) {
      sendError("BUSY", commandId);
      return;
    }
    if (strcmp(argument, "PLASTIC") && strcmp(argument, "ORGANIC") &&
        strcmp(argument, "METAL") && strcmp(argument, "OTHER")) {
      sendError("UNKNOWN_CMD", commandId);
      return;
    }
    moveServoToCategory(argument);
  } else {
    sendError("UNKNOWN_CMD", commandId);
  }
}

void moveServoToCategory(const char *category) {
  int targetAngle = OTHER_ANGLE;
  if (strcmp(category, "PLASTIC") == 0) targetAngle = PLASTIC_ANGLE;
  else if (strcmp(category, "ORGANIC") == 0) targetAngle = ORGANIC_ANGLE;
  else if (strcmp(category, "METAL") == 0) targetAngle = METAL_ANGLE;

  diverterServo.write(targetAngle);
  delay(1200); // Enough time for a light item to leave the diverter gate.
  diverterServo.write(SERVO_NEUTRAL_ANGLE);
  delay(400);
  waitingForClassification = false;
  conveyorControl(true);
  delay(700);  // Clear the item from the IR sensor before accepting another cycle.
  conveyorControl(false);
  queueEvent("SERVO_DONE", category);
}

void conveyorControl(bool run) {
  if (run) {
    digitalWrite(MOTOR_IN1_PIN, HIGH);
    digitalWrite(MOTOR_IN2_PIN, LOW);
    digitalWrite(MOTOR_ENA_PIN, HIGH);
  } else {
    digitalWrite(MOTOR_IN1_PIN, LOW);
    digitalWrite(MOTOR_IN2_PIN, LOW);
    digitalWrite(MOTOR_ENA_PIN, LOW);
  }
}

void queueEvent(const char *eventName, const char *argument) {
  if (pendingEvent) {
    // There should only be one outstanding protocol event; retain safety over noise.
    sendError("BUSY", 0);
    return;
  }
  pendingEventId = nextEventId++;
  if (argument) snprintf(pendingEventFrame, sizeof(pendingEventFrame), "EVT:%lu:%s:%s", pendingEventId, eventName, argument);
  else snprintf(pendingEventFrame, sizeof(pendingEventFrame), "EVT:%lu:%s", pendingEventId, eventName);
  pendingEvent = true;
  pendingEventSends = 0;
  pendingEventSentAt = 0; // servicePendingEvent sends immediately.
}

void servicePendingEvent() {
  if (!pendingEvent) return;
  unsigned long now = millis();
  if (pendingEventSentAt != 0 && now - pendingEventSentAt < ACK_TIMEOUT_MS) return;
  if (pendingEventSends >= MAX_EVENT_SENDS) {
    pendingEvent = false;
    sendError("LINK", pendingEventId);
    conveyorControl(false);
    signalError();
    return;
  }
  Serial.println(pendingEventFrame);
  pendingEventSends++;
  pendingEventSentAt = now;
}

void sendError(const char *code, unsigned long relatedId) {
  Serial.print(F("ERROR:"));
  Serial.print(code);
  if (relatedId > 0) {
    Serial.print(':');
    Serial.print(relatedId);
  }
  Serial.println();
  signalError();
}

void updateStatusLed() {
  unsigned long now = millis();
  if (errorTogglesRemaining > 0) {
    if (now - ledLastToggle >= 350) {
      ledLastToggle = now;
      ledState = !ledState;
      digitalWrite(STATUS_LED_PIN, ledState);
      errorTogglesRemaining--;
    }
  } else if (waitingForClassification) {
    if (now - ledLastToggle >= 120) {
      ledLastToggle = now;
      ledState = !ledState;
      digitalWrite(STATUS_LED_PIN, ledState);
    }
  } else {
    ledState = true;
    digitalWrite(STATUS_LED_PIN, HIGH);
  }
}

void signalError() {
  errorTogglesRemaining = 6; // Three slow off/on blink cycles.
  ledLastToggle = millis();
  ledState = true;
}
