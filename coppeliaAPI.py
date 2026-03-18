# Updated code: Dummy path changed to '/OpenArm/target'.
# Added constraints:
# - Z >= 0 (clamp floor).
# - Keep inside sphere of radius 0.5 centered at (0.008, 0.036, 0.131).
#   If new position exceeds, project to sphere surface (slides along boundary).
#   This creates a "hemisphere-like" dome above Z=0 (full sphere clamped by floor).
# Pygame still used for multi-key detection (combinations supported).

import time
import math
from coppeliasim_zmqremoteapi_client import RemoteAPIClient  # ZMQ remote API client
import pygame  # For multi-key state detection

# Optional: Brief pause to ensure server readiness
time.sleep(0.5)

# Connect to CoppeliaSim (default port 23000 for ZMQ; adjust if customized)
client = RemoteAPIClient()

# Enable synchronous mode for real-time control (step the simulation manually)
client.setStepping(True)

# Initialize pygame for input (headless mode)
pygame.init()
# Minimal display to enable events (1x1 pixel, hidden)
screen = pygame.display.set_mode((1, 1), pygame.NOFRAME)
pygame.display.set_caption("CoppeliaSim Controller")  # Optional

# Sphere constraints
cx, cy, cz = 0.008, 0.036, 0.131
r = 0.5

def clamp_to_constraints(pos):
    """Clamp position: Z >= 0, and inside/out on sphere boundary."""
    x, y, z = pos
    
    # Clamp Z floor
    z = max(z, 0)
    
    # Check distance from center
    dx, dy, dz_ = x - cx, y - cy, z - cz
    dist = math.sqrt(dx**2 + dy**2 + dz_**2)
    
    if dist > r:
        # Project to sphere surface: normalize direction and scale to radius
        scale = r / dist
        x = cx + dx * scale
        y = cy + dy * scale
        z = cz + dz_ * scale
        # Re-clamp Z after projection (in case it goes below 0)
        z = max(z, 0)
    
    return [x, y, z]

try:
    sim = client.require('sim')  # Get the 'sim' namespace
    print("Connected to CoppeliaSim ZMQ remote API server")
    
    # Get handles for joints (adjust paths if needed)
    base_joint_handle = sim.getObject('/OpenArm/base_joint')
    shoulder_joint_handle = sim.getObject('/OpenArm/shoulder_joint')
    elbow_joint_handle = sim.getObject('/OpenArm/elbow_joint')
    wrist_joint_handle = sim.getObject('/OpenArm/wrist_joint')
    
    # Get handle for the dummy (updated path)
    dummy_handle = sim.getObject('/OpenArm/target')
    
    print("Handles obtained successfully")
    print("Controls (hold for continuous movement; combinations supported, e.g., W+A for diagonal):")
    print("W: Forward (+Y), S: Backward (-Y)")
    print("A: Left (-X), D: Right (+X)")
    print("Q: Up (+Z), E: Down (-Z)")
    print("ESC: Quit")
    print("Constraints: Z >= 0; inside sphere r=0.5 @ (0.008, 0.036, 0.131) (projects to boundary)")
    print("Speed: 0.01 units/step. Starting loop...")
    
    # Initial position for dummy (get current, clamp to constraints)
    dummy_pos = sim.getObjectPosition(dummy_handle, -1)  # -1 for world reference frame
    x, y, z = clamp_to_constraints(dummy_pos)
    sim.setObjectPosition(dummy_handle, -1, [x, y, z])  # Set clamped initial pos
    move_speed = 0.01  # Adjust for faster/slower movement
    
    clock = pygame.time.Clock()  # For consistent loop rate
    loop_count = 0
    
    running = True
    while running:
        # Pump events to keep pygame responsive
        pygame.event.pump()
        
        # Check for quit events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
        
        # Get current pressed keys for simultaneous detection
        keys = pygame.key.get_pressed()
        
        # Reset movement deltas
        dx, dy, dz = 0, 0, 0
        
        # Handle XY movement (WASD) - supports combinations
        if keys[pygame.K_w]:
            dy += move_speed
        if keys[pygame.K_s]:
            dy -= move_speed
        if keys[pygame.K_a]:
            dx -= move_speed
        if keys[pygame.K_d]:
            dx += move_speed
        
        # Handle Z movement (QE)
        if keys[pygame.K_q]:
            dz += move_speed
        if keys[pygame.K_e]:
            dz -= move_speed
        
        # Only update if any movement
        if dx != 0 or dy != 0 or dz != 0:
            # Tentative new position
            new_x, new_y, new_z = x + dx, y + dy, z + dz
            
            # Clamp to constraints
            clamped_pos = clamp_to_constraints([new_x, new_y, new_z])
            x, y, z = clamped_pos
            
            # Update dummy position in the world
            sim.setObjectPosition(dummy_handle, -1, [x, y, z])
        
        # Continuously get joint positions (convert to degrees, apply offsets for display)
        base_joint_position = math.degrees(sim.getJointPosition(base_joint_handle))
        shoulder_joint_position = math.degrees(sim.getJointPosition(shoulder_joint_handle)) + 135
        elbow_joint_position = math.degrees(sim.getJointPosition(elbow_joint_handle)) + 250
        wrist_joint_position = math.degrees(sim.getJointPosition(wrist_joint_handle)) + 120
        
        # Print updates every 20 frames to reduce spam (adjust for frequency)
        loop_count += 1
        if loop_count % 20 == 0:
            print(f"Base joint: {base_joint_position:.2f}° | Shoulder: {shoulder_joint_position:.2f}° | Elbow: {elbow_joint_position:.2f}° | Wrist: {wrist_joint_position:.2f}°")
            print(f"Dummy pos: ({x:.3f}, {y:.3f}, {z:.3f}) | Movement: Δx={dx:.3f}, Δy={dy:.3f}, Δz={dz:.3f}")
            print("-" * 60)
        
        # Step the simulation forward (essential for synchronous mode and dynamic updates)
        client.step()
        
        # Cap loop rate at 60 FPS for smooth but efficient control
        clock.tick(60)
    
    print("Exiting loop...")

except KeyboardInterrupt:
    print("Interrupted by user")
except Exception as e:
    print(f"Error: {e}")
    print("Common fixes: Verify object paths/names in scene hierarchy, ensure ZMQ add-on is enabled, and load the scene.")

finally:
    # Cleanup: Stop simulation if running, quit pygame
    try:
        sim.stopSimulation()
    except:
        pass
    pygame.quit()

# No explicit disconnect needed; ZMQ handles it on client destruction
print("Program ended")