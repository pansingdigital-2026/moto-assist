import ctypes
from ctypes import wintypes
import os
from PySide6.QtCore import QAbstractNativeEventFilter

class Hotkeys(QAbstractNativeEventFilter):
    def __init__(self, app, mapping, callback):
        super().__init__()
        self.app, self.callback = app, callback
        self.registered = {}
        self.failed = []
        if os.name == "nt":
            self.user = ctypes.WinDLL("user32", use_last_error=True)
            self.user.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
            self.user.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
            for index, (action, key) in enumerate(mapping.items(), 1):
                if self.user.RegisterHotKey(None, index, 0x4000, 0x70+int(key[1:])-1): self.registered[index] = action
                else: self.failed.append(key)
            app.installNativeEventFilter(self)
    def nativeEventFilter(self, event_type, message):
        msg = wintypes.MSG.from_address(int(message))
        if msg.message == 0x0312 and int(msg.wParam) in self.registered:
            self.callback(self.registered[int(msg.wParam)])
            return True, 0
        return False, 0
    def close(self):
        for index in self.registered: self.user.UnregisterHotKey(None, index)
        self.registered.clear()
        self.app.removeNativeEventFilter(self)
