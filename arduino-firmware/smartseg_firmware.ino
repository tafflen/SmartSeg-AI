/*
  SmartSeg Arduino Uno - SENSOR ONLY firmware

  Current prototype:
    - IR sensor
    - Proximity sensor
    - Rain-drop sensor
    - USB serial communication with laptop

  NOT USED in this version:
    - Servo motor
    - Stepper motor
    - Stepper motor driver
    - Motor batteries
    - Conveyor control

  The Arduino only detects the waste presence and sends sensor
  readings to the laptop. The laptop performs camera + YOLO
  classification.

  SmartSeg v1 serial protocol:
    Arduino -> HELLO:ARDUINO:1
    Laptop  -> HELLO:LAPTOP:1
    Arduino -> EVT:<id>:SENSOR_READY

    Arduino -> EVT:<id>:IR_TRIGGERED:PROX=<value>,RAIN=<value>

    Laptop  -> ACK:<id>

    Laptop  -> CMD:<id>:CLASSIFY:<category>
    Arduino -> EVT:<id>:SERVO_DONE:<category>

    Laptop  -> CMD:<id>:MANUAL_TRIGGER
    (fires the same IR_TRIGGERED event the IR sensor would,
     using real proximity/rain readings - IR sensor itself
     stays connected and active; this is an additional
     trigger path, not a replacement)

  Supported categories:
    PLASTIC
    ORGANIC
    METAL
    OTHER

  Error frames (protocol-level, not conveyor-specific):
    ERROR:BUSY              - a new event was queued while a
                               previous event was still waiting
                               for ACK
    ERROR:LINK:<id>         - an event was sent MAX_EVENT_SENDS
                               times with no ACK
    ERROR:TIMEOUT           - laptop did not respond to an
                               IR_TRIGGERED event within
                               CLASSIFY_TIMEOUT_MS
    ERROR:FRAME             - malformed line received over serial
    ERROR:NOT_READY:<id>    - CMD received before HELLO:LAPTOP:1
    ERROR:UNKNOWN_CMD:<id>  - unrecognized command or argument

  ------------------------------------------------------------
  FIX LOG (vs. previous version)
  ------------------------------------------------------------
  Bug: readSensors() used to set waitingForClassification = true
  BEFORE knowing whether queueEvent() actually succeeded in
  queuing the IR_TRIGGERED event. If another event (like
  SENSOR_READY) was still pending an ACK at that exact moment,
  queueEvent() would reject the new event with ERROR:BUSY, but
  waitingForClassification stayed stuck at true anyway - since
  no event had actually been sent, the laptop could never
  answer it, guaranteeing an ERROR:TIMEOUT five seconds later.

  Fix: queueEvent() now returns a bool indicating success.
  readSensors() only sets waitingForClassification = true if
  the event was actually queued. It also skips attempting to
  trigger at all while another event is still pending, instead
  of relying on queueEvent() to reject it.
*/

#include <stdlib.h>
#include <string.h>


// ============================================================
// PIN MAP - SENSOR ONLY
// ============================================================

const byte IR_PIN = 2;
const byte PROXIMITY_PIN = 6;
const byte RAIN_PIN = A0;

// Built-in Arduino Uno LED.
// Used only as a status indicator.
const byte STATUS_LED_PIN = 13;


// ============================================================
// SERIAL / PROTOCOL SETTINGS
// ============================================================

const unsigned long SERIAL_BAUD = 115200;

// How long the Arduino waits for the laptop to respond
// after an IR trigger.
const unsigned long CLASSIFY_TIMEOUT_MS = 5000;

// Time between retransmissions of an unacknowledged event.
const unsigned long ACK_TIMEOUT_MS = 1000;

// Maximum number of times an event is transmitted.
const byte MAX_EVENT_SENDS = 3;

// Prevent duplicate commands from being processed repeatedly.
const unsigned long DUPLICATE_WINDOW_MS = 30000;


// ============================================================
// IR SENSOR SETTINGS
// ============================================================

// Confirmed via isolation test: this module reports HIGH
// when an object is detected, LOW when idle.
const bool IR_ACTIVE_HIGH = true;


// ============================================================
// SERIAL BUFFER / STATE
// ============================================================

char lineBuffer[97];
byte lineLength = 0;
bool lineOverflow = false;

bool sessionReady = false;
bool waitingForClassification = false;

bool previousIrPresent = false;

unsigned long triggerTime = 0;
unsigned long nextEventId = 1;


// ============================================================
// PENDING EVENT
// ============================================================

// Only one sensor event is outstanding at a time.

