from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class InputState:
    timestamp: float
    connected: bool = False
    slot: int = -1
    lx: float = 0.0
    ly: float = 0.0
    rx: float = 0.0
    ry: float = 0.0
    lt: float = 0.0
    rt: float = 0.0
    buttons: int = 0

@dataclass(frozen=True)
class Frame:
    sequence: int
    timestamp: float
    image: Any
    capture_ms: float = 0.0

@dataclass(frozen=True)
class Observation:
    timestamp: float
    speed: float
    target_speed: float
    curvature: float
    confidence: float
    gameplay: bool = True
    focused: bool = True

@dataclass(frozen=True)
class Decision:
    steering: float
    throttle: float
    brake: float
    active: bool
    reason: str
