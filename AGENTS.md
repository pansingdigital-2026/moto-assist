# MotoAssist contributor instructions

Use Python 3.12 and the existing checkout. Cloud tasks are isolated; do not create worktrees unless explicitly asked. Run `.venv/bin/python -m pytest -q` on Linux; `test.bat` on Windows. For GUI checks on Linux set `QT_QPA_PLATFORM=offscreen`. Run the application with `--simulate` when Windows hardware is unavailable.

Keep UI, device adapters, recording, decisions and storage independently testable. Use monotonic timestamps, bounded buffers and explicit stale/unknown states. Preserve raw controller samples in recordings. Never label simulated results or mocked adapters as hardware verification. Update DEVELOPMENT_STATUS.md after material changes.

Scope is offline, single-player, non-leaderboard gameplay. No process-memory access, injection, anti-cheat bypasses or fabricated telemetry. Virtual output remains absent until a maintained, permitted solution and input deduplication path are verified. All future output paths must fail closed on stale input, missing focus, low confidence, menus, disconnects and emergency stop.

Do not silently add network inference, model downloads or training dependencies. Do not overwrite user recordings/settings. Inspect upstream licensing before copying code. Keep Windows setup and packaging instructions reproducible and report checks actually executed.

Phase 2: `controllers.py` owns XInput/SDL resources on the polling thread. Keep SDL calls on their owning thread; test virtual devices without touching physical hardware. `vision.py` publishes unknown/error/confidence per module. Maintain conservative parsing and explicit calibration; do not turn missing observations into numeric zero. `learning.py` profiles use elapsed-time alignment, not live localization. Preserve source provenance and never mix synthetic/video/Windows laps. Run the bundled-model and SDL virtual-device tests as well as UI checks before pushing changes.
