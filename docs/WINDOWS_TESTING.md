# Windows acceptance — pending user execution

Run these checks separately on the RTX 3050 laptop first, then the RTX 3060 Ti desktop. Record Windows/NVIDIA versions, resolution, display arrangement, controller connection type and game/OBS settings. Never mark these complete from Linux simulation.

- Run setup.bat, test.bat, run.bat --simulate. Verify synthetic image, axes, FPS, recording and normal Quit.
- Run live. Verify Windows reports the actual NVIDIA GPU and integrated adapter (if present). Compare with Device Manager.
- Connect Xbox via cable, then wireless; move both sticks, triggers and each standard button. Compare endpoints/dead centre. Unplug and reconnect; ensure stale values clear and polling recovers.
- Start offline MotoGP 26. Confirm the exact window-title filter, client area, foreground state and capture preview. Alt-tab: image must clear and capture must suspend. No game memory access is used.
- Exercise 1920×1080, 2560×1440 and 3840×2160 where the display supports them. Check Windows scaling and borderless/windowed capture. Set DXcam device/output and desktop origin when needed; reject windows spanning outputs.
- F6 with the game focused starts a session; ride for 30 seconds; F6 stops. Validate manifest `complete`, JPEG files, monotonically increasing timestamps, physical input labels and input validity. Do not assume built-in game assists appear in the recorded input.
- Confirm registered hotkeys work in background and conflict messages appear for occupied keys. F12 may be unavailable; configure a replacement and verify Back + Start stop.
- Hide/restore via tray; Quit while recording and confirm the recording finalizes and process exits.
- Run OBS alongside the game. Compare game frame time and OBS dropped frames with MotoAssist off and on. Try Lightweight first; collect process CPU/RAM and actual capture FPS. No numerical overhead limit has been validated yet.
- Run build.bat; copy the whole dist/MotoAssist folder to a clean Windows account without development Python. Launch, record, close, restart and verify persisted settings.

No virtual inputs should be emitted in any check. There is no autopilot or actual braking/steering assistance to validate in Phase 1. Pause/menu recognition is not implemented; those frames may be recorded. Report results and logs before enabling subsequent development phases.
