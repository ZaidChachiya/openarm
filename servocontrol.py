import serial
import time
import sys
import os

# --- Configuration ---
ARDUINO_PORT = '/dev/ttyACM0'  # Update this as needed
BAUD_RATE = 9600
# ---------------------

def connect_arduino():
    print(f"Connecting to Arduino on {ARDUINO_PORT} @ {BAUD_RATE} baud...")
    try:
        ser = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)
        print("✅ Connected successfully!\n")
        return ser
    except serial.SerialException as e:
        print(f"❌ Serial connection failed: {e}")
        sys.exit(1)

def send_command(ser, command):
    try:
        ser.write((command.strip() + "\n").encode('utf-8'))
        print(f"➡ Sent: {command}")
    except Exception as e:
        print(f"Error sending command: {e}")

def read_response(ser):
    while ser.in_waiting:
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        if line:
            print(f"⬅ Arduino: {line}")

def main():
    # Optional: Check if user has permission for serial port
    if not os.access(ARDUINO_PORT, os.W_OK):
        print(f"⚠ Permission denied for {ARDUINO_PORT}.")
        print("Run this first:")
        print(f"  sudo usermod -a -G dialout {os.getlogin()}")
        print("Then log out and back in.")
        sys.exit(1)

    ser = connect_arduino()
    print("=== Robotic Arm Python Interface (Linux) ===")
    print("Examples:")
    print("  S 90 120 150 180  -> Move all servos smoothly")
    print("  A 45              -> Move servo1 to 45°")
    print("  MD 1              -> Motor forward")
    print("  M 200             -> Set motor speed")
    print("  MSTOP             -> Stop motor")
    print("  q                 -> Quit")

    try:
        while True:
            read_response(ser)
            cmd = input("\nEnter command: ").strip()
            if cmd.lower() == 'q':
                break
            send_command(ser, cmd)
            time.sleep(0.2)
            read_response(ser)
    except KeyboardInterrupt:
        print("\nUser stopped program.")
    finally:
        if ser.is_open:
            ser.close()
            print("Serial connection closed.")

if __name__ == "__main__":
    main()
