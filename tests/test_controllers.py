import ctypes as C
import time
from types import SimpleNamespace
import pytest
from motoassist.controllers import NativeXInput,ControllerManager,SDLController
from motoassist.windows import State
from motoassist.models import InputState

class FakeGetState:
    def __init__(self,slots):self.slots=slots;self.calls=[]
    def __call__(self,slot,pointer):
        self.calls.append(slot)
        if slot not in self.slots:return 1167
        state=C.cast(pointer,C.POINTER(State)).contents
        state.pad.buttons=4096|32;state.pad.lx=-32768;state.pad.ry=32767;state.pad.lt=255;state.pad.rt=128
        return 0

def test_native_scans_all_slots_all_dlls_and_normalizes():
    first=FakeGetState(set());second=FakeGetState({3})
    def loader(name):
        if name=="xinput1_4.dll":return SimpleNamespace(XInputGetState=first)
        if name=="xinput1_3.dll":return SimpleNamespace(XInputGetState=second)
        raise OSError("not installed")
    device=NativeXInput(loader);found=device.scan()
    assert first.calls==[0,1,2,3] and second.calls==[0,1,2,3]
    assert found[0]["id"]=="xinput:3"
    sample=device.poll("xinput:3")
    assert sample.connected and sample.lx==-1 and sample.ry==1 and sample.lt==1 and sample.rt==pytest.approx(128/255)
    assert sample.buttons==4128
    second.slots.clear();assert not device.poll("xinput:3").connected
    second.slots.add(1);assert device.scan()[0]["id"]=="xinput:1"

class FakeBackend:
    def __init__(self,name="sdl2"):self.name=name;self.connected=True;self.raise_poll=False;self.closed=False
    def scan(self):return [{"id":self.name+":1","name":"Xbox test","backend":self.name}] if self.connected else []
    def poll(self,device):
        if self.raise_poll:self.raise_poll=False;raise OSError("temporary polling failure")
        return InputState(time.perf_counter(),self.connected,buttons=8192)
    def close(self):self.closed=True

def test_manager_fallback_reconnection_and_exception_recovery():
    backend=FakeBackend()
    def missing():raise OSError("XInput unavailable")
    manager=ControllerManager(factories={"xinput":missing,"sdl2":lambda:backend})
    assert manager.poll().connected and manager.active["backend"]=="sdl2"
    assert "xinput" in manager.errors
    backend.connected=False;manager.next_scan=0;assert not manager.poll().connected
    backend.connected=True;manager.next_scan=0;assert manager.poll().connected
    backend.raise_poll=True;assert not manager.poll().connected
    manager.next_scan=0;assert manager.poll().connected
    manager.close();assert backend.closed

def test_manager_explicit_selection_does_not_switch_to_another_device():
    backend=FakeBackend();manager=ControllerManager("sdl2","sdl2:missing",{"sdl2":lambda:backend})
    assert not manager.poll().connected
    manager.selected="sdl2:1";manager.next_scan=0;assert manager.poll().connected
    manager.close()

def test_actual_sdl_virtual_xbox_axes_buttons_and_detach():
    import sdl2 as s
    backend=SDLController();joystick=None;index=-1
    try:
        desc=s.SDL_VirtualJoystickDesc();desc.version=s.SDL_VIRTUAL_JOYSTICK_DESC_VERSION
        desc.type=s.SDL_JOYSTICK_TYPE_GAMECONTROLLER;desc.naxes=6;desc.nbuttons=15
        desc.vendor_id=0x045e;desc.product_id=0x028e;desc.name=b"Xbox MotoAssist automated test"
        desc.axis_mask=(1<<6)-1;desc.button_mask=(1<<15)-1
        index=s.SDL_JoystickAttachVirtualEx(C.byref(desc));assert index>=0,s.SDL_GetError()
        joystick=s.SDL_JoystickOpen(index);assert joystick
        # Make axis mapping explicit; no physical device is injected or modified.
        guid=C.create_string_buffer(33);s.SDL_JoystickGetGUIDString(s.SDL_JoystickGetDeviceGUID(index),guid,33)
        mapping=guid.value+b",Xbox MotoAssist automated test,a:b0,b:b1,x:b2,y:b3,back:b4,start:b6,leftstick:b7,rightstick:b8,leftshoulder:b9,rightshoulder:b10,dpup:b11,dpdown:b12,dpleft:b13,dpright:b14,leftx:a0,lefty:a1,rightx:a2,righty:a3,lefttrigger:a4,righttrigger:a5,"
        assert s.SDL_GameControllerAddMapping(mapping)>=0
        devices=backend.scan();device=next(d for d in devices if "MotoAssist" in d["name"])
        assert s.SDL_JoystickSetVirtualAxis(joystick,0,16384)==0
        assert s.SDL_JoystickSetVirtualAxis(joystick,1,-16384)==0
        assert s.SDL_JoystickSetVirtualAxis(joystick,5,32767)==0
        assert s.SDL_JoystickSetVirtualButton(joystick,0,1)==0
        s.SDL_JoystickUpdate();sample=backend.poll(device["id"])
        assert sample.connected and sample.buttons&4096
        assert sample.lx==pytest.approx(.5,abs=.01) and sample.ly==pytest.approx(.5,abs=.01) and sample.rt==1
        s.SDL_JoystickClose(joystick);joystick=None
        assert s.SDL_JoystickDetachVirtual(index)==0;index=-1
        assert not backend.poll(device["id"]).connected
    finally:
        if joystick:s.SDL_JoystickClose(joystick)
        if index>=0:s.SDL_JoystickDetachVirtual(index)
        backend.close()
