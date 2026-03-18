#!/usr/bin/env python3
import serial
import time
import sys
import os
import math
import pygame
from coppeliasim_zmqremoteapi_client import RemoteAPIClient

# ------------------- CONFIG -------------------
ARDUINO_PORT = '/dev/ttyACM0'
BAUD_RATE = 9600
SPHERE_CENTER = (0.011, -0.00183, 0.131)
SPHERE_RADIUS = 0.5
MOVE_SPEED = 0.0005
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

    # --- Connect Devices ---
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

    # --- Init pygame for control ---
    pygame.init()
    screen = pygame.display.set_mode((1, 1), pygame.NOFRAME)
    clock = pygame.time.Clock()

    print("\n=== OpenArm Control Interface ===")
    print("Keys: W/A/S/D/Q/E move dummy | ESC quits")
    print("Auto-syncs servo data to Arduino\n")

    loop_count = 0
    motor_dir = 0
    wp_index = 0
    waypoints = [[2],[-0.15,0.0,0.4],[1],[-0.15,0.15,0.4],[-0.13,0.13,0.06],[-0.14,0.14,0.025],[2],[-0.15,0.15,0.4],[-0.15,0.0,0.4],[-0.15,-0.15,0.4],[-0.14,-0.14,0.025],[1],[-0.13,-0.13,0.06],[-0.15,-0.15,0.4],[-0.15,0.0,0.4]]
    running = True
    while running:
        pygame.event.pump()
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False

        #TELEOP
        keys = pygame.key.get_pressed()
        dx = dy = dz = 0
        motor_dir = 0
        if keys[pygame.K_w]: dy += MOVE_SPEED
        if keys[pygame.K_s]: dy -= MOVE_SPEED
        if keys[pygame.K_a]: dx -= MOVE_SPEED
        if keys[pygame.K_d]: dx += MOVE_SPEED
        if keys[pygame.K_q]: dz += MOVE_SPEED
        if keys[pygame.K_e]: dz -= MOVE_SPEED
        if keys[pygame.K_o]: motor_dir = 1
        if keys[pygame.K_p]: motor_dir = 2

        if dx or dy or dz:
            pos = [pos[0]+dx, pos[1]+dy, pos[2]+dz]
            pos = clamp_to_constraints(pos)
            sim.setObjectPosition(dummy, -1, pos)

        # wp = waypoints[wp_index]
        # if len(wp)>1:
        #     motor_dir = 0
        #     sl_time = 5
        #     sim.setObjectPosition(dummy, -1, wp)
        # else:
        #     sl_time = 8
        #     if wp_index == 0:
        #         sl_time = 10
        #     motor_dir = wp[0]
        # print("==============",wp_index)
        # wp_index+=1

        # Get joint angles and convert for Arduino (degrees + offsets)
        base_ang = math.degrees(sim.getJointPosition(base))
        shoulder_ang = math.degrees(sim.getJointPosition(shoulder)) + 90
        elbow_ang = int((math.degrees(sim.getJointPosition(elbow)) + 250)*180/270)
        wrist_ang = int((math.degrees(sim.getJointPosition(wrist)) + 120)*180/270)

        # Periodically send to Arduino
        loop_count += 1
        if loop_count % 10 == 0:
            cmd = f"S {base_ang:.0f} {shoulder_ang:.0f} {elbow_ang:.0f} {wrist_ang:.0f}"
            send_command(ser, cmd)
            read_arduino(ser)
            # print(f"➡ Sent: {cmd}")
            # print(f"Dummy: ({pos[0]:.3f}, {pos[1]:.3f}, {pos[2]:.3f})")
            # print("-" * 60)
            cmd = f"MD {motor_dir:.0f}"
            send_command(ser, cmd)
            read_arduino(ser)
            # print(f"➡ Sent: {cmd}")
            # print("-" * 60)
            # time.sleep(sl_time)
            client.step()
            clock.tick(60)

    # --- Cleanup ---
    print("Shutting down...")
    try:
        sim.stopSimulation()
    except:
        pass
    if ser.is_open:
        ser.close()
    pygame.quit()
    print("✅ Closed cleanly.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProgram interrupted by user.")
