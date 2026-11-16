# Windows acceptance checklist — version 0.2

The user has confirmed that 0.1 launches on Windows and runs alongside MotoGP 26 without crashing. They reported no physical controller inputs in 0.1. Do not expand those observations into validation of 0.2.

Run on the RTX 3050 laptop first, then RTX 3060 Ti desktop. Record Windows/NVIDIA versions, display arrangement, resolution, Xbox model/firmware, USB/Bluetooth and Steam Input/device-hiding settings if applicable.

1. Rerun setup.bat, then test.bat. Check version 0.2 and seven tabs. Tests include actual SDL virtual-device IO and bundled OCR; they do not require or verify physical hardware.
2. Run controller_test.bat with the game closed and open, in foreground and background. Test auto, xinput and sdl2; record backend inventory, slot return codes and inputs. Select the working backend/device in Diagnostics.
3. Verify both sticks, both triggers, all standard buttons and D-pad. Test USB and Bluetooth separately. Disconnect/reconnect and refresh. Unselected/duplicate API representations must not merge inputs; stale values must clear. Back+Start must stop recording.
4. Confirm GPU inventory, foreground game detection and DXcam capture still work. Verify supported resolutions, Windows scaling and hybrid GPU/output configuration. Recalibrate when camera or HUD layout changes.
5. Calibrate each visible numeric HUD field and minimap; inspect readings against the actual display. Label representative frames manually before claiming accuracy. Check unknown states when HUD is hidden or cropped.
6. Calibrate clear asphalt/search region and fixed-camera bike anchor. Check road edges, curve direction, relative offset and colored ideal-line sections on straights, corners, shadows, grass, wet track and off-track frames. Expect unknown or incorrect heuristic estimates in difficult conditions; log examples.
7. Pause, resume, load, crash and recover. Explicit state-text detection needs readable matching text; unlabelled states remain unknown. No virtual output must occur under any circumstances.
8. Record at least two complete offline laps with game assists enabled. F5 marks start/finish three times; F6 stops. Check manifest complete, frame/observation sequence/timestamps, physical-input age/provenance, events and drop counts.
9. Generate and review a profile. Check reference speeds, time-aligned corners, line colors, visual braking intervals, reference laps, landmark descriptors, category/weather and confidence. Export/import on the other PC; delete a profile and verify recordings remain.
10. Analyze a prerecorded gameplay video. Verify media timestamps and unavailable original inputs; edit lap boundaries in seconds if OCR cannot segment laps. Cancel a long task and verify partial output is marked incomplete.
11. Confirm global shortcuts (F12 may be reserved), tray hide/restore/quit and shutdown while recording/analyzing. No overlay should appear in OBS footage.
12. Compare game frame time and OBS dropped frames with the app off/on, Lightweight first. Record capture FPS, OCR latency, CPU/RAM, not just configured targets. No numerical performance guarantee is made.
13. Run build.bat on Windows, then test the entire dist/MotoAssist folder on an account without development Python, including SDL discovery and offline OCR models.
