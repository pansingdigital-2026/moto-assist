# Troubleshooting

- **Python not found:** install Python 3.12 x64 with the launcher. `py -3.12 --version` must work. Do not use a 32-bit interpreter. Run setup from a writable extracted folder.
- **Package install fails:** retain the error; check Internet/proxy access to pypi.org and files.pythonhosted.org. Do not disable certificate checks. Rerun setup after correcting access. No paid keys are needed.
- **No controller:** check Windows Game Controllers and Xbox Accessories. The device must expose XInput; use wired USB as the first diagnostic. Only the selected/first connected XInput slot is monitored. The Guide button is not exposed by standard XInput.
- **No game found:** set a distinctive substring of the visible game's window title in Settings and restart. Detection is a title match, not authenticated game telemetry. Avoid titles matching another application.
- **No capture while looking at MotoAssist:** expected; only the foreground game is captured. Use the background recording shortcut while the game is focused. Simulation and video replay do not need game focus.
- **Start recording says no fresh frame:** focus the game and press F6; the GUI cannot capture a game that is behind it. Check global shortcut registration errors.
- **Wrong output / hybrid laptop:** DXcam adapter/output IDs may not equal NVIDIA's ordinal. Inspect `dxcam.device_info()` and `dxcam.output_info()` in the virtual environment. Choose the output containing the game and enter that monitor's desktop origin. Ensure the game is entirely within one output. Restart after saving. This path needs laptop validation.
- **Black frames or capture error:** try borderless/windowed mode, current drivers and the correct adapter. Restart MotoAssist after changing display mode. No protected-surface or security bypass is provided.
- **Shortcut does nothing:** inspect status bar. F12 may be OS-reserved; configure an unused F-key. Back + Start stops recording. F7/F9/F11 have no live riding behavior yet.
- **Recording fills disk:** stop and move complete session folders. JPEG recording can be large. The writer stops below 256 MiB free; check the manifest's `error` and `complete`. Partial recordings remain for diagnosis.
- **Low FPS:** use Lightweight mode; avoid 4K capture until measured; reduce OBS/game load. UI preview refreshes at 10 Hz even when capture is faster. A static frame may not generate new DXGI captures. Metrics measure local processing, not end-to-end game latency.
- **Window disappears:** restore from tray. Quit from tray actually stops workers and saves data. If the desktop has no tray, closing exits normally.
- **Invalid settings:** the startup dialog names the settings file. Back it up and rename it to reset defaults. Existing recordings remain untouched.
- **Diagnostics:** `%LOCALAPPDATA%\MotoAssist\logs\motoassist.log`; recording folders include timestamp indexes and manifest. Logs never claim live assistance was active in this release.

## Version 0.2 recognition and controller additions

- Rerun setup.bat after updating; otherwise SDL2/OCR imports may be missing. Read CONTROLLERS.md and run controller_test.bat. Simulation intentionally shows synthetic inputs; use run.bat without --simulate for physical input.
- Inspect Diagnostics for every XInput slot and SDL device inventory. If a connected native device has no changing input, explicitly select SDL2. Both representations can refer to one physical Xbox controller.
- Unknown speed/gear/timer/lap values: tightly calibrate the numeric region on a saved gameplay screenshot. Set the speed unit correctly; avoid including unrelated HUD text. Auto detection requires unambiguous labels.
- Unknown road or bike offset: calibrate asphalt sample, road search and bike anchor. Lighting, shadows, wet surfaces or changed cameras invalidate appearance assumptions. These are image-space heuristics.
- Unknown crash/recovery: this release requires explicit readable crash/recovery text. Absence of evidence does not mean the rider is upright. No input correction is ever sent.
- Profile generation requires two complete laps and at least five reliable speed readings each. F5 boundaries need three presses for two laps; prerecorded sessions can use Edit recorded lap boundaries. Incomplete sessions, mismatched conditions and mixed source types are rejected.
- Duplicate imported profile IDs are rejected. Review the existing profile before deleting it if you intend to import that ID again; reference recordings remain separate.
- Recognition is slower than capture by design; a latest-frame worker targets 2 Hz, adjustable in Settings. Lower the rate if CPU contention affects game/OBS. Stale data is labelled. No GPU resource sharing guarantee is made.
- In restricted Linux cloud development, set MOTOASSIST_DATA_DIR to a writable /tmp or /workspace path. An unwritable home data directory is an environment limitation, not a controller failure.
