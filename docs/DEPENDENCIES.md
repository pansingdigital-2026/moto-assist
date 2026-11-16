# Dependency and prior-art review

Reviewed 2026-11-16 using PyPI release metadata and upstream repository documentation. Versions below were available in the sources at review time. A recent package release is evidence of release activity, not proof of long-term maintenance or Windows game compatibility.

| Component | Decision | Evidence / compatibility |
|---|---|---|
| Python | 3.12 x64 baseline | Supported intersection of selected wheels; avoids adopting newest interpreter before hardware validation |
| PySide6 Essentials | 6.12.0 | PySide6 release 2026-10-08, Python ≥3.10; Essentials supplies Qt Core/Gui/Widgets without unused WebEngine. LGPLv3/GPL/commercial licensing requires distribution review |
| DXcam | 0.3.0, Windows only | Released 2026-03-12; Python ≥3.10; upstream documents CPython 3.10–3.14 wheels, grab/create/release, adapter/output selection and DXGI. MIT upstream; transitive comtypes |
| NumPy | 2.5.5 | Released 2026-11-15, Python ≥3.12; BSD family |
| OpenCV Python | 5.0.0.93 | Released 2026-07-02; Python ≥3.9 requires NumPy ≥2, consistent with selected NumPy. Used for JPEG/resize/video, no trained vision model |
| psutil | 7.2.2 | Released 2026-01-28; CPU/RAM reporting; BSD |
| XInput / Win32 | ctypes, built into Python | Documented OS APIs, no injected code or third-party controller hook |
| SQLite | Python standard library | Local session index; no server required |
| PyInstaller | 6.22.3, development extra | Released 2026-09-12; build on Windows for Windows; GPL with bundling exception, review dependency notices |
| pytest | 9.2.0, development extra | Released 2026-10-27; tests run in this environment |
| PyTorch | defer; observed 2.15.0 | Training unnecessary for Phase 1; avoid large runtime/CUDA dependencies |
| ONNX Runtime | defer; observed 1.32.0 | Evaluate CPU first when a validated model exists; no inference metrics fabricated |
| DirectML runtime | defer; observed 1.24.4 | Windows acceleration candidate, Python ≥3.11; compare on laptop against CUDA/CPU with the actual model |
| vgamepad | not installed; observed 0.2.0 | A Python wrapper release does not resolve retired Windows driver dependency |
| ViGEmBus | do not select as supported foundation | Upstream README explicitly says project is retired. No driver installation or anti-cheat bypass |

Direct application dependencies are pinned in pyproject.toml; transitive packages are resolved by pip and are not a cross-platform hash lock. Linux installation and `pip check` validate the local combination only. Windows wheel resolution can be checked without hardware, but runtime behavior needs Windows acceptance. Keep TLS verification enabled. No models, services or subscriptions are required at runtime.

## Research references

- [DXcam](https://github.com/ra1nty/DXcam): documented latest-frame capture, timestamp and bounded-buffer APIs. Our synchronous `grab` loop records local acquisition completion timestamps; it does not claim DXGI presentation timestamps.
- [TMRL](https://github.com/trackmania-rl/tmrl): reviewed README and MIT LICENSE. Useful techniques include screenshot observations, temporal histories, action/observation latency handling and replay datasets. Distributed training and Trackmania-specific state interfaces are unnecessary for this local Phase 1. No code copied.
- [Linesight](https://github.com/Linesight-RL/linesight): reviewed README; its interface targets Trackmania Nations Forever via TMInterface. Its discrete-action racing assumptions and privileged game state cannot be transplanted into MotoGP. LICENSE, LICENSE.md and LICENSE.txt at the repository root were not found during review; no permission to reuse code was inferred and no code copied.
- [ViGEmBus](https://github.com/nefarius/ViGEmBus): reviewed retirement notice and Windows driver scope. No maintained alternative was verified during this task. Stay in monitoring/coaching until one is established.
- [XInputGetState](https://learn.microsoft.com/en-us/windows/win32/api/xinput/nf-xinput-xinputgetstate), [RegisterHotKey](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-registerhotkey): API references for future hardware troubleshooting. F12 may be reserved by the debugger.
- PyPI JSON metadata: `https://pypi.org/pypi/<package>/json` for the package names above. The local install preserves upstream checksums and TLS verification.

These projects provide architectural references, not evidence of MotoGP compatibility or expected lap times. Before distributing binaries, collect bundled third-party notices and satisfy Qt and all transitive licensing requirements. No application license has been chosen on the user's behalf.
