"""Physical Xbox input only. Backends are owned by a single polling thread."""
import ctypes as C
from dataclasses import asdict
import logging
import os
import time
from .models import InputState
from .windows import State, axis

log = logging.getLogger("motoassist.controllers")

class NativeXInput:
    def __init__(self, loader=None):
        self.functions = []
        self.diagnostics = {}
        loader = loader or getattr(C, "WinDLL", None)
        if loader is None: raise OSError("Native XInput is available only on Windows")
        for name in ("xinput1_4.dll", "xinput1_3.dll", "xinput9_1_0.dll"):
            try:
                dll = loader(name)
                fn = dll.XInputGetState
                fn.argtypes = [C.c_uint32, C.POINTER(State)]
                fn.restype = C.c_uint32
                self.functions.append((name, dll, fn))
                log.info("XInput loaded %s; state_size=%d gamepad_size=%d", name, C.sizeof(State), C.sizeof(State._fields_[1][1]))
            except (OSError, AttributeError) as exc:
                self.diagnostics[name] = str(exc)
                log.info("XInput DLL unavailable %s: %s", name, exc)
        if not self.functions: raise OSError("No XInput DLL could be loaded")
        self.routes = {}

    @staticmethod
    def _sample(state, slot):
        p = state.pad
        return InputState(time.perf_counter(), True, slot, axis(p.lx), axis(p.ly), axis(p.rx), axis(p.ry), p.lt/255, p.rt/255, p.buttons)

    def scan(self):
        devices, routes, codes = [], {}, {}
        # Check every slot and every available DLL; never stop enumeration at slot 0.
        for name, dll, fn in self.functions:
            for slot in range(4):
                state = State(); code = int(fn(slot, C.byref(state)))
                codes[f"{name}/slot{slot}"] = code
                if code == 0 and slot not in routes:
                    routes[slot] = fn
                    devices.append({"id": f"xinput:{slot}", "name": f"Xbox / XInput slot {slot}", "backend": "xinput", "dll": name})
        if codes != self.diagnostics: log.info("XInput scan return codes (0=connected,1167=disconnected): %s", codes)
        self.diagnostics = codes; self.routes = routes
        return devices

    def poll(self, device):
        slot = int(device.split(":")[1]); fn = self.routes.get(slot)
        state = State()
        if fn and fn(slot, C.byref(state)) == 0: return self._sample(state, slot)
        return InputState(time.perf_counter())
    def close(self): pass