bool pendingEvent = false;

unsigned long pendingEventId = 0;

char pendingEventFrame[97];

byte pendingEventSends = 0;

unsigned long pendingEventSentAt = 0;


// ============================================================
// DUPLICATE COMMAND PROTECTION
// ============================================================

unsigned long lastCommandId = 0;
unsigned long lastCommandAt = 0;


// ============================================================
// STATUS LED
// ============================================================

unsigned long ledLastToggle = 0;

byte errorTogglesRemaining = 0;

bool ledState = true;


// ============================================================
// FUNCTION DECLARATIONS
// ============================================================

void readSensors();

bool attemptTrigger();

void readSerialLines();

void handleSerialCommand(char *line);

bool queueEvent(const char *eventName, const char *argument);

void servicePendingEvent();

void sendError(const char *code, unsigned long relatedId);

void updateStatusLed();

void signalError();


// ============================================================
// SETUP
// ============================================================

void setup() {

  // Sensor inputs
  pinMode(IR_PIN, INPUT);
  pinMode(PROXIMITY_PIN, INPUT);
  pinMode(RAIN_PIN, INPUT);

  // Built-in LED
  pinMode(STATUS_LED_PIN, OUTPUT);

  // Start USB serial communication
  Serial.begin(SERIAL_BAUD);

  // Startup LED self-test:
  // 3 short blinks
  for (byte i = 0; i < 3; i++) {

    digitalWrite(STATUS_LED_PIN, HIGH);
    delay(180);

    digitalWrite(STATUS_LED_PIN, LOW);
    delay(180);
  }

  // Solid LED = Arduino is powered and ready
  digitalWrite(STATUS_LED_PIN, HIGH);

  // Tell laptop that Arduino is alive.
  Serial.println(F("HELLO:ARDUINO:1"));
}


// ============================================================
// MAIN LOOP
// ============================================================

void loop() {

  // Check commands coming from laptop
  readSerialLines();

  // Send/retry pending sensor events
  servicePendingEvent();

  // Read IR + proximity + rain sensors
  readSensors();

  // If laptop does not respond after an IR trigger,
  // cancel the waiting state.
  //
  // IMPORTANT:
  // There is NO conveyor restart here because no motor
  // is connected in this prototype.
  if (
    waitingForClassification &&
    millis() - triggerTime >= CLASSIFY_TIMEOUT_MS
  ) {

    waitingForClassification = false;

    sendError("TIMEOUT", 0);
  }

  // Update built-in LED status
  updateStatusLed();
}


// ============================================================
// SENSOR READING
// ============================================================

/*
  Shared trigger logic.

  Both the automatic IR pin detection AND the manual
  MANUAL_TRIGGER serial command call this same function, so
  they behave identically: same guard conditions, same real
  proximity/rain readings, same event format. The only
  difference between the two trigger sources is WHAT decides
  the moment to call this - a sensor edge, or a keypress
  relayed from the laptop.

  Returns true if a trigger was actually queued.
*/
bool attemptTrigger() {

  // Refuse to trigger while another event (e.g. SENSOR_READY)
  // is still pending an ACK, or while a previous trigger is
  // still awaiting a classification reply, or before the
  // laptop handshake has completed.
  if (
    waitingForClassification ||
    pendingEvent ||
    !sessionReady
  ) {

    return false;
  }

  // Read proximity sensor
  // int proximity = digitalRead(PROXIMITY_PIN);

  // // Read rain sensor
  // int rain = analogRead(RAIN_PIN);
  int proximityDigital = digitalRead(PROXIMITY_PIN);
  int proximity = proximityDigital ? 1023 : 0;

  int rain = analogRead(RAIN_PIN);
    // Build sensor payload
  char context[40];

  snprintf(
    context,
    sizeof(context),
    "PROX=%d,RAIN=%d",
    proximity,
    rain
  );

  // Only mark ourselves as waiting for classification if
  // the event actually got queued successfully.
  bool queued = queueEvent(
    "IR_TRIGGERED",
    context
  );

  if (queued) {

    waitingForClassification = true;

    triggerTime = millis();
  }

  return queued;
}


void readSensors() {

  // Read IR sensor
  bool irPresent =
    (digitalRead(IR_PIN) ==
     (IR_ACTIVE_HIGH ? HIGH : LOW));


  /*
    Detect only the transition:

        NO OBJECT -> OBJECT

    This prevents the Arduino from sending hundreds
    of events while the same object remains in front
    of the IR sensor.

    The IR sensor stays fully wired and functional here -
    this path fires automatically on a real detection, exactly
    as before. It shares attemptTrigger() with the manual
    command path below, so the guard conditions and event
    format are identical either way.
  */

  if (
    irPresent &&
    !previousIrPresent
  ) {

    attemptTrigger();
  }

  // Store current IR state for rising-edge detection
  previousIrPresent = irPresent;
}


