"""Deterministic simulation-only policies. No motorcycle dynamics claims."""
import math
from .models import Decision

MODES = ("Manual", "Subtle", "Balanced", "Maximum", "Experimental Autopilot")

def decide(observation, physical, now, mode="Manual", enabled=True, emergency=False):
    values = (now, observation.timestamp, physical.timestamp, observation.speed, observation.target_speed,
              observation.curvature, observation.confidence, physical.lx, physical.rt, physical.lt)
    reason = None
    if not all(math.isfinite(v) for v in values): reason = "invalid data"
    elif emergency: reason = "emergency stop"
    elif not physical.connected: reason = "controller disconnected"
    elif not 0 <= now - physical.timestamp <= 0.1: reason = "stale controller"
    elif not 0 <= now - observation.timestamp <= 0.2: reason = "stale frame"
    elif not observation.focused or not observation.gameplay: reason = "gameplay unavailable"
    elif observation.confidence < 0.8: reason = "low confidence"
    elif observation.speed < 0 or observation.target_speed < 0: reason = "invalid speed"
    elif not enabled or mode == "Manual": reason = "manual"
    elif mode not in MODES or mode == MODES[4]: reason = "mode unavailable"
    elif abs(physical.lx) > 0.8 or physical.buttons & 0x0030 == 0x0030: reason = "manual override"
    if reason:
        # Neutral hypothetical output on unsafe observations. Physical device is never intercepted.
        return Decision(0, 0, 0, False, reason)
    strength = {"Subtle": 0.15, "Balanced": 0.4, "Maximum": 0.7}[mode]
    clip = lambda v, lo, hi: max(lo, min(hi, v))
    excess = max(0, observation.speed - observation.target_speed)
    brake = clip(physical.lt + strength * excess / 40, 0, 1)
    throttle = clip(physical.rt * (1 - strength * min(1, abs(observation.curvature))) - strength * excess / 60, 0, 1)
    steer = clip(physical.lx + strength * clip(observation.curvature, -1, 1) * 0.3, -1, 1)
    return Decision(steer, throttle, brake, True, "simulation only")
