import cv2
import mediapipe as mp
import math
import numpy as np
import serial
import time
import sys
import os
from coppeliasim_zmqremoteapi_client import RemoteAPIClient

# ------------------- CONFIG -------------------
ARDUINO_PORT = '/dev/ttyACM0'
BAUD_RATE = 9600
SPHERE_CENTER = (0.011, -0.00183, 0.131)
SPHERE_RADIUS = 0.5
MOVE_SPEED = 0.01
# ------------------------------------------------

def connect_arduino():
    print(f"Connecting to Arduino on {ARDUINO_PORT} @ {BAUD_RATE} baud...")
    try:
        ser = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)
        print("✅ Arduino connected!\n")
        return ser
    except serial.SerialException as e:
        print(f"❌ Serial connection failed: {e}")
        sys.exit(1)

def send_command(ser, command):
    try:
        ser.write((command.strip() + "\n").encode('utf-8'))
    except Exception as e:
        print(f"Error sending to Arduino: {e}")

def read_arduino(ser):
    while ser.in_waiting:
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        if line:
            print(f"⬅ Arduino: {line}")

def clamp_to_constraints(pos):
    """Clamp to Z≥0 and within sphere radius."""
    cx, cy, cz = SPHERE_CENTER
    r = SPHERE_RADIUS
    x, y, z = pos
    z = max(z, 0)
    dx, dy, dz_ = x - cx, y - cy, z - cz
    dist = math.sqrt(dx**2 + dy**2 + dz_**2)
    if dist > r:
        scale = r / dist
        x, y, z = cx + dx * scale, cy + dy * scale, cz + dz_ * scale
        z = max(z, 0)
    return [x, y, z]

def connect_coppelia():
    print("Connecting to CoppeliaSim ZMQ remote API...")
    client = RemoteAPIClient()
    client.setStepping(True)
    sim = client.require('sim')
    print("✅ Connected to CoppeliaSim")
    return client, sim