// ============================================================
// SERIAL INPUT
// ============================================================

void readSerialLines() {

  while (Serial.available() > 0) {

    char incoming = (char)Serial.read();

    // Ignore carriage return
    if (incoming == '\r') {
      continue;
    }

    // End of line
    if (incoming == '\n') {

      if (lineOverflow) {

        sendError("FRAME", 0);

      }
      else if (lineLength > 0) {

        lineBuffer[lineLength] = '\0';

        handleSerialCommand(lineBuffer);
      }

      // Reset buffer
      lineLength = 0;
      lineOverflow = false;
    }

    // Add character to buffer
    else if (lineLength < sizeof(lineBuffer) - 1) {

      lineBuffer[lineLength++] = incoming;
    }

    // Buffer overflow
    else {

      lineOverflow = true;
    }
  }
}


// ============================================================
// SERIAL COMMAND HANDLER
// ============================================================

void handleSerialCommand(char *line) {

  // ----------------------------------------------------------
  // Laptop handshake
  // ----------------------------------------------------------

  if (strcmp(line, "HELLO:LAPTOP:1") == 0) {

    sessionReady = true;

    // Sensor-only firmware: no conveyor exists, so we tell
    // the laptop the sensor stage is ready, not a conveyor.
    queueEvent("SENSOR_READY", NULL);

    return;
  }


  // ----------------------------------------------------------
  // Event acknowledgement
  // ----------------------------------------------------------

  if (strncmp(line, "ACK:", 4) == 0) {

    unsigned long ackId =
      strtoul(line + 4, NULL, 10);

    if (
      pendingEvent &&
      ackId == pendingEventId
    ) {

      pendingEvent = false;
    }

    return;
  }


  // ----------------------------------------------------------
  // CMD:<id>:<command>[:argument]
  // ----------------------------------------------------------

  unsigned long commandId = 0;

  char *command = NULL;

  char *argument = NULL;

  bool correlated = false;


  if (strncmp(line, "CMD:", 4) == 0) {

    char *save = NULL;

    // CMD
    strtok_r(line, ":", &save);

    // ID
    char *idText =
      strtok_r(NULL, ":", &save);

    // COMMAND
    command =
      strtok_r(NULL, ":", &save);

    // ARGUMENT
    argument =
      strtok_r(NULL, ":", &save);


    // Validate command ID
    if (
      !idText ||
      !command ||
      strtoul(idText, NULL, 10) == 0
    ) {

      sendError("FRAME", 0);

      return;
    }


    commandId =
      strtoul(idText, NULL, 10);

    correlated = true;
  }


  // ----------------------------------------------------------
  // Correlated command handling
  // ----------------------------------------------------------

  if (correlated) {

    // Laptop must perform handshake first
    if (!sessionReady) {

      sendError("NOT_READY", commandId);

      return;
    }


    // Prevent duplicate commands
    if (
      commandId == lastCommandId &&
      millis() - lastCommandAt < DUPLICATE_WINDOW_MS
    ) {

      Serial.print(F("ACK:"));
      Serial.println(commandId);

      return;
    }


    // Acknowledge command
    Serial.print(F("ACK:"));
    Serial.println(commandId);

    lastCommandId = commandId;

    lastCommandAt = millis();
  }


  // ----------------------------------------------------------
  // CLASSIFY command
  // ----------------------------------------------------------

  if (
    command != NULL &&
    strcmp(command, "CLASSIFY") == 0 &&
    argument != NULL
  ) {

    // Validate category
    if (
      strcmp(argument, "PLASTIC") != 0 &&
      strcmp(argument, "ORGANIC") != 0 &&
      strcmp(argument, "METAL") != 0 &&
      strcmp(argument, "OTHER") != 0
    ) {

      sendError("UNKNOWN_CMD", commandId);

      return;
    }


    /*
      SENSOR-ONLY MODE

      The Arduino does NOT:
        - move a servo
        - rotate a stepper
        - start a conveyor
        - control a motor driver

      The laptop has already performed the classification.

      We simply mark this waste cycle as completed.
      "SERVO_DONE" is kept as the completion-event name since
      it just means "classification cycle finished", which is
      still accurate even with no physical servo attached.
    */

    waitingForClassification = false;

    queueEvent(
      "SERVO_DONE",
      argument
    );

    return;
  }


  // ----------------------------------------------------------
  // MANUAL_TRIGGER command
  // ----------------------------------------------------------

  /*
    Lets the laptop fire the exact same event the IR sensor
    would fire, on demand (e.g. an operator pressing Enter
    during a demo). Proximity and rain readings are still
    real, live sensor values - only the "an object arrived"
    moment is manual instead of IR-detected.

    The IR sensor itself is untouched and still fully wired
    and active; this is simply an additional way to reach the
    same attemptTrigger() call.
  */

  if (
    command != NULL &&
    strcmp(command, "MANUAL_TRIGGER") == 0
  ) {

    bool queued = attemptTrigger();

    if (!queued) {

      sendError("NOT_READY", commandId);
    }

    return;
  }


  // ----------------------------------------------------------
  // Conveyor commands
  // ----------------------------------------------------------

  if (
    command != NULL &&
    (
      strcmp(command, "CONVEYOR_START") == 0 ||
      strcmp(command, "CONVEYOR_STOP") == 0
    )
  ) {

    /*
      Motors are NOT connected in this prototype.

      Therefore these commands are intentionally ignored
      after acknowledgement.

      This prevents the Arduino from attempting to control
      any absent motor hardware.
    */

    return;
  }


  // ----------------------------------------------------------
  // Unknown command
  // ----------------------------------------------------------

  sendError(
    "UNKNOWN_CMD",
    commandId
  );
}


