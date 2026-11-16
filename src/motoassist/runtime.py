import collections
from dataclasses import asdict
import logging
import math
import os
import threading
import time
import cv2
import numpy as np
from .config import PRESETS
from .models import Frame, InputState
from .recording import Recorder
from .windows import Windows, XInput

class Runtime:
    def __init__(self, settings, simulate=False, video=None):
        self.settings, self.simulate, self.video = settings, simulate, video
        self.lock = threading.RLock()
        self.stop_event = threading.Event()
        self.inputs = collections.deque(maxlen=512)
        self.frame = None
        self.recorder = None
        self.status = "Starting"
        self.game = None
        self.fps = 0.0
        self.target_fps = PRESETS[settings.preset][0]
        self.emergency = False
        self.threads = []

    def start(self):
        for name, fn in (("controller", self._controller), ("capture", self._capture)):
            thread = threading.Thread(target=fn, name=name, daemon=True)
            self.threads.append(thread); thread.start()

    def _controller(self):
        try:
            device = XInput() if not self.simulate and not self.video else None
            stop_held = False
            while not self.stop_event.is_set():
                now = time.perf_counter()
                sample = device.poll() if device else InputState(now, True, 0, math.sin(now)*0.5, 0, 0, 0, max(0, math.sin(now/2))*0.4, 0.65, 0)
                with self.lock: self.inputs.append(sample)
                pressed = sample.buttons & self.settings.controller_stop_mask == self.settings.controller_stop_mask
                if pressed and not stop_held:
                    self.emergency = True
                stop_held = pressed
                self.stop_event.wait(0.008)
        except Exception:
            logging.exception("Controller polling failed")
            with self.lock: self.inputs.append(InputState(time.perf_counter()))

    def sample_for(self, timestamp):
        with self.lock:
            return next((s for s in reversed(self.inputs) if s.timestamp <= timestamp), None)

    def snapshot(self):
        with self.lock:
            return self.frame, self.inputs[-1] if self.inputs else InputState(time.perf_counter()), self.status, self.fps

    def _capture(self):
        camera = video = None
        try:
            windows = None
            if self.video:
                video = cv2.VideoCapture(str(self.video))
                if not video.isOpened(): raise RuntimeError("Cannot open prerecorded video")
                fps = video.get(cv2.CAP_PROP_FPS)
                if math.isfinite(fps) and fps > 0: self.target_fps = min(self.target_fps, fps)
            elif not self.simulate:
                windows = Windows()
                import dxcam
                camera = dxcam.create(device_idx=self.settings.device_idx, output_idx=self.settings.output_idx, output_color="BGR", max_buffer_len=2)
            seq = 0
            stamps = collections.deque(maxlen=120)
            while not self.stop_event.is_set():
                started = time.perf_counter()
                image = None
                if windows:
                    self.game = windows.find(self.settings.game_title)
                    if not self.game or not self.game["focused"]:
                        with self.lock: self.frame = None; self.status = "Game not found" if not self.game else "Game unfocused — capture suspended"; self.fps = 0
                        self.stop_event.wait(0.15); continue
                    left, top, right, bottom = self.game["rect"]
                    region = (left-self.settings.monitor_left, top-self.settings.monitor_top, right-self.settings.monitor_left, bottom-self.settings.monitor_top)
                    if region[0] < 0 or region[1] < 0 or region[2] > camera.width or region[3] > camera.height or right <= left or bottom <= top:
                        with self.lock: self.frame = None; self.status = "Game outside selected output; check monitor origin and DXcam indices"; self.fps = 0
                        self.stop_event.wait(0.5); continue
                    image = camera.grab(region=region)
                elif video:
                    ok, image = video.read()
                    if not ok:
                        with self.lock: self.status = "Video ended"; self.frame = None; self.fps = 0
                        break
                else:
                    image = np.zeros((540, 960, 3), np.uint8)
                    cv2.fillPoly(image, [np.array([[150,540],[430,180],[530,180],[810,540]])], (55,55,55))
                    cv2.line(image, (480+int(math.sin(started)*40),540), (480,180), (220,180,40), 4)
                    cv2.putText(image, "SIMULATED FRAME - NO GAME DATA", (40,80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)
                if image is not None:
                    acquired = time.perf_counter()
                    width = PRESETS[self.settings.preset][1]
                    if image.shape[1] > width:
                        image = cv2.resize(image, (width, round(image.shape[0]*width/image.shape[1])), interpolation=cv2.INTER_AREA)
                    image.flags.writeable = False
                    seq += 1
                    frame = Frame(seq, acquired, image, (acquired-started)*1000)
                    stamps.append(acquired)
                    with self.lock:
                        self.frame = frame
                        self.status = "Synthetic capture" if self.simulate else "Video replay (synthetic controller)" if video else self.game["title"]
                        self.fps = (len(stamps)-1)/(stamps[-1]-stamps[0]) if len(stamps)>1 else 0
                        if self.recorder: self.recorder.submit(frame, self.sample_for(acquired))
                elapsed = time.perf_counter()-started
                # Reduce demand when processing cannot sustain its target; never grow a frame backlog.
                if elapsed > 1/self.target_fps * 1.5: self.target_fps = max(10, self.target_fps*0.95)
                self.stop_event.wait(max(0, 1/self.target_fps-elapsed))
        except Exception as exc:
            logging.exception("Capture failed")
            with self.lock: self.status = str(exc); self.frame = None; self.fps = 0
        finally:
            if camera: camera.release()
            if video: video.release()

    def start_recording(self, root, metadata=None):
        with self.lock:
            if self.recorder: return self.recorder.path
            if self.frame is None or time.perf_counter()-self.frame.timestamp > 0.2: raise RuntimeError("No fresh frame. Start simulation or focus the game first.")
            source = "video-replay" if self.video else "simulation" if self.simulate else "windows"
            self.recorder = Recorder(root, source, asdict(self.settings), metadata=metadata)
            return self.recorder.path

    def stop_recording(self):
        with self.lock:
            recorder, self.recorder = self.recorder, None
        if recorder is None: return None
        try: return recorder.stop()
        except Exception:
            with self.lock: self.recorder = recorder
            raise

    def stop(self):
        self.stop_event.set()
        for thread in self.threads: thread.join(timeout=3)
        self.stop_recording()
        if any(thread.is_alive() for thread in self.threads):
            raise RuntimeError("A device worker is still stopping; retry Quit after it returns")
