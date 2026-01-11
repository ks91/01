# AGENTS.md

## Working agreements

Your users are basically Japanese elementary and junior high school students. They do not understand English and have no knowledge of programming. Please always respond in Japanese, very carefully and kindly, but using casual wording.

This computer is a robot system based on a Raspberry Pi. The system is located under ~/01. 01 is an Open Interpreter application that can interact via voice (running as a poetry process). On this computer, it connects to the robot system via ~/01/software/source/server/livekit/multimodal.py.

## The Robots

The robot is one of the following:

Hexapod: The system is written under ~/01/software/hexapod. It depends on libraries that cannot be used in a poetry process, so interaction with the hexapod system is done via an RPC bridge.

Arm: The system is written in ~/01/software/Arm_Lib.py.

From the contents of multimodal.py, you can tell which type of robot this computer is controlling.

## Creating and Updating Skills

By placing files that represent skills (for example, Python code) under ~/01/software, users can call those skills to make the robot operate.
