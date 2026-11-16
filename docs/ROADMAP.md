# Roadmap

## Implemented foundation and Phase 2 baseline

0.1: monitoring, capture, recording, simulated decisions, tray, metrics and Windows install/build scripts. The user confirmed Windows launch and coexistence with MotoGP; controller detection failed on their hardware.

0.2: native all-DLL/all-slot XInput diagnostics, SDL2 alternative, device selection/reconnection, independent controller utility; local OCR and calibrated vision; diagnostics and HUD editor; video analysis; multi-lap recording/profile generation and JSON profile management. Synthetic/software acceptance exists; physical controller recovery and actual MotoGP recognition accuracy remain user hardware/data verification requirements.

## Next validation gates

1. Run controller diagnostics over USB and Bluetooth on the laptop; verify background input and reconnection, then repeat on desktop.
2. Collect annotated MotoGP clips in the fixed third-person camera at supported resolutions. Measure speed/gear/timer/lap errors, boundary quality, line-color false positives and state confusion against manual labels. Do not treat OCR confidence as measured accuracy.
3. Tune calibration/algorithms from that evidence. Add trained segmentation/state models only if data justifies their resource cost. Current appearance heuristics should remain explicitly identified.
4. Validate profile repeatability across multiple laps and conditions. Add visual landmark matching/live progression estimation before using reference profiles for real-time intervention. Time-normalized profiles alone cannot locate a bike on track.
5. Phase 3: offline-evaluated braking decisions, a maintained/authorized virtual-output solution and validated failure-release safeguards. Until then retain monitoring/coaching.
6. Phases 4–6: calibrated steering, throttle/trail braking, tuck-in mappings and learning from properly labeled data. Experimental autonomous laps remain separate from baseline functionality.
7. Distribution: Windows build acceptance, dependencies/notices, clean-machine testing, performance alongside OBS, profile migration and optional installer/signing.
