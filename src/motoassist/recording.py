"""Bounded asynchronous JPEG + JSONL recorder with monotonic sample association."""
from dataclasses import asdict
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import queue
import shutil
import threading
import uuid
import cv2

class Recorder:
    def __init__(self, root, source, settings, capacity=8, metadata=None):
        self.path = Path(root) / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:8])
        self.path.mkdir(parents=True)
        self.meta = {"schema_version": 1, "source": source, "assistance_active": False,
                     "input_kind": "physical" if source == "windows" else "synthetic", "settings": settings,
                     "clock": "perf_counter seconds; frame acquisition completion and controller sample completion",
                     "association": "latest controller sample at or before frame acquisition completion; invalid after 100 ms",
                     "reference_warning": "Physical inputs do not include internal game assists", "complete": False}
        self.meta["reference_labels"] = dict(metadata or {})
        self.queue = queue.Queue(capacity)
        self.lock = threading.Lock()
        self.closed = False
        self.saved = self.dropped = 0
        self.error = None
        self.stop_event = threading.Event()
        self._manifest()
        self.thread = threading.Thread(target=self._run, name="recording", daemon=True)
        self.thread.start()

    def _manifest(self):
        self.meta.update(saved_frames=self.saved, dropped_frames=self.dropped, error=self.error)
        tmp = self.path / "manifest.tmp"
        tmp.write_text(json.dumps(self.meta, indent=2), encoding="utf-8")
        tmp.replace(self.path / "manifest.json")

    def submit(self, frame, physical):
        with self.lock:
            if self.closed or self.error: return False
            try: self.queue.put_nowait((frame, physical)); return True
            except queue.Full: self.dropped += 1; return False

    def _run(self):
        try:
            with (self.path / "frames.jsonl").open("w", encoding="utf-8") as log:
                while not self.stop_event.is_set() or not self.queue.empty():
                    try: frame, physical = self.queue.get(timeout=0.05)
                    except queue.Empty: continue
                    if shutil.disk_usage(self.path).free < 256 * 1024**2: raise OSError("Recording stopped: less than 256 MiB disk space")
                    filename = f"{frame.sequence:09d}.jpg"
                    if not cv2.imwrite(str(self.path / filename), frame.image, [cv2.IMWRITE_JPEG_QUALITY, 85]): raise OSError("JPEG write failed")
                    age = frame.timestamp - physical.timestamp if physical else None
                    row = {"sequence": frame.sequence, "timestamp": frame.timestamp, "file": filename,
                           "capture_ms": frame.capture_ms, "input": asdict(physical) if physical else None,
                           "input_age_ms": age*1000 if age is not None else None,
                           "input_valid": bool(physical and physical.connected and 0 <= age <= 0.1),
                           "assistance_active": False}
                    log.write(json.dumps(row) + "\n"); log.flush()
                    self.saved += 1
        except Exception as exc:
            self.error = str(exc)
            logging.exception("Recording writer failed")
        finally:
            self.meta["complete"] = self.error is None and self.stop_event.is_set()
            try: self._manifest()
            except OSError as exc: self.error = str(exc)

    def stop(self):
        with self.lock: self.closed = True; self.stop_event.set()
        self.thread.join(timeout=15)
        if self.thread.is_alive(): raise RuntimeError("Recording still draining; do not close until writing finishes")
        return self.path
