import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

PRESETS = {"Lightweight": (30, 960), "Balanced": (60, 1280), "Performance": (120, 1920)}

def data_dir():
    return Path(os.environ.get("MOTOASSIST_DATA_DIR") or (Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local/share")) / "MotoAssist"))

@dataclass
class Settings:
    game_title: str = "MotoGP"
    preset: str = "Lightweight"
    device_idx: int = 0
    output_idx: int = 0
    monitor_left: int = 0
    monitor_top: int = 0
    deadzone: float = 0.12
    minimize_to_tray: bool = True
    controller_stop_mask: int = 0x0030  # Back + Start
    hotkeys: dict = field(default_factory=lambda: {"record": "F6", "brake": "F7", "assist": "F8", "steer": "F9", "mode": "F10", "throttle": "F11", "stop": "F12"})

    def validate(self):
        if not self.game_title.strip(): raise ValueError("Game title must not be empty")
        if self.preset not in PRESETS: raise ValueError("Unknown performance preset")
        if not 0 <= self.deadzone < 0.9: raise ValueError("Dead zone must be between 0 and 0.89")
        if self.device_idx < 0 or self.output_idx < 0: raise ValueError("Device indices must be nonnegative")
        if not 1 <= self.controller_stop_mask <= 65535: raise ValueError("Invalid controller stop mask")
        if set(self.hotkeys) != {"record", "brake", "assist", "steer", "mode", "throttle", "stop"}: raise ValueError("All shortcut actions are required")
        if len(set(self.hotkeys.values())) != 7 or any(v not in {f"F{i}" for i in range(1, 25)} for v in self.hotkeys.values()): raise ValueError("Shortcuts must be distinct F1-F24 keys")
        return self

    @classmethod
    def load(cls, path):
        if not path.exists(): return cls()
        return cls(**json.loads(path.read_text(encoding="utf-8"))).validate()

    def save(self, path):
        self.validate()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
        tmp.replace(path)
