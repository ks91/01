import os
import threading
import time

import cv2
import numpy as np

from .adc import ADC
from .buzzer import Buzzer
from .camera import Camera
from .command import COMMAND as cmd
from .control import Control
from .led import Led
from .Thread import stop_thread
from .ultrasonic import Ultrasonic


class _TrackingPID:
    def __init__(self, p=0.0, i=0.0, d=0.0):
        self.set_point = 0.0
        self.kp = p
        self.ki = i
        self.kd = d
        self.last_error = 0.0
        self.i_error = 0.0
        self.i_saturation = 10.0

    def compute(self, feedback_val):
        error = self.set_point - feedback_val
        p_error = self.kp * error
        self.i_error += error
        d_error = self.kd * (error - self.last_error)
        if self.i_error < -self.i_saturation:
            self.i_error = -self.i_saturation
        elif self.i_error > self.i_saturation:
            self.i_error = self.i_saturation
        output = p_error + (self.ki * self.i_error) + d_error
        self.last_error = error
        return -output


class HexapodDevice:
    _LEG_CHANNELS = [
        (15, 14, 13),  # leg 0
        (12, 11, 10),  # leg 1
        (9, 8, 31),    # leg 2
        (22, 23, 27),  # leg 3
        (19, 20, 21),  # leg 4
        (16, 17, 18),  # leg 5
    ]

    def __init__(self):
        self.control = Control()
        self.led = Led()
        self.adc = ADC()
        self.buzzer = Buzzer()
        self.ultrasonic = Ultrasonic()
        self.camera = Camera()

        self.connected = False
        self.move_speed = 8

        self._led_thread = None
        self._ball_thread = None
        self._ball_stop = threading.Event()
        self._ball_active = False
        self._ball_tracking = False

        self._pid_x = _TrackingPID(p=0.05, i=0.005, d=0.02)
        self._pid_distance = _TrackingPID(p=0.3, i=0.05, d=0.05)
        self._pid_x.set_point = 180
        self._pid_distance.set_point = 60

        self._moving = False

    def connect(self):
        if not self.control.condition_thread.is_alive():
            self.control.condition_thread.start()
        if not self.camera.streaming:
            self.camera.start_stream()
        self.connected = True

    def disconnect(self):
        self.ball_stop()
        self.servopower(False)
        if self.camera.streaming:
            self.camera.stop_stream()
        self.connected = False

    def servopower(self, on):
        if on:
            self.control.servo_power_disable.off()
        else:
            self.control.servo_power_disable.on()

    def speed(self, tempo=8):
        self.move_speed = int(tempo)
        return self.move_speed

    def move(self, gait=1, x=0, y=0, angle=0):
        self._ball_active = False
        self._moving = not (int(x) == 0 and int(y) == 0 and int(angle) == 0)
        cmd_list = [
            cmd.CMD_MOVE,
            str(int(gait)),
            str(int(x)),
            str(int(y)),
            str(int(self.move_speed)),
            str(int(angle)),
        ]
        self.control.command_queue = cmd_list
        self.control.timeout = time.time()

    def stop(self):
        self._moving = False
        self.move(gait=1, x=0, y=0, angle=0)

    def balance(self, on=False):
        state = "1" if on else "0"
        self.control.command_queue = [cmd.CMD_BALANCE, state]
        self.control.timeout = time.time()

    def position(self, x=0, y=0, z=0):
        self.control.command_queue = [cmd.CMD_POSITION, str(int(x)), str(int(y)), str(int(z))]
        self.control.timeout = time.time()

    def attitude(self, roll=0, pitch=0, yaw=0):
        self.control.command_queue = [
            cmd.CMD_ATTITUDE,
            str(int(roll)),
            str(int(pitch)),
            str(int(yaw)),
        ]
        self.control.timeout = time.time()

    def head_vertical(self, angle=90):
        self.control.servo.set_servo_angle(0, int(angle))

    def head_horizontal(self, angle=90):
        self.control.servo.set_servo_angle(1, int(angle))

    def buzzer_on(self):
        self.buzzer.set_state(True)

    def buzzer_off(self):
        self.buzzer.set_state(False)

    def led_mode(self, mode=0):
        self._run_led_command([cmd.CMD_LED_MOD, str(int(mode))])

    def led_color(self, red=255, green=255, blue=255):
        self._run_led_command([
            cmd.CMD_LED,
            str(int(red)),
            str(int(green)),
            str(int(blue)),
        ])

    def _run_led_command(self, data):
        if self._led_thread is not None and self._led_thread.is_alive():
            stop_thread(self._led_thread)
        self._led_thread = threading.Thread(
            target=self.led.process_light_command,
            args=(data,),
            daemon=True,
        )
        self._led_thread.start()

    def camera_capture(self, filename="image.jpg"):
        if not self.camera.streaming:
            self.camera.start_stream()
        frame = self.camera.get_frame()
        frame = self.camera.get_frame()
        if frame:
            with open(filename, "wb") as file:
                file.write(frame)
        return os.path.abspath(filename)

    def sonic(self):
        return self.ultrasonic.get_distance()

    def power(self):
        return self.adc.read_battery_voltage()

    def ball_start(self):
        self.head_vertical(90)
        self.head_horizontal(90)
        self._ball_active = True
        self._ball_tracking = True
        self._ball_stop.clear()
        if self._ball_thread is None or not self._ball_thread.is_alive():
            self._ball_thread = threading.Thread(target=self._ball_tracking_loop, daemon=True)
            self._ball_thread.start()

    def ball_stop(self):
        self._ball_active = False
        self._ball_tracking = False
        self._ball_stop.set()
        if self._ball_thread is not None and self._ball_thread.is_alive():
            self._ball_thread.join(timeout=1.0)
            if self._ball_thread.is_alive():
                stop_thread(self._ball_thread)
        self.stop()

    def ball_state(self):
        if self._ball_active:
            return "ongoing" if self._ball_tracking else "completed"
        return "not tracking"

    def _ball_tracking_loop(self):
        min_radius = 7
        threshold_low = (0, 180, 180)
        threshold_high = (5, 255, 255)

        while not self._ball_stop.is_set():
            frame = self._read_frame()
            if frame is None:
                time.sleep(0.05)
                continue

            img_filter = cv2.GaussianBlur(frame, (3, 3), 0)
            img_filter = cv2.cvtColor(img_filter, cv2.COLOR_BGR2HSV)
            img_binary = cv2.inRange(img_filter, threshold_low, threshold_high)
            img_binary = cv2.dilate(img_binary, None, iterations=1)
            contours = cv2.findContours(
                img_binary.copy(),
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE,
            )[-2]

            center = None
            radius = 0
            if len(contours) > 0:
                contour = max(contours, key=cv2.contourArea)
                ((x, y), radius) = cv2.minEnclosingCircle(contour)
                moments = cv2.moments(contour)
                if moments["m00"] > 0:
                    center = (int(moments["m10"] / moments["m00"]), int(moments["m01"] / moments["m00"]))
                    if radius < min_radius:
                        center = None

            self._ball_tracking = True
            if center is not None:
                distance = round(2700 / (2 * radius))
                angle_out = self._pid_x.compute(center[0])
                step_out = self._pid_distance.compute(distance)
                angle = max(-10, min(10, int(angle_out)))
                step = max(-15, min(15, int(step_out)))
                self.control.command_queue = [
                    cmd.CMD_MOVE,
                    "1",
                    "0",
                    str(step),
                    str(self.move_speed),
                    str(angle),
                ]
                self.control.timeout = time.time()
                if step == 0 and angle == 0:
                    self._ball_tracking = False
            else:
                self.control.command_queue = [
                    cmd.CMD_MOVE,
                    "1",
                    "0",
                    "0",
                    str(self.move_speed),
                    "0",
                ]
                self.control.timeout = time.time()

            time.sleep(0.05)

    def _read_frame(self):
        if not self.camera.streaming:
            self.camera.start_stream()
        frame = self.camera.get_frame()
        if not frame:
            return None
        return cv2.imdecode(np.frombuffer(frame, dtype=np.uint8), cv2.IMREAD_COLOR)

    def _assert_leg_index(self, leg_index):
        if leg_index < 0 or leg_index > 5:
            raise ValueError("leg_index must be in [0, 5]")

    def _ensure_manual_leg_allowed(self):
        if self._moving or self._ball_active:
            raise RuntimeError("Stop motion and ball tracking before manual leg control.")

    def set_leg_position(self, leg_index, x, y, z):
        self._ensure_manual_leg_allowed()
        self._assert_leg_index(leg_index)
        prev = list(self.control.leg_positions[leg_index])
        self.control.leg_positions[leg_index] = [int(x), int(y), int(z)]
        if not self.control.check_point_validity():
            self.control.leg_positions[leg_index] = prev
            raise ValueError("Leg position out of range.")
        self.control.set_leg_angles()

    def set_leg_positions(self, positions):
        self._ensure_manual_leg_allowed()
        if len(positions) != 6:
            raise ValueError("positions must contain 6 items.")
        prev = [list(p) for p in self.control.leg_positions]
        for i, position in enumerate(positions):
            if len(position) != 3:
                self.control.leg_positions = prev
                raise ValueError("Each position must be [x, y, z].")
            self.control.leg_positions[i] = [int(position[0]), int(position[1]), int(position[2])]
        if not self.control.check_point_validity():
            self.control.leg_positions = prev
            raise ValueError("Leg positions out of range.")
        self.control.set_leg_angles()

    def set_leg_servo_angles(self, leg_index, a, b, c):
        self._ensure_manual_leg_allowed()
        self._assert_leg_index(leg_index)
        channels = self._LEG_CHANNELS[leg_index]
        angles = [int(a), int(b), int(c)]
        for channel, angle in zip(channels, angles):
            self.control.servo.set_servo_angle(channel, angle)

    def set_leg_servo_angles_all(self, angles):
        self._ensure_manual_leg_allowed()
        if len(angles) != 6:
            raise ValueError("angles must contain 6 items.")
        for leg_index, leg_angles in enumerate(angles):
            if len(leg_angles) != 3:
                raise ValueError("Each angle entry must be [a, b, c].")
            self.set_leg_servo_angles(leg_index, leg_angles[0], leg_angles[1], leg_angles[2])

    def set_leg_joint_angles(self, leg_index, a, b, c):
        self._ensure_manual_leg_allowed()
        self._assert_leg_index(leg_index)
        servo_angles = self._apply_calibration(leg_index, int(a), int(b), int(c))
        self.set_leg_servo_angles(leg_index, *servo_angles)

    def set_leg_joint_angles_all(self, angles):
        self._ensure_manual_leg_allowed()
        if len(angles) != 6:
            raise ValueError("angles must contain 6 items.")
        for leg_index, leg_angles in enumerate(angles):
            if len(leg_angles) != 3:
                raise ValueError("Each angle entry must be [a, b, c].")
            self.set_leg_joint_angles(leg_index, leg_angles[0], leg_angles[1], leg_angles[2])

    def _apply_calibration(self, leg_index, a, b, c):
        calib = self.control.calibration_angles[leg_index]
        if leg_index < 3:
            adj_a = self.control.restrict_value(a + calib[0], 0, 180)
            adj_b = self.control.restrict_value(90 - (b + calib[1]), 0, 180)
            adj_c = self.control.restrict_value(c + calib[2], 0, 180)
        else:
            adj_a = self.control.restrict_value(a + calib[0], 0, 180)
            adj_b = self.control.restrict_value(90 + b + calib[1], 0, 180)
            adj_c = self.control.restrict_value(180 - (c + calib[2]), 0, 180)
        return [adj_a, adj_b, adj_c]
