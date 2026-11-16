# MotoAssist

A local Windows desktop foundation for an offline MotoGP riding assistant. **Version 0.1 monitors, captures and records; it does not control the game.** No trained model, game telemetry or automatic riding is included.

## First launch on Windows 11

1. Install **Python 3.12, 64-bit** from https://www.python.org/downloads/windows/ with the Python Launcher enabled. Install current NVIDIA drivers through NVIDIA's official installer.
2. Download/extract this repository to a writable folder (for example `Documents\MotoAssist`). Keep all project files together.
3. Double-click `setup.bat`. Internet is needed for package installation only. Wait for “Setup complete.”
4. Open a terminal in that folder and run `run.bat --simulate`. You should see animated synthetic frames, analog values and capture FPS. This does not require a controller or game.
5. Close using the tray menu **Quit**. Connect your Xbox controller and start MotoGP 26 in an **offline practice session**, preferably borderless windowed on your primary monitor.
6. Run `run.bat`. The dashboard displays all six analog axes and standard XInput button states. The application enumerates GPU names through Windows CIM, including NVIDIA and integrated GPUs.
7. If needed, set the matching **Game title** text in Settings, save and restart. “MotoGP” is a configurable title match, not a verified executable name or game connection.
8. Click **Start recording**, then focus the game. Capture is suspended while the game is unfocused. The start action requires a fresh frame: use global **F6 while the game is focused**, or use the tray/UI immediately after a frame. Press F6 again to stop.
9. On the Performance page, inspect actual capture FPS, capture-call time, process CPU and RAM. Target FPS is not a performance claim.
10. Click **Hide to tray**. Use the tray icon to restore or quit. Closing the window normally hides it when a tray is available.

Use `run.bat --video "C:\path\practice.mp4"` to replay a local video. Its controller stream is explicitly synthetic; it cannot reconstruct original player inputs.

## Controls and data

Default background shortcuts: F6 recording; F7/F9/F11 report that braking/steering/throttle assistance are unavailable; F8 toggles the **simulation** engine; F10 cycles simulation modes; F12 stops recording and simulated decisions. Windows reserves F12 on some systems, so registration can fail: set a different key in Settings. Conflicts are reported in the status bar. **Back + Start** is the independent controller stop shortcut (configurable bitmask). Physical game control always remains connected directly to the game.

The Riding Assistance page evaluates synthetic speed/curvature/confidence inputs. Manual and Experimental Autopilot produce no automated decision. Subtle/Balanced/Maximum use bounded illustrative policies; these are not calibrated motorcycle controllers. Future live-feature controls are disabled and labeled.

Data is stored in `%LOCALAPPDATA%\MotoAssist`: settings, rotating logs, SQLite session history and recording folders. Set `MOTOASSIST_DATA_DIR` before launch for a portable/custom location. Copy whole recording folders between computers. No runtime cloud service is used.

Each recording contains JPEG images, a `frames.jsonl` index with timestamps and physical inputs, and a versioned manifest. Input samples are associated to each frame at or before acquisition completion. Inputs older than 100 ms are marked invalid. This is software timestamp association, **not guaranteed hardware synchronization**. Only the controller sample associated with each frame is persisted; sub-frame button transitions may be missed. Dropped frames are counted; timestamps must be used for replay timing. In-game assistance corrections are never labeled as physical demonstrations.

## Tests and executable

- `test.bat`: automated policy, safety, capture simulation, recording, video replay, configuration and Qt UI tests.
- `build.bat`: Windows-only PyInstaller folder build in `dist\MotoAssist`. Distribute the **entire folder**, not just the EXE. Windows packaging still needs validation on real Windows.
- To update: quit MotoAssist, back up your data folder, replace project files with the new version, rerun `setup.bat`, then `test.bat`. User data stays outside the checkout.

Linux development: `python3.12 -m venv .venv`, `.venv/bin/python -m pip install -e '.[dev]'`, `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q`. For a headless UI startup check: `QT_QPA_PLATFORM=offscreen .venv/bin/python -m motoassist --simulate --smoke-seconds 3`.

Read [development status](DEVELOPMENT_STATUS.md), [architecture](docs/ARCHITECTURE.md), [roadmap](docs/ROADMAP.md), [dependency research](docs/DEPENDENCIES.md), [Windows acceptance checklist](docs/WINDOWS_TESTING.md) and [troubleshooting](docs/TROUBLESHOOTING.md).