// ============================================================
// EVENT QUEUE
// ============================================================

// Returns true if the event was successfully queued, false if
// rejected because another event is still pending an ACK.
bool queueEvent(
  const char *eventName,
  const char *argument
) {

  // Only one event can be waiting for acknowledgement
  if (pendingEvent) {

    sendError("BUSY", 0);

    return false;
  }


  pendingEventId = nextEventId++;


  // Event with argument
  if (argument) {

    snprintf(
      pendingEventFrame,
      sizeof(pendingEventFrame),
      "EVT:%lu:%s:%s",
      pendingEventId,
      eventName,
      argument
    );
  }

  // Event without argument
  else {

    snprintf(
      pendingEventFrame,
      sizeof(pendingEventFrame),
      "EVT:%lu:%s",
      pendingEventId,
      eventName
    );
  }


  pendingEvent = true;

  pendingEventSends = 0;

  // Send immediately on next service cycle
  pendingEventSentAt = 0;

  return true;
}


// ============================================================
// EVENT TRANSMISSION / RETRY
// ============================================================

void servicePendingEvent() {

  if (!pendingEvent) {
    return;
  }


  unsigned long now = millis();


  // Wait for ACK timeout before retrying
  if (
    pendingEventSentAt != 0 &&
    now - pendingEventSentAt < ACK_TIMEOUT_MS
  ) {

    return;
  }


  // Too many failed transmissions
  if (pendingEventSends >= MAX_EVENT_SENDS) {

    pendingEvent = false;

    sendError(
      "LINK",
      pendingEventId
    );

    return;
  }


  // Send event
  Serial.println(pendingEventFrame);

  pendingEventSends++;

  pendingEventSentAt = now;
}


// ============================================================
// ERROR MESSAGE
// ============================================================

void sendError(
  const char *code,
  unsigned long relatedId
) {

  Serial.print(F("ERROR:"));
  Serial.print(code);


  if (relatedId > 0) {

    Serial.print(':');
    Serial.print(relatedId);
  }


  Serial.println();

  signalError();
}


// ============================================================
// STATUS LED
// ============================================================

void updateStatusLed() {

  unsigned long now = millis();


  // Error state
  if (errorTogglesRemaining > 0) {

    if (
      now - ledLastToggle >= 350
    ) {

      ledLastToggle = now;

      ledState = !ledState;

      digitalWrite(
        STATUS_LED_PIN,
        ledState
      );

      errorTogglesRemaining--;
    }
  }


  // Waiting for laptop classification
  else if (waitingForClassification) {

    if (
      now - ledLastToggle >= 120
    ) {

      ledLastToggle = now;

      ledState = !ledState;

      digitalWrite(
        STATUS_LED_PIN,
        ledState
      );
    }
  }


  // Normal idle state
  else {

    ledState = true;

    digitalWrite(
      STATUS_LED_PIN,
      HIGH
    );
  }
}


// ============================================================
// ERROR LED SIGNAL
// ============================================================

void signalError() {

  // 3 slow blink cycles
  errorTogglesRemaining = 6;

  ledLastToggle = millis();

  ledState = true;
}