def main():
    # --- Check Arduino access ---
    if not os.access(ARDUINO_PORT, os.W_OK):
        print(f"⚠ Permission denied for {ARDUINO_PORT}. Run:")
        print(f"  sudo usermod -a -G dialout {os.getlogin()}")
        print("Then log out and back in.")
        sys.exit(1)

    # # --- Connect Devices ---
    ser = connect_arduino()
    client, sim = connect_coppelia()

    # --- Get handles ---
    base = sim.getObject('/OpenArm/base_joint')
    shoulder = sim.getObject('/OpenArm/shoulder_joint')
    elbow = sim.getObject('/OpenArm/elbow_joint')
    wrist = sim.getObject('/OpenArm/wrist_joint')
    dummy = sim.getObject('/OpenArm/target')

    # --- Initialize position ---
    pos = clamp_to_constraints(sim.getObjectPosition(dummy, -1))
    sim.setObjectPosition(dummy, -1, pos)

    # Initialize MediaPipe Hands
    mp_hands = mp.solutions.hands
    mp_drawing = mp.solutions.drawing_utils
    mp_drawing_styles = mp.solutions.drawing_styles

    # Palm-specific landmarks for center calculation
    PALM_LANDMARKS = [0, 5, 9, 13, 17]  # Wrist and finger bases
    PALM_CONNECTIONS = [(0, 1), (0, 5), (5, 9), (9, 13), (13, 17)]  # Palm outline connections

    # Assumptions for distance estimation
    FOCAL_LENGTH = 550  # Approximate focal length in pixels for typical webcam (640x480, ~60° FOV)
    AVERAGE_PALM_WIDTH_MM = 80  # Average adult palm width in mm (distance between index and pinky bases)
    AVERAGE_PALM_WIDTH_M = AVERAGE_PALM_WIDTH_MM / 1000  # Convert to meters

    # For webcam input
    # loop_count = 0
    cap = cv2.VideoCapture(0)
    motor_dir = 0
    old_cx = None
    old_cy = None
    old_estimated_distance_cm = None
    cx = 0
    cy = 0
    estimated_distance_cm = 0
    palm_open = False
    en = 1
    print("DISABLED")

    with mp_hands.Hands(
        model_complexity=0,
        min_detection_confidence=0.3,
        min_tracking_confidence=0.1) as hands:
        while cap.isOpened():
            success, image = cap.read()
            if not success:
                print("Ignoring empty camera frame.")
                continue

            # To improve performance, optionally mark the image as not writeable to pass by reference.
            image.flags.writeable = False
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            results = hands.process(image)

            # Draw the hand annotations on the image.
            image.flags.writeable = True
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            
            h, w, _ = image.shape  # Image dimensions
            blank=np.zeros((h,w,3),np.uint8)
            
            if results.multi_hand_landmarks and results.multi_handedness and en==-1:
                for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
                    # Only process the right hand
                    if handedness.classification[0].label == 'Left':
                        # Draw palm connections and landmarks
                        mp_drawing.draw_landmarks(
                            blank,
                            hand_landmarks,
                            PALM_CONNECTIONS,
                            mp_drawing_styles.get_default_hand_landmarks_style(),
                            mp_drawing_styles.get_default_hand_connections_style())
                        
                        # Extract palm landmarks coordinates
                        palm_points = []
                        for idx in PALM_LANDMARKS:
                            landmark = hand_landmarks.landmark[idx]
                            x = int(landmark.x * w)
                            y = int(landmark.y * h)
                            palm_points.append((x, y))
                        index_tip = hand_landmarks.landmark[12].y
                        index_base = hand_landmarks.landmark[9].y
                        palm_open = False
                        motor_dir = 2
                        if index_tip<index_base:
                            palm_open = True
                            motor_dir = 1
                        # cv2.circle(blank, index_tip, 8, (0, 255, 0), -1)  # Blue circle for center
                        # cv2.circle(blank, index_base, 8, (0, 0, 255), -1)  # Blue circle for center
                        
                        # Calculate palm center (average of palm landmarks)
                        cx = int(sum(p[0] for p in palm_points) / len(palm_points))
                        cy = int(sum(p[1] for p in palm_points) / len(palm_points))
                        
                        # Draw center point
                        cv2.circle(blank, (cx, cy), 8, (255, 0, 0), -1)  # Blue circle for center
                        # print(hand_landmarks)
                        # Estimate distance using palm width (landmarks 5 and 17: index to pinky base)
                        idx_base = palm_points[1]  # Landmark 5
                        pinky_base = palm_points[4]  # Landmark 17
                        pixel_width = math.hypot(pinky_base[0] - idx_base[0], pinky_base[1] - idx_base[1])
                        
                        if pixel_width > 0:
                            estimated_distance_m = (FOCAL_LENGTH * AVERAGE_PALM_WIDTH_M) / pixel_width
                            estimated_distance_cm = estimated_distance_m * 100
                            cx = 0.5 - cx/w
                            cy = 0.5 - cy/(2*h)
                            if estimated_distance_cm<50:
                                estimated_distance_cm = 50
                            elif estimated_distance_cm>250:
                                estimated_distance_cm = 250
                            estimated_distance_cm = 0.5 - (estimated_distance_cm-50)/200
                            if estimated_distance_cm<0.2:
                                estimated_distance_cm = 0.2
                            if old_cx is None:
                                old_cx = cx
                            if old_cy is None:
                                old_cy = cy
                            if old_estimated_distance_cm is None:
                                old_estimated_distance_cm = estimated_distance_cm
                            smoothen = 0.05
                            cx = smoothen*cx+(1-smoothen)*old_cx
                            cy = smoothen*cy+(1-smoothen)*old_cy
                            estimated_distance_cm = smoothen*estimated_distance_cm+(1-smoothen)*old_estimated_distance_cm
                            old_cx = cx
                            old_cy = cy
                            old_estimated_distance_cm = estimated_distance_cm
                            pos = clamp_to_constraints([cx,estimated_distance_cm,cy])
                            sim.setObjectPosition(dummy, -1, pos)
                            # Get joint angles and convert for Arduino (degrees + offsets)
                            base_ang = math.degrees(sim.getJointPosition(base))
                            shoulder_ang = math.degrees(sim.getJointPosition(shoulder)) + 90
                            elbow_ang = int((math.degrees(sim.getJointPosition(elbow)) + 250)*180/270)
                            wrist_ang = int((math.degrees(sim.getJointPosition(wrist)) + 120)*180/270)

                            # Periodically send to Arduino
                            # loop_count += 1
                            # if loop_count % 10 == 0:
                            cmd = f"S {base_ang:.0f} {shoulder_ang:.0f} {elbow_ang:.0f} {wrist_ang:.0f}"
                            send_command(ser, cmd)
                            read_arduino(ser)
                            print(f"➡ Sent: {cmd}")
                            print(f"Dummy: ({pos[0]:.3f}, {pos[1]:.3f}, {pos[2]:.3f})")
                            print("-" * 60)
                            cmd = f"MD {motor_dir:.0f}"
                            send_command(ser, cmd)
                            read_arduino(ser)
                            print(f"➡ Sent: {cmd}")
                            print("-" * 60)
                            client.step()
                        
                        # # Optionally draw palm width line
                        # cv2.line(blank, idx_base, pinky_base, (0, 0, 255), 2)  # Red line for width
            blank = cv2.putText(cv2.flip(blank, 1), f"({round(cx,3)}, {round(estimated_distance_cm,3)}, {round(cy,3)})",(100,200),cv2.FONT_ITALIC ,1,(255,255,255),2)
            blank = cv2.putText(blank, f"Palm Open: {palm_open}",(100,400),cv2.FONT_ITALIC ,1,(255,255,255),2)
            # Flip the image horizontally for a selfie-view display.
            cv2.imshow('Right Hand Palm Detection with Center & Distance', blank)
            if cv2.waitKey(5)==ord('q'):
                en = -1*en
                if en==-1:
                    print("ENABLED")
                else:
                    print("DISABLED")
            if cv2.waitKey(5) & 0xFF == 27:
                break
    cap.release()
    # --- Cleanup ---
    print("Shutting down...")
    try:
        sim.stopSimulation()
    except:
        pass
    if ser.is_open:
        ser.close()
    print("✅ Closed cleanly.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProgram interrupted by user.")