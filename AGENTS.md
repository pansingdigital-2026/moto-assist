# MotoAssist contributor instructions

Use Python 3.12 and the existing checkout. Cloud tasks are isolated; do not create worktrees unless explicitly asked. Run `.venv/bin/python -m pytest -q` on Linux; `test.bat` on Windows. For GUI checks on Linux set `QT_QPA_PLATFORM=offscreen`. Run the application with `--simulate` when Windows hardware is unavailable.

Keep UI, device adapters, recording, decisions and storage independently testable. Use monotonic timestamps, bounded buffers and explicit stale/unknown states. Preserve raw controller samples in recordings. Never label simulated results or mocked adapters as hardware verification. Update DEVELOPMENT_STATUS.md after material changes.

Scope is offline, single-player, non-leaderboard gameplay. No process-memory access, injection, anti-cheat bypasses or fabricated telemetry. Virtual output remains absent until a maintained, permitted solution and input deduplication path are verified. All future output paths must fail closed on stale input, missing focus, low confidence, menus, disconnects and emergency stop.

Do not silently add network inference, model downloads or training dependencies. Do not overwrite user recordings/settings. Inspect upstream licensing before copying code. Keep Windows setup and packaging instructions reproducible and report checks actually executed.
