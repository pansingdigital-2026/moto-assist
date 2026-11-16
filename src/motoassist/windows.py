"""Documented Windows APIs only: XInput, window enumeration and DPI awareness."""
import ctypes as C
from ctypes import wintypes as W
import os
import time
from .models import InputState

BUTTONS = {1:"D-pad up",2:"D-pad down",4:"D-pad left",8:"D-pad right",16:"Start",32:"Back",64:"L3",128:"R3",256:"LB",512:"RB",4096:"A",8192:"B",16384:"X",32768:"Y"}

def axis(value, deadzone=0):
    x = value / (32768 if value < 0 else 32767)
    return 0.0 if abs(x) <= deadzone else (1 if x > 0 else -1) * (abs(x)-deadzone)/(1-deadzone)

class Gamepad(C.Structure):
    _fields_ = [("buttons", C.c_uint16), ("lt", C.c_uint8), ("rt", C.c_uint8), ("lx", C.c_int16), ("ly", C.c_int16), ("rx", C.c_int16), ("ry", C.c_int16)]
class State(C.Structure):
    _fields_ = [("packet", C.c_uint32), ("pad", Gamepad)]

class XInput:
    def __init__(self):
        self.get = None
        for name in ("xinput1_4", "xinput9_1_0", "xinput1_3"):
            try:
                self.dll = C.WinDLL(name)
                self.get = self.dll.XInputGetState
                self.get.argtypes = [W.DWORD, C.POINTER(State)]
                self.get.restype = W.DWORD
                break
            except OSError: pass
        if self.get is None: raise RuntimeError("Windows XInput DLL unavailable")
        self.slot = 0

    def poll(self):
        for i in [self.slot] + [j for j in range(4) if j != self.slot]:
            state = State()
            if self.get(i, C.byref(state)) == 0:
                self.slot = i
                p = state.pad
                return InputState(time.perf_counter(), True, i, axis(p.lx), axis(p.ly), axis(p.rx), axis(p.ry), p.lt/255, p.rt/255, p.buttons)
        return InputState(time.perf_counter())

class Windows:
    def __init__(self):
        if os.name != "nt": raise RuntimeError("Live capture requires Windows; use --simulate")
        self.user = C.WinDLL("user32", use_last_error=True)
        self.user.GetForegroundWindow.restype = W.HWND
        self.user.GetWindowTextLengthW.argtypes = [W.HWND]
        self.user.GetWindowTextW.argtypes = [W.HWND, W.LPWSTR, C.c_int]
        self.user.IsWindowVisible.argtypes = [W.HWND]
        self.user.IsIconic.argtypes = [W.HWND]
        self.user.GetClientRect.argtypes = [W.HWND, C.POINTER(W.RECT)]
        self.user.ClientToScreen.argtypes = [W.HWND, C.POINTER(W.POINT)]
        self.callback_type = C.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)
        self.user.EnumWindows.argtypes = [self.callback_type, W.LPARAM]

    def find(self, title):
        matches = []
        def visit(hwnd, _):
            if self.user.IsWindowVisible(hwnd) and not self.user.IsIconic(hwnd):
                buf = C.create_unicode_buffer(self.user.GetWindowTextLengthW(hwnd)+1)
                self.user.GetWindowTextW(hwnd, buf, len(buf))
                if title.casefold() in buf.value.casefold() and "motoassist" not in buf.value.casefold():
                    matches.append((hwnd, buf.value))
            return True
        self.user.EnumWindows(self.callback_type(visit), 0)
        foreground = self.user.GetForegroundWindow()
        if not matches: return None
        hwnd, text = next((m for m in matches if m[0] == foreground), matches[0])
        rect, point = W.RECT(), W.POINT()
        if not self.user.GetClientRect(hwnd, C.byref(rect)) or not self.user.ClientToScreen(hwnd, C.byref(point)): return None
        return {"title": text, "focused": hwnd == foreground, "rect": (point.x, point.y, point.x+rect.right, point.y+rect.bottom)}

def enable_dpi_awareness():
    if os.name == "nt":
        try:
            user = C.WinDLL("user32")
            user.SetProcessDpiAwarenessContext.argtypes = [C.c_void_p]
            user.SetProcessDpiAwarenessContext(C.c_void_p(-4))
        except (AttributeError, OSError): pass
