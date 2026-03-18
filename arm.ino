/*
  Robotic Arm Controller - SMOOTH MULTI SERVO MOVEMENT + Single Angle Mode
  Works with Python Serial Interface (Linux Compatible)
*/

#include <Servo.h>

#define SERVO1_MIN_US 500
#define SERVO1_MAX_US 2450
#define SERVO2_MIN_US 620
#define SERVO2_MAX_US 1950
#define SERVO3_MIN_US 500
#define SERVO3_MAX_US 2490
#define SERVO4_MIN_US 500
#define SERVO4_MAX_US 2490

#define SERVO1_PIN 6
#define SERVO2_PIN 10
#define SERVO3_PIN 5
#define SERVO4_PIN 9
#define DC_MOTOR_EN 11
#define DC_MOTOR_IN1 12
#define DC_MOTOR_IN2 13

Servo servo1, servo2, servo3, servo4;

int g_servo1Pos = 90;
int g_servo2Pos = 90;
int g_servo3Pos = 90;
int g_servo4Pos = 90;

int g_dcMotorDirection = 0;

String inputString = "";
bool stringComplete = false;

void setup() {
  Serial.begin(9600);
  servo1.attach(SERVO1_PIN, SERVO1_MIN_US, SERVO1_MAX_US);
  servo2.attach(SERVO2_PIN, SERVO2_MIN_US, SERVO2_MAX_US);
  servo3.attach(SERVO3_PIN, SERVO3_MIN_US, SERVO3_MAX_US);
  servo4.attach(SERVO4_PIN, SERVO4_MIN_US, SERVO4_MAX_US);

  pinMode(DC_MOTOR_EN, OUTPUT);
  pinMode(DC_MOTOR_IN1, OUTPUT);
  pinMode(DC_MOTOR_IN2, OUTPUT);

  controlDCMotor(0, 0);

  Serial.println("=== Robotic Arm Controller Ready ===");
  Serial.println("Commands:");
  Serial.println("  S a1 a2 a3 a4 [delay]");
  Serial.println("  A angle (single servo1 test)");
  Serial.println("  MD dir (1=fwd, 2=rev, 0=stop)");
  Serial.println("  M speed (0–255)");
  Serial.println("  MSTOP");
}

void loop() {
  if (stringComplete) {
    processInput(inputString);
    inputString = "";
    stringComplete = false;
  }
}

void serialEvent() {
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    if (inChar == '\n') {
      stringComplete = true;
    } else {
      inputString += inChar;
    }
  }
}

void processInput(String input) {
  input.trim();
  if (input.length() == 0) return;

  if (input.startsWith("S") || input.startsWith("s")) {
    int a1, a2, a3, a4, delayMs = 1;
    int numArgs = sscanf(input.c_str(), "%*s %d %d %d %d %d", &a1, &a2, &a3, &a4, &delayMs);
    if (numArgs < 4) {
      Serial.println("Error: Need 4 angles (S a1 a2 a3 a4 [delay])");
      return;
    }
    moveAllServosSmooth(a1, a2, a3, a4, delayMs);
  }

  else if (input.startsWith("A") || input.startsWith("a")) {
    int angle = input.substring(1).toInt();
    angle = constrain(angle, 0, 180);
    servo1.write(angle);
    g_servo1Pos = angle;
    Serial.print("Servo1 Angle Set to: ");
    Serial.println(angle);
  }

  else if (input.startsWith("MD") || input.startsWith("md")) {
    int dir = input.substring(3).toInt();
    g_dcMotorDirection = dir;
    controlDCMotor(dir, 200);
    Serial.print("Motor dir set to ");
    Serial.println(dir);
  }

  else if (input.startsWith("M ") || input.startsWith("m ")) {
    int speed = input.substring(2).toInt();
    controlDCMotor(g_dcMotorDirection, speed);
    Serial.print("Motor speed set to ");
    Serial.println(speed);
  }

  else if (input.equalsIgnoreCase("MSTOP")) {
    controlDCMotor(0, 0);
    Serial.println("Motor STOP");
  }

  else {
    Serial.print("Unknown command: ");
    Serial.println(input);
  }
}

void moveAllServosSmooth(int t1, int t2, int t3, int t4, int delayMs) {
  t1 = constrain(t1, 0, 180);
  t2 = constrain(180-t2, 0, 180);
  t3 = constrain(180-t3, 0, 180);
  t4 = constrain(t4, 0, 180);
  delayMs = constrain(delayMs, 1, 100);

  int maxDiff = max(max(abs(t1 - g_servo1Pos), abs(t2 - g_servo2Pos)),
                    max(abs(t3 - g_servo3Pos), abs(t4 - g_servo4Pos)));

  for (int i = 0; i <= maxDiff; i++) {
    if (g_servo1Pos != t1) g_servo1Pos += (t1 > g_servo1Pos) ? 1 : -1;
    if (g_servo2Pos != t2) g_servo2Pos += (t2 > g_servo2Pos) ? 1 : -1;
    if (g_servo3Pos != t3) g_servo3Pos += (t3 > g_servo3Pos) ? 1 : -1;
    if (g_servo4Pos != t4) g_servo4Pos += (t4 > g_servo4Pos) ? 1 : -1;

    servo1.write(g_servo1Pos);
    servo2.write(g_servo2Pos);
    servo3.write(g_servo3Pos);
    servo4.write(g_servo4Pos);
    delay(delayMs);
  }
  Serial.println("Servos reached targets.");
}

void controlDCMotor(int dir, int speed) {
  speed = constrain(speed, 0, 255);
  if (dir == 1) {
    digitalWrite(DC_MOTOR_IN1, HIGH);
    digitalWrite(DC_MOTOR_IN2, LOW);
  } else if (dir == 2) {
    digitalWrite(DC_MOTOR_IN1, LOW);
    digitalWrite(DC_MOTOR_IN2, HIGH);
  } else {
    digitalWrite(DC_MOTOR_IN1, LOW);
    digitalWrite(DC_MOTOR_IN2, LOW);
  }
  analogWrite(DC_MOTOR_EN, speed);
}
