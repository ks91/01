# Hexapod Direct Control Notes

This directory provides a direct Python control interface for the Freenove Big Hexapod.

## Important Notes
- Call `HexapodDevice.connect()` first. It starts the control thread and camera stream.
- Use `hexapod.stop()` to stop motion immediately. Movement commands are continuous by design.
- Toggle servo power with `hexapod.servopower(True/False)` before and after work.
- `led_mode(2-5)` runs looped effects. Always stop them with `led_mode(0)`.
- `ball_start()` enters an auto-tracking loop. Always end with `ball_stop()`.
- Use `camera_capture("image.jpg")` to save a still image for external vision processing.
- `sonic()` returns distance only when the head faces the target.
- `power()` returns battery voltage. Do not operate at low voltage.
- Manual per-leg control is allowed only when the robot is stopped and ball tracking is inactive.

## Configuration Files
- `params.json` selects PCB/PI versions for the LED driver. Update for your hardware.
- `point.txt` stores leg calibration values.

## Calibration Workflow (GUI)
1) Run the legacy GUI calibration tools:
   - Server: `../Freenove_Hexapod/Code/Server/main.py`
   - Client: `../Freenove_Hexapod/Code/Client/Main.py`
2) Adjust leg positions in the GUI and save calibration.
   - This updates `../Freenove_Hexapod/Code/Server/point.txt`.
3) Copy the calibration to the direct-control interface:
   - `cp ../Freenove_Hexapod/Code/Server/point.txt software/hexapod/point.txt`
4) Restart the hexapod process. The new interface will use the updated calibration.

## Per-Leg Control
- Position control (XYZ in the leg coordinate frame):\n
  - `hexapod.set_leg_position(leg_index, x, y, z)`\n
  - `hexapod.set_leg_positions([[x, y, z], ...])` (6 legs)\n
- Servo-angle control (raw servo angles, bypasses calibration transforms):\n
  - `hexapod.set_leg_servo_angles(leg_index, a, b, c)`\n
  - `hexapod.set_leg_servo_angles_all([[a, b, c], ...])` (6 legs)\n
- Joint-angle control (applies calibration transforms, consistent with kinematics):\n
  - `hexapod.set_leg_joint_angles(leg_index, a, b, c)`\n
  - `hexapod.set_leg_joint_angles_all([[a, b, c], ...])` (6 legs)\n
\n
Notes:\n
- Use leg indices 0-5 to match the original server numbering.\n
- Position control uses the calibrated kinematics and respects range checks.\n
- Servo-angle control writes directly to the servo channels.\n
- Joint-angle control applies the same calibration transforms used by gait/pose.\n

## Dependencies
- Requires real hardware (Raspberry Pi, sensors, PCA9685, camera).
- `mpu6050` is vendored under `software/hexapod/mpu6050/`.

## Minimal Example
```python
from Hexapod_Lib import HexapodDevice

hexapod = HexapodDevice()
hexapod.connect()
hexapod.servopower(True)
hexapod.move(gait=1, x=0, y=10, angle=0)
hexapod.stop()
hexapod.servopower(False)
```
