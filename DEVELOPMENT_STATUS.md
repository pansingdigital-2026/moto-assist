# Development status

Updated 2026-11-16. Release: 0.1.0 foundation. **Windows hardware acceptance is pending.** Phase 1 implementation and the checks feasible on this Linux host are complete; this is not yet a verified Windows release or an intelligent riding controller.

## Implemented

- Five-page dark PySide6 Essentials desktop UI: dashboard, riding simulation, reference recording/history, performance, settings.
- Windows XInput physical controller polling, six raw analog axes, standard button mask, slot scanning/reconnection; configurable stop chord. No virtual controller output.
- Windows GPU/system enumeration, game window title matching, foreground detection, client-area capture through DXcam, configurable adapter/output/origin, DPI awareness.
- Independent input, capture, recording and hardware-query workers; latest-frame UI; bounded recording buffer; local overrun-based capture-rate reduction.
- Lightweight/Balanced/Performance presets with explicit FPS targets, measured capture rate/call latency and process CPU/RAM.
- Timestamp-associated JPEG + JSONL recordings, validity/age metadata, dropped-frame counts, assisted-reference caveat, partial-session manifests, disk/error handling, SQLite session history.
- Tray hide/restore/quit, configurable Windows global shortcuts with conflict reporting, controller emergency stop, rotating logs.
- Pure synthetic decision engine demonstrating speed-dependent braking, bounded steering/throttle, manual mode/override, confidence/focus/staleness/disconnect/emergency gates. This engine never drives a game.
- Synthetic capture and prerecorded-video replay with explicitly synthetic controller samples.
- Automated setup/run/test/build batch scripts, defaults, architecture, roadmap, dependency research and beginner installation/troubleshooting guidance.

## Executed validation

On Linux, Python 3.12.14:

- **25 automated tests passed** on the final run (2.20 seconds). Tests cover analog normalization, stale/future/nonfinite data, confidence/focus/gameplay/manual/disconnect/emergency conditions, speed-dependent synthetic decisions, config validation, timestamp association, JPEG readback, recorder disk-write failure, bounded queue drops, worker shutdown, local-video EOF and Qt dashboard/recording/settings flow.
- Headless Qt application startup and timed clean shutdown succeeded. Offscreen screenshot inspected: dashboard renders the synthetic capture, axes, navigation and controls correctly.
- `pip check`: no broken requirements. Source/test compilation succeeded.
- All selected runtime dependencies and their dependencies resolved and downloaded as **Windows x64 / CPython 3.12 wheels**, including DXcam 0.3.0. Inspected the shipped DXcam wheel's create/grab/release and width/height API used by the adapter. This is compatibility evidence, not Windows execution.
- Reusable cloud `install_script` and `start_skill` saved as an environment draft; publication and fresh-task restoration are not verified. Linux/Windows GitHub Actions test configuration added but not executed remotely.
- No application source or commits existed before this work. The initial foundation is intended for the GitHub main branch; Git history records its source revisions. Source publication does not verify Windows hardware or publish the cloud environment.

Non-fatal Linux headless messages: Qt offscreen plugin does not support propagateSizeHints; fontconfig could not write its cache. These did not prevent tests, screenshot rendering or application shutdown.

## Unverified / limitations

- **User testing required:** Windows launch, real Xbox wired/wireless/reconnection, NVIDIA and hybrid GPU detection, MotoGP 26 window matching, DXcam frame capture, display scaling/multiple outputs, background shortcuts, tray behavior and both target PCs alongside OBS.
- Windows executable build recipe is supplied but **the Windows EXE has not been built or tested here**. No game/OBS FPS or latency claims are made. F12 may be reserved by Windows; fallback shortcut configuration is provided.
- Frame/input synchronization uses host acquisition-completion timestamps. Controller state is recorded per captured frame, not every 125 Hz poll; sub-frame transitions can be lost. Input freshness validity is recorded, not hidden.
- Reference recording may include menus, pauses or loading screens. No gameplay-state recognition, speed/gear OCR, HUD calibration, segmentation, circuit localization, lap timing, profile generation or learned model exists yet.
- No live automatic braking/steering/throttle/tuck-in, virtual output, double-input isolation, trail braking or autopilot. Future controls are visibly disabled. ViGEmBus retirement prevents presenting its wrapper as a maintained solution.
- Per-process GPU utilization, model inference/output latency, direct OBS/GPU-pressure detection, correction graphs and automatic game-state safety gating are not implemented. Adaptation currently reacts only to local processing overruns.
- Profile schema is reserved in SQLite; no fabricated track data or operational profile import/export. Recorded sessions can be copied between computers.
- No code was copied from TMRL/Linesight; Linesight root license location was not established, so reuse was not assumed.

## Next steps

1. Run docs/WINDOWS_TESTING.md on the RTX 3050 laptop, then desktop, and record actual outcomes.
2. Resolve any hardware/window/display incompatibilities and validate the packaged folder on Windows.
3. Collect labeled offline clips with one fixed camera; implement calibrated HUD/gameplay recognition in Phase 2.
4. Select a maintained, permitted virtual output path before attempting live intervention. Until then, monitoring and future coaching remain the supported direction.
