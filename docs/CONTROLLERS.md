# Physical Xbox controller diagnosis

The 0.1 implementation already used native XInput and scanned slots. Inspection found insufficient diagnostics, no SDL fallback or selection, and a worker-wide exception handler that could terminate polling permanently. The user's exact hardware failure cannot be established without their diagnostic output; it was not reproduced using a physical Xbox controller in the cloud.

0.2 replaces that path with `NativeXInput`, `SDLController` and `ControllerManager`:

- Native XInput loads xinput1_4.dll, xinput1_3.dll and xinput9_1_0.dll where available. Explicit fixed-width structures/signatures are used. Every DLL and all four slots are checked; a working route is retained per slot. All DLL names and return codes are logged (0 success, 1167 disconnected).
- SDL2 uses its GameController mappings and Xbox HIDAPI support, background-event hints and regular updates. Only mapped devices identified as Xbox type, Microsoft vendor or Xbox name are offered. Unsupported/unmapped devices remain visible in the diagnostic inventory with their exclusion reason.
- Auto mode chooses one device, preferring native XInput on first discovery. It does not merge duplicate native/SDL representations. If a native device appears connected but has no changing values, choose its SDL representation explicitly.
- Refresh closes/reinitializes backends on their owning polling thread. Disconnected devices are rescanned and absent backends retried. Polling exceptions do not permanently end monitoring. SDL selection uses GUID plus identical-device ordinal; identical controllers may require reselection after their connection order changes.
- Six analog axes, D-pad, face/shoulder/stick/menu buttons use the original XInput bitmask conventions. SDL Y axes are inverted to XInput's positive-up convention; triggers map to 0–1. Standard XInput does not expose Guide. Raw inputs are not dead-zone filtered in recordings.

## User procedure

1. Rerun setup.bat after updating. Quit old copies of MotoAssist.
2. Run controller_test.bat normally (not `--simulate`). Move both sticks/triggers and press buttons while the console is focused, then while the game is focused. Read the printed selected backend and input values.
3. If native reports all slots disconnected, run `controller_test.bat --backend sdl2`. If SDL reports a mapped Xbox device, choose it under Diagnostics in the app.
4. Test USB first, then Bluetooth. If Windows recognizes a device but SDL reports `mapped: false`, preserve the log. Do not guess axis mappings or install unsigned drivers. Update Xbox firmware through Microsoft's Xbox Accessories app and test documented Windows connection options.
5. Device-hiding tools or Steam Input can change which controllers a process sees. Inspect their documented configuration if installed; do not bypass filters/security or modify game memory. Compare diagnostics with the game closed and open.
6. Disconnect/reconnect during monitoring. Values should clear within 100 ms and reconnect after enumeration, normally within a second. A missing backend may retry after five seconds. These are polling targets, not hardware guarantees.

Logs: `%LOCALAPPDATA%\MotoAssist\logs\controller-detection.log` for the app and `controller-diagnostic.log` for the standalone tool. They include backend/slot status, SDL mapped-device inventory, selected source and failures. The standalone tool additionally logs input samples at 10 Hz. Share these logs if the issue persists; do not send credentials. No diagnostic needs administrator rights, cloud services, Qt, screen capture or a running game.

Automated tests exercise fixed-width native bindings using fake DLL return values and actual SDL2 virtual-device axis/button/detach behavior. They do not prove USB/Bluetooth or native XInput behavior on the user's computer.
