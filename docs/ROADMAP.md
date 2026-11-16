# Roadmap and release gates

1. **Foundation (current):** GUI, physical XInput monitoring, GPU/window detection adapters, capture, timestamped recording, tray, diagnostics, simulation. Linux checks precede Windows acceptance on both machines. No hardware verification without user evidence.
2. **Recognition:** manual HUD ROI calibration saved in normalized coordinates; labeled speed/gear validation set; gameplay/menu/crash classifiers; user-supplied track labels and reference-lap boundaries. Test 1080p, 1440p, 4K with the fixed camera. Report recognition error and confidence calibration, not just FPS.
3. **Braking:** single user-configured circuit, aligned reference speed profiles across multiple laps, distance/progression uncertainty, progressive braking. First evaluate offline replay. Select a maintained, permitted virtual controller route and documented physical-device isolation before any game output. Otherwise retain coaching-only operation.
4. **Steering:** boundary segmentation, corner recognition, uncertain bike positioning and bounded corrections. Require immediate physical override, focus/menu/staleness safeguards and hardware output-release tests.
5. **Advanced assistance:** calibrated trail braking, throttle and tuck-in mappings, internal racing line, departure risk, coordinated front/rear braking only where mappings support it. Do not infer tire grip or lean as exact measurements.
6. **Learning:** curated multi-lap datasets, assisted-reference labels, train/validation splits by session, optional PyTorch experiments, model export and ONNX benchmarking. Autonomous laps remain experimental; use no online leaderboards.
7. **Distribution:** verified Windows builds, dependency/license inventory, signing/installer decisions, portable profile exchange, upgrade/migration testing and both-hardware acceptance. Package recipe exists now; shipping readiness does not.

Every phase requires tests, recorded evidence, explicit limitations and updates to DEVELOPMENT_STATUS.md. No time or lap-performance guarantees are made.
