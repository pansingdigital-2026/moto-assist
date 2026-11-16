# MotoAssist 0.2

A local Windows desktop application for **offline MotoGP monitoring, gameplay recognition and reference-track learning**. No live controller output, automatic riding or autopilot is enabled. Windows launch and running alongside MotoGP were confirmed by the user for 0.1; the new physical-controller paths still need hardware verification.

## Update or install on Windows 11

1. Download the repository using **Code → Download ZIP**, then **Extract all** into a writable folder.
2. Install **Python 3.12 x64**, including the launcher. With the Python install manager: `py install 3.12`. Verify with `py -3.12 --version`. Python 3.14 is not supported by the selected OCR dependency; both Python versions can coexist.
3. Double-click **setup.bat**. Rerun it when updating from 0.1: new SDL2 and local OCR dependencies are required. Internet is used for installation only; OCR models are bundled in the installed package.
4. Double-click **controller_test.bat**, connect your Xbox controller and move sticks/buttons. It prints live inputs and writes `%LOCALAPPDATA%MotoAssistlogscontroller-diagnostic.log`. No game or UI is required.
5. Double-click **run.bat** for the physical controller and game. **`run.bat --simulate` deliberately uses synthetic inputs**, not your Xbox controller.
6. Open **Diagnostics**. Choose `auto`, `xinput` or `sdl2`, click **Refresh / reconnect**, choose the controller and click **Use selected controller**. SDL2 is the alternative for devices not exposed correctly through XInput, including supported Xbox Bluetooth paths. Wired and Bluetooth behavior must be tested on your hardware.
7. Start MotoGP in offline practice, preferably borderless. Keep the game title/output settings from your working installation. Capture runs only while the game is foreground; controller monitoring continues in the background.

Read [controller troubleshooting](docs/CONTROLLERS.md) if input remains absent. No driver replacement, game modification or anti-cheat bypass is performed.

## Recognize gameplay

Open **Recognition**. The table shows values, confidence, unknown/error/stale status and the reason for every module. Automatic OCR uses labelled speed, gear, lap and timer text where unambiguous. Small or unlabelled values need calibration:

1. Capture a gameplay frame, switch back to MotoAssist, then click **Calibrate last captured frame**. Alternatively select a screenshot.
2. Select `speed`, `gear`, `lap_timer` or `lap_number` and drag a tight box around **only that value**. Select the whole map for `minimap`.
3. Select `road_sample` and mark a small clear asphalt patch away from the bike, markings, shadows and grass. Set `road_search` around the visible track; set `bike_anchor` around the rear tire's contact point for the fixed third-person camera.
4. Save. Calibration applies immediately and persists. Regions use normalized coordinates for 1080p/1440p/4K. Changing camera, HUD layout or aspect ratio requires recalibration. Set `speed_unit` to `mph` if the cropped speed has no unit and the game uses mph; stored speed is km/h.
5. Review the detected values. Confidence scores are model scores/heuristics, **not measured probabilities of correctness on MotoGP footage**. Unknown is an expected result when evidence is insufficient.

Road boundaries, surface, bends and bike offset are calibrated image-space estimates. Racing-line green/yellow/red blobs are visual candidates. Minimap extraction provides an outline and marker candidate, not world position. Crash/recovery detection requires explicit visible text and temporal confirmation; unlabelled crashes remain unknown. Menus, replays, shadows and unusual weather can confuse estimates. These observations never control the game.

## Learn a track

1. Enable the game's ideal racing line and built-in assists if desired. Keep one camera, bike/category and weather per profile.
2. In **Track Learning**, enter circuit, category, bike and weather; preserve the checkbox stating whether in-game assists are enabled or unknown.
3. Focus the game and press **F6** to begin recording. Press **F5** at the start/finish line before the first lap, after lap one and after lap two. More laps improve the reference set. F6 stops recording.
4. Select the stopped session(s), then **Generate profile from selected sessions**. At least two complete laps and five reliable speed observations per lap are required. If manual boundaries are absent, stable increases in recognized lap number supply boundaries; partial first/last laps are excluded.
5. Use **Review** to inspect lap durations, sampled reference speed, corner entry/exit points, visual braking intervals, ORB landmarks, line sections and confidence. Profiles align laps by **normalized elapsed lap time**, not world coordinates or reliable live localization.
6. **Export** produces a portable JSON profile. **Import** validates it into the local database; duplicate IDs are rejected. **Delete** removes only the selected profile after confirmation, preserving recordings. Copy referenced recording folders separately if needed on another computer.

Physical controller inputs do **not** include corrections made by the game's assistance systems. The manifest and profile retain this distinction. Profiles are references requiring review, not trained policies or ideal racing lines proven optimal.

## Analyze recorded videos

Use **Recognition → Analyze video to reference session** to process a local MP4/MKV/AVI/MOV without capturing the game. Frames, media timestamps and recognition results are saved locally; original physical inputs are marked unavailable. Then select that session in Track Learning and use **Edit recorded lap boundaries** if necessary: enter seconds from its first frame, such as `0, 92.4, 185.1` for two complete laps. Generate a profile as above.

Command line:

```bat
.venv\Scripts\python.exe -m motoassist.analyze_video "practice.mp4" --output "analysis\practice-01" --settings "%LOCALAPPDATA%\MotoAssist\settings.json" --interval 0.5
```

The output folder must be new. `run.bat --video "practice.mp4"` remains available for real-time preview with a clearly labelled synthetic controller stream. Offline analysis is preferable when every sampled frame must be analyzed.

## Controls, data and testing

F5 marks lap boundaries; F6 starts/stops recording; F8/F10 control the **simulation-only** decision demonstration. F7/F9/F11 report that live riding assistance is unavailable. F12 and **Back + Start** stop recording/simulated decisions. Windows can reserve F12; configure a different unused key if registration fails. Background shortcuts and tray behavior require Windows acceptance.

Settings, rotating logs, SQLite profiles/session history and recordings live in `%LOCALAPPDATA%\MotoAssist`. Set `MOTOASSIST_DATA_DIR` for a portable folder. Existing 0.1 settings migrate to new defaults, including F5. Recordings contain JPEG frames, `frames.jsonl`, `observations.jsonl`, `events.jsonl` and a manifest. Frames/observations share acquisition sequence and monotonic timestamp; controller samples are taken at or before acquisition and flagged invalid after 100 ms. Raw controller data is persisted per frame, not every poll. Frame drops and observation drops are counted; use indexes rather than assuming constant FPS.

- `test.bat`: automated checks, including actual bundled OCR and SDL virtual-device input.
- `controller_test.bat --backend sdl2`: independent SDL diagnostic; `--backend xinput` isolates native input; `--simulate --seconds 5` tests the diagnostic without hardware.
- `build.bat`: Windows PyInstaller folder build with SDL and OCR assets. This recipe is not a verified Windows executable release. Distribute the entire `dist\MotoAssist` folder.
- Linux: `python3.12 -m venv .venv`, `.venv/bin/python -m pip install -e '.[dev]'`, `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q`.
- Headless smoke: `QT_QPA_PLATFORM=offscreen MOTOASSIST_DATA_DIR=/tmp/motoassist-smoke .venv/bin/python -m motoassist --simulate --smoke-seconds 4`.

See [development status](DEVELOPMENT_STATUS.md), [architecture](docs/ARCHITECTURE.md), [roadmap](docs/ROADMAP.md), [dependency research](docs/DEPENDENCIES.md) and [Windows acceptance](docs/WINDOWS_TESTING.md).