class SDLController:
    def __init__(self):
        os.environ["SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "1"
        os.environ["SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "1"
        import sdl2
        self.s = sdl2
        sdl2.SDL_SetHint(b"SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS", b"1")
        sdl2.SDL_SetHint(b"SDL_JOYSTICK_HIDAPI", b"1")
        sdl2.SDL_SetHint(b"SDL_JOYSTICK_HIDAPI_XBOX", b"1")
        sdl2.SDL_SetHint(b"SDL_JOYSTICK_HIDAPI_XBOX_ONE", b"1")
        self.flags = sdl2.SDL_INIT_GAMECONTROLLER | sdl2.SDL_INIT_EVENTS
        if sdl2.SDL_InitSubSystem(self.flags) != 0: raise OSError(sdl2.SDL_GetError().decode(errors="replace"))
        self.handles = {}; self.inventory = []
        version = sdl2.SDL_version(); sdl2.SDL_GetVersion(C.byref(version))
        log.info("SDL %d.%d.%d initialized; background joystick monitoring enabled",version.major,version.minor,version.patch)

    def scan(self):
        s = self.s; s.SDL_PumpEvents(); s.SDL_GameControllerUpdate()
        devices = []; live = set(); occurrences = {}; inventory = []
        for index in range(s.SDL_NumJoysticks()):
            name = (s.SDL_JoystickNameForIndex(index) or b"Unknown").decode(errors="replace")
            mapped = bool(s.SDL_IsGameController(index))
            kind = s.SDL_GameControllerTypeForIndex(index) if mapped else 0
            vendor = s.SDL_JoystickGetDeviceVendor(index)
            supported = mapped and (kind in (s.SDL_CONTROLLER_TYPE_XBOX360,s.SDL_CONTROLLER_TYPE_XBOXONE) or vendor == 0x045e or "xbox" in name.lower() or "x-box" in name.lower())
            inventory.append({"index":index,"name":name,"mapped":mapped,"type":kind,"vendor":vendor,"xbox_supported":supported})
            if not supported: continue
            guid_buffer = C.create_string_buffer(33)
            s.SDL_JoystickGetGUIDString(s.SDL_JoystickGetDeviceGUID(index),guid_buffer,33)
            guid = guid_buffer.value.decode(); ordinal = occurrences.get(guid,0); occurrences[guid] = ordinal+1
            key = f"sdl:{guid}:{ordinal}"; live.add(key)
            handle = self.handles.get(key)
            if handle and not s.SDL_GameControllerGetAttached(handle): s.SDL_GameControllerClose(handle); handle = None
            if not handle: handle = s.SDL_GameControllerOpen(index)
            if not handle:
                log.warning("SDL could not open %s: %s", name, s.SDL_GetError());continue
            self.handles[key] = handle
            devices.append({"id":key,"name":name,"backend":"sdl2"})
        for key in list(self.handles):
            if key not in live: s.SDL_GameControllerClose(self.handles.pop(key))
        if inventory != self.inventory: log.info("SDL joystick inventory: %s",inventory)
        self.inventory = inventory
        return devices

    def poll(self, device):
        s = self.s; s.SDL_PumpEvents(); s.SDL_GameControllerUpdate()
        handle = self.handles.get(device)
        if not handle or not s.SDL_GameControllerGetAttached(handle): return InputState(time.perf_counter())
        axes = [s.SDL_GameControllerGetAxis(handle,i) for i in range(6)]
        # SDL sticks use positive-down Y; convert to XInput positive-up convention.
        mapping = {0:4096,1:8192,2:16384,3:32768,4:32,6:16,7:64,8:128,9:256,10:512,11:1,12:2,13:4,14:8}
        buttons = sum(mask for button,mask in mapping.items() if s.SDL_GameControllerGetButton(handle,button))
        return InputState(time.perf_counter(),True,-1,axis(axes[0]),-axis(axes[1]),axis(axes[2]),-axis(axes[3]),max(0,axes[4])/32767,max(0,axes[5])/32767,buttons)

    def close(self):
        for handle in self.handles.values(): self.s.SDL_GameControllerClose(handle)
        self.handles.clear(); self.s.SDL_QuitSubSystem(self.flags)

class ControllerManager:
    def __init__(self, backend="auto", selected="auto", factories=None):
        self.backend = backend; self.selected = selected
        self.factories = factories or {"xinput":NativeXInput,"sdl2":SDLController}
        self.backends = {}; self.errors = {}; self.devices = []; self.active = None
        self.next_scan = 0; self.next_init = 0
        self._last_status = None

    def scan(self):
        now = time.perf_counter()
        wanted = ("xinput","sdl2") if self.backend == "auto" else (self.backend,)
        if now >= self.next_init:
            for name in wanted:
                if name not in self.backends:
                    try: self.backends[name] = self.factories[name]();self.errors.pop(name,None)
                    except Exception as exc:
                        self.errors[name] = str(exc); log.warning("Controller backend %s unavailable: %s",name,exc)
            self.next_init = now+5
        devices=[]
        for name,backend in list(self.backends.items()):
            if name not in wanted: continue
            try: devices.extend(backend.scan());self.errors.pop(name,None)
            except Exception as exc: self.errors[name]=str(exc);log.exception("Controller scan failed: %s",name)
        self.devices=devices;self.next_scan=now+1
        if self.selected != "auto": self.active=next((d for d in devices if d["id"]==self.selected),None)
        else:
            self.active=next((d for d in devices if self.active and d["id"]==self.active["id"]),None) or next(iter(devices),None)
        status=(str(devices),str(self.active),str(self.errors))
        if status != self._last_status: log.info("Controller selection=%s devices=%s active=%s errors=%s",self.selected,devices,self.active,self.errors)
        self._last_status=status

    def poll(self):
        if time.perf_counter() >= self.next_scan: self.scan()
        if self.active:
            try:
                sample=self.backends[self.active["backend"]].poll(self.active["id"])
                if not sample.connected: self.next_scan=0
                return sample
            except Exception as exc:
                self.errors[self.active["backend"]]=str(exc);log.exception("Controller poll failed; rescanning")
                self.active=None;self.next_scan=time.perf_counter()+1
        return InputState(time.perf_counter())

    def report(self):
        return {"devices":list(self.devices),"active":self.active,"errors":dict(self.errors),
                "xinput":getattr(self.backends.get("xinput"),"diagnostics",{}),"sdl_inventory":getattr(self.backends.get("sdl2"),"inventory",[])}

    def close(self):
        for backend in self.backends.values():
            try: backend.close()
            except Exception: log.exception("Controller backend close failed")
