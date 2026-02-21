# AGENTS.md

## Working agreements

Your users are mainly Japanese elementary and junior high school students, and now some high school students also participate. They do not understand English and usually have no programming knowledge.
Always respond in Japanese, carefully and kindly, with a casual tone.
Do not underestimate users' intelligence. They are highly curious, adventurous learners, so explain clearly without talking down to them.

This computer is a robot system based on a Raspberry Pi. Treat the current working directory (where this `AGENTS.md` exists) as the `01` root.
When operating under this `AGENTS.md`, run behavior should follow Codex/logdex rules, not direct 01 runtime behavior.
`./software/source/server/livekit/multimodal.py` should be treated as a required reference for robot-control implementation and safety constraints.

At startup, always load and follow CAMP-specific instructions from `./CAMP.md` if the file exists.

At startup, check whether `../gamer-pat` exists.
If it exists, ask the user whether they want to also run as GAMER PAT.
If the answer is YES, read and follow:
- `../gamer-pat/README.md` (especially `Main Instructions`)
- all four `.txt` files under `../gamer-pat`

## Runtime Authority (Important)

For this camp, the default runtime is `logdex.sh` with Codex.
Treat `./software/source/server/livekit/multimodal.py` as a required reference for robot-control behavior and safety rules, not as the default execution path.
Do not assume `multimodal.py` is actively running unless user context explicitly indicates that it is.

## The Robots

The robot is one of the following:

Hexapod: The system is written under `./software/hexapod`. It depends on libraries that cannot be used in a poetry process, so interaction with the hexapod system is done via an RPC bridge.

Arm: The system is written in `./software/Arm_Lib.py`.

From the contents of multimodal.py, you can tell which type of robot this computer is controlling.
Reading `./software/source/server/livekit/multimodal.py` is mandatory before deciding robot behavior, because it contains detailed control rules.

## Special Case: Development Environment

This repository may be used to develop and maintain the Academy Camp fork of 01, without controlling a physical robot.
In that case, treat the session as a software development task environment, not as an active robot control environment.
Do not assume Hexapod or Arm behavior unless `./software/source/server/livekit/multimodal.py` and the user context clearly indicate that a robot is currently being controlled.

## Creating and Updating Skills

By placing files that represent skills (for example, Python code) under `./software`, users can call those skills to make the robot operate.

## Skill Import Destination Policy

When users ask to "import a skill" in this repository context, treat it as a robot-skill import by default.
Install destination must be fixed to:
- `./software/skills`

Do not import to Codex skill directory (`~/.codex/skills`) unless the user explicitly says they want a Codex skill.

If an import command supports `-X`, interpret `-X` only as "skip confirmation prompts".
`-X` must never change the install destination away from `./software/skills`.
