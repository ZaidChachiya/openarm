# OpenArm: Gesture-Controlled Robotic Arm 🤖🖐️

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![MediaPipe](https://img.shields.io/badge/MediaPipe-Vision-orange)](https://developers.google.com/mediapipe)
[![CoppeliaSim](https://img.shields.io/badge/CoppeliaSim-ZMQ_API-green)](https://www.coppeliarobotics.com/)

**OpenArm** is a low-cost, 4-DOF (Degrees of Freedom) gesture-controlled robotic manipulator built from scratch. It demonstrates intuitive human–robot interaction using monocular vision (a standard webcam) to control a physical robotic arm in real-time.


---

## 📖 Table of Contents
- [About the Project](#about-the-project)
-[System Architecture](#system-architecture)
- [Hardware Setup](#hardware-setup)
- [Software Scripts Overview](#software-scripts-overview)
- [Installation & Setup](#installation--setup)
- [How to Use](#how-to-use)
- [Video Demonstration](#video-demonstration)
- [Safety & Constraints](#safety--constraints)

---

## 🎯 About the Project
Instead of using complex joysticks or pre-programmed sequences, OpenArm uses wearable-free, IMU-free **computer vision** to map the user's hand motions directly to the robotic arm. 

1. **Hand Tracking:** Google's MediaPipe detects the user's hand and palm centroid.
2. **Depth Estimation:** A clever monocular depth estimation technique calculates the Z-axis (forward/backward) by measuring the pixel distance between the index and pinky finger bases.
3. **Inverse Kinematics (IK):** The 3D hand coordinates are sent to **CoppeliaSim** (a robotics simulator) functioning as a background IK solver to calculate the required joint angles.
4. **Hardware Execution:** The computed joint angles are sent over Serial to an Arduino, which actuates high-torque servos and a DC gripper.

---

## 🧠 System Architecture

```text
[ Webcam ] ➔ (Python/MediaPipe) Extract 3D Palm Coordinates & Gesture
                                      │
                                      ▼
[ CoppeliaSim ] ➔ Computes Inverse Kinematics (IK) for 4 Joints
                                      │
                                      ▼
[ Arduino ] ➔ (Firmware) Translates angles to PWM signals
                                      │
                                      ▼
[ Hardware ] ➔ Actuates Base, Shoulder, Elbow, Wrist Servos & Gripper
```

---

## ⚙️ Hardware Setup

### Mechanical Components
* **Base Plate, Mounts & Joints:** Modular 3D-printed (PLA/ABS) and Aluminium (6061-T6) brackets.
* **Links:** Lightweight Carbon-fibre tubes (20-30mm OD) for shoulder and forearm.

### Electronics & Actuation
* **Controller:** Arduino (Uno/Nano/Mega).
* **M1 (Base):** 80 kg-cm High-torque Servo (powered via 6–8.4V Buck Converter).
* **M2 (Shoulder):** 60 kg-cm Servo (powered via 6–8.4V Buck Converter).
* **M3 (Elbow & Wrist):** 2x 20 kg-cm Medium-torque Servos (powered via 5–6.8V Buck Converter).
* **M5 (Gripper):** DC Geared Motor controlled via an **L298N Motor Driver**.
* **Power Supply:** 12V High-Current SMPS powering the buck converters and a cooling fan. *(Note: Common ground across all components is mandatory).*

---

## 📂 Software Scripts Overview

The repository contains modular Python scripts for different testing and operational modes:

| Script | Description |
| :--- | :--- |
| `gesture.py` | **Main operation script.** Uses webcam + MediaPipe to track hand position and open/close gestures. Interfaces with CoppeliaSim for IK and sends serial commands to the Arduino. |
| `openarm.py` | **Keyboard Teleoperation.** Allows you to manually drive the physical arm using Pygame inputs (`W/A/S/D/Q/E` for X/Y/Z translation, `O/P` for gripper). |
| `coppeliaAPI.py` | **Simulation-Only Test.** Connects exclusively to CoppeliaSim. Great for testing workspace constraints and IK behavior using keyboard inputs without connecting the physical robot. |
| `servocontrol.py` | **Hardware Debugging.** A lightweight CLI interface to send raw Serial commands (e.g., `S 90 120 150 180` for joint angles or `MD 1` for motor direction) directly to the Arduino. |

---

## 🛠️ Installation & Setup

### 1. Prerequisites
* Python 3.8+
*[CoppeliaSim](https://www.coppeliarobotics.com/downloads) installed on your system.
* Arduino IDE (to upload the receiving firmware to your microcontroller).

### 2. Python Dependencies
Clone this repository and install the required Python packages:
```bash
git clone https://github.com/yourusername/OpenArm.git
cd OpenArm
pip install opencv-python mediapipe pyserial pygame coppeliasim-zmqremoteapi-client
```

### 3. Linux Serial Port Permissions
If you are on Linux, ensure you have permission to read/write to the Arduino serial port (usually `/dev/ttyACM0`):
```bash
sudo usermod -a -G dialout $USER
```
*(Log out and log back in for the changes to take effect).*

### 4. CoppeliaSim Setup
1. Open CoppeliaSim.
2. Load the OpenArm scene file (`.ttt` file containing the `/OpenArm` hierarchy).
3. Ensure the **ZMQ Remote API** is enabled in CoppeliaSim.

---

## 🚀 How to Use

### Mode A: Full Gesture Control (Webcam ➔ Sim ➔ Real Robot)
1. Ensure the Arduino is plugged in and CoppeliaSim is running the OpenArm scene.
2. Run the gesture script:
   ```bash
   python gesture.py
   ```
3. Show your **Left Hand** to the camera:
   * **Move hand up/down/left/right/forward/backward** to move the robotic arm in 3D space.
   * **Open Palm:** Opens the gripper.
   * **Closed Fist:** Closes the gripper.
4. Press `q` to toggle control ENABLED/DISABLED. Press `ESC` to quit.

### Mode B: Keyboard Teleoperation
To control the physical arm via keyboard instead of webcam:
```bash
python openarm.py
```
* **W / S**: Move Forward / Backward (+Y / -Y)
* **A / D**: Move Left / Right (-X / +X)
* **Q / E**: Move Up / Down (+Z / -Z)
* **O / P**: Open / Close Gripper

### Mode C: Hardware Calibration/Testing
To test your servos directly without launching CoppeliaSim:
```bash
python servocontrol.py
```
Type commands like `S 90 90 90 90` to set servos, or `MD 1` / `MD 2` to test the gripper motor.

---

## 🎥 Output Video Demonstration

You can view the output videos demonstrating the OpenArm in action here:

[**View Demo Video Folder on Google Drive**](https://drive.google.com/drive/folders/1fj4Zdd7q7hfHtoaU4wSkX2pFJES7Fx8f?usp=sharing)
---

## ⚠️ Safety & Constraints

To prevent the arm from damaging itself or its surroundings, **software-level constraints** are mapped in the Python scripts (`clamp_to_constraints` function):
* **Floor Clamping:** `Z >= 0` ensures the end-effector never attempts to dig into the table.
* **Spherical Boundary:** The arm's workspace is restricted to a hemisphere of radius `0.5m` centered at `(0.011, -0.00183, 0.131)`. If the target exceeds this radius, the coordinates smoothly slide along the surface of the bounding sphere.

**Hardware Safety:** Always ensure high-torque servos (M1/M2) and the microcontroller are powered by *separate* regulated buck converters to prevent voltage drops from browning out the logic board.

---
