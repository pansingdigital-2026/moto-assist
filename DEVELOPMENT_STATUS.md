# Development status — MotoAssist 0.2.0

Updated 2026-11-16. Phase 1.1 controller remediation and the Phase 2 recognition/reference-learning implementation are present. **Actual physical-controller recovery and MotoGP recognition accuracy remain unverified on the user's hardware.** No automated game inputs are emitted.

## User-reported Windows evidence

The user confirmed that version 0.1 launched on Windows and that MotoGP 26 ran alongside it without crashing. They reported that Windows and MotoGP recognized their Xbox controller while MotoAssist did not. This verifies neither the new backends nor any recognition module. The exact original device/backend failure cannot be established without the new controller diagnostic logs.

## Implemented controller changes

- Replaced the old polling worker with native XInput routes across all four slots and all available system XInput DLLs; fixed-width bindings, return-code diagnostics and explicit device selection.
- Added SDL2 GameController/HIDAPI alternative, Xbox device filtering, background updates, normalized axes/triggers/buttons and mapped-device inventory.
- Added backend/device selection, refresh/reconnect, automatic rescans/retries and polling-exception recovery. One selected source is used; duplicate native/SDL representations are not merged.
- Added independent controller_test.bat / CLI, live console inputs, controller-diagnostic.log and rotating application controller-detection.log.
- Preserved raw input recording, input freshness checks, stop chord, simulation, capture, tray and existing controls. Legacy settings migrate with existing shortcut choices preserved.

## Implemented Phase 2

- CPU-only bundled-model OCR for speed, gear, lap timer and lap number; strict parsing, confidence threshold, unambiguous labelled HUD proposals and manual normalized calibration fallback.
- Drag-to-select calibration from the retained last capture or a screenshot: numeric HUD, minimap, road sample/search region, bike anchor and state text. Calibration applies live and is saved.
- Calibrated asphalt appearance segmentation, image-space road boundaries, centreline bend/corner direction, fixed-camera relative bike offset, green/yellow/red line candidates, minimap outline/marker extraction and ORB/hash visual references.
- Temporally confirmed pause/loading/crash/recovery text states; gameplay evidence from visible speed plus road. Missing/ambiguous/unlabelled states remain unknown.
- Independent latest-frame recognition worker, per-module diagnostics/confidence/reasons/staleness, annotated app-only preview, model latency display and bounded CPU thread counts.
- Timestamped observations associated with captured frames and the controller sample retained before inference; bounded writer queues, provenance, invalid/stale input flags, drop counts and lap-boundary events.
- Multi-lap recording with F5/manual boundary editing and conservative OCR lap-transition segmentation. Profile generation requires two complete laps with adequate speed evidence and rejects incomplete/mismatched/mixed-provenance sessions.
- Profiles contain median reference speeds, corner entry/exit estimates, colored visual braking intervals, landmarks, line sections, lap references, conditions, coverage and confidence. They explicitly use normalized elapsed lap time, not world position or live localization.
- SQLite profile storage, review, validated/size-limited JSON import/export, duplicate-ID rejection and confirmed deletion retaining original sessions.
- Prerecorded video analysis via GUI/background task and CLI; source media timestamps, unavailable original controller inputs, cancellation/incomplete manifests. Existing realtime replay and synthetic-controller workflows remain.
- Updated Windows packaging recipe, README, controller troubleshooting, architecture, dependency analysis, roadmap, defaults and acceptance checklist.

## Executed validation in Linux cloud

- **63 automated tests passed** in the final full regression run (17.39 seconds); no skips or expected failures. One informational warning identifies the bundled SDL2 binary version.
- Tests cover native DLL/slot enumeration via controlled native-call doubles, fallback/selection/reconnection/error recovery, and **actual SDL2 virtual Xbox axes/buttons/detachment**. Virtual-device evidence is not physical USB/Bluetooth evidence.
- Actual bundled OCR tested against generated HUD images. Vision tested on generated 960×540, 1920×1080 and 3840×2160 scenes. Separate numerical tests cover invalid/ambiguous/low-confidence readings and temporal state confirmation.
- Actual generated MJPEG video decoded, analyzed with bundled OCR, segmented into two reference laps and converted into a profile with recognized speed, line information and visual landmarks. This is a synthetic fixture, not a real MotoGP lap or performance benchmark.
- Recorder synchronization/drop/error/shutdown tests; profile exchange/validation/database CRUD; Qt calibration dragging, dashboard recording, asynchronous profile generation and legacy configuration migration.
- Independent simulated controller diagnostic completed. Headless app startup/shutdown completed; Recognition and Track Learning pages visually inspected. Initial OCR warm-up can be stale and is labelled accordingly.
- `pip check`: no broken requirements. Source/tests compile. Windows x64/CPython 3.12 wheels resolved and downloaded for the new dependencies and their dependencies.
- No Windows EXE was built or hardware tested in this Linux task. GitHub Actions execution is separate from these local results; do not infer CI outcomes from this report.

## Corrections found during development

The previous worker could permanently stop on a polling exception and exposed little useful controller diagnosis; it lacked SDL and selection. The exact physical-controller failure was not reproduced here. New backend tests verify the replacement behavior.

End-to-end tests found OCR labels without whitespace (`180km/h`) and a potential input-history expiry during model warm-up. Parsing now accepts the valid no-space label, and the matching physical sample is retained before inference. A first-model startup allowance is used in integration tests; no FPS guarantee is hidden in that timeout.

## Limitations / required verification

- Run docs/WINDOWS_TESTING.md on the RTX 3050 laptop first, then desktop. Verify native/SDL USB and Bluetooth, background monitoring, reconnection, shortcuts, tray, DXcam output selection and package assets.
- No actual MotoGP footage or annotated dataset was provided. HUD-font/layout robustness, road segmentation, corner estimates, minimap markers and line-color false positives require calibrated testing. Confidence values are model scores/heuristics, not measured accuracy probabilities.
- Road/bike estimates depend on manually selected asphalt and a fixed camera. Lighting, wet surfaces, grass, shadows, overlays and camera changes can invalidate them. No exact lean/grip/world coordinates are produced.
- Crash/recovery detection only acts on explicit readable text with confirmation. Unlabelled falls/recovery remain unknown. Replay/pause ambiguity remains; this system is not suitable for live input automation.
- Profiles align by elapsed lap time and retain visual references; they do not implement robust live localization, an optimal racing line or a trained riding policy. Inspect profile coverage and individual laps. Exported JSON does not embed all source images; copy session folders separately.
- Original physical inputs from prerecorded videos are unavailable. Synthetic runtime replay inputs are labelled synthetic. Physical recordings cannot reveal corrections performed internally by built-in game assists.
- Capture/recognition rates are targets. Measure CPU/RAM, game frame times and OBS dropped frames on both PCs. Direct GPU/OBS pressure arbitration, per-process GPU metrics and trained segmentation are absent.
- RapidOCR's bundled-model distribution is a deliberate legacy-package maintenance tradeoff; Python remains 3.12. Do not upgrade the package/interpreter without checking model packaging and rerunning validation.
- Virtual output, automatic braking/steering/throttle/tuck-in and autopilot remain outside this implementation. ViGEmBus retirement is unchanged; no unsupported driver was installed.

Next: collect the independent controller log if the physical issue persists, complete hardware acceptance, then validate/tune recognition against labelled MotoGP clips before starting live assistance work.
