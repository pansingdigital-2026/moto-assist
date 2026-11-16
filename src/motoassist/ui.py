from dataclasses import asdict
import json
import logging
import os
from pathlib import Path
import threading
import time
import psutil
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QIcon, QImage, QPixmap, QPainter
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QTabWidget, QFormLayout, QProgressBar, QSlider, QCheckBox, QPlainTextEdit,
    QMessageBox, QSystemTrayIcon, QMenu, QSpinBox, QDoubleSpinBox, QLineEdit, QListWidget, QGroupBox)
from .config import Settings, PRESETS
from .database import Database
from .decisions import MODES, decide
from .hotkeys import Hotkeys
from .models import InputState, Observation
from .runtime import Runtime
from .system import system_info
from .windows import BUTTONS

STYLE = """
QWidget { background:#171c24; color:#f2f5fa; font-size:13px; }
QMainWindow,QTabWidget::pane { background:#171c24; }
QPushButton { background:#166cda; border:0; border-radius:5px; padding:9px 15px; }
QPushButton:disabled { background:#323b49; color:#8993a4; }
QLineEdit,QComboBox,QSpinBox,QDoubleSpinBox,QPlainTextEdit,QListWidget { background:#242d3b; padding:5px; border:1px solid #39465a; }
QProgressBar { background:#242d3b; border:0; text-align:center; min-height:18px; }
QProgressBar::chunk { background:#1699dd; }
QTabBar::tab { padding:10px; background:#242d3b; }
QTabBar::tab:selected { background:#166cda; }
QGroupBox { border:1px solid #39465a; margin-top:12px; padding:15px; }
"""

class Window(QMainWindow):
    def __init__(self, settings, directory, simulate=False, video=None):
        super().__init__()
        self.settings, self.directory = settings, directory
        self.simulate, self.video = simulate, video
        self.runtime = Runtime(settings, simulate, video)
        self.db = Database(directory / "tracks.sqlite3")
        self.quitting = False
        self.last_sequence = -1
        self.info = None
        self.process = psutil.Process()
        self.process.cpu_percent()
        self.setWindowTitle("MotoAssist • Phase 1")
        self.resize(990, 820)
        self.setStyleSheet(STYLE)
        pix = QPixmap(32,32); pix.fill(QColor("#166cda"))
        painter = QPainter(pix); painter.setPen(QColor("white")); painter.drawText(pix.rect(), Qt.AlignCenter, "M"); painter.end()
        self.icon = QIcon(pix); self.setWindowIcon(self.icon)
        self.tabs = QTabWidget(); self.setCentralWidget(self.tabs)
        self.dashboard(); self.assistance(); self.learning(); self.performance(); self.preferences()
        self.tray = QSystemTrayIcon(self.icon, self)
        menu = QMenu(self)
        menu.addAction("Show MotoAssist", self.restore)
        menu.addAction("Emergency stop", self.emergency_stop)
        menu.addAction("Quit", self.quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda reason: self.restore() if reason == QSystemTrayIcon.Trigger else None)
        if QSystemTrayIcon.isSystemTrayAvailable(): self.tray.show()
        self.hotkeys = Hotkeys(QApplication.instance(), settings.hotkeys, self.shortcut)
        suffix = " Global shortcuts unavailable: " + ", ".join(self.hotkeys.failed) if self.hotkeys.failed else ""
        self.statusBar().showMessage(("Simulation — no controller output" if simulate else "Monitor only — no controller output")+suffix)
        self.runtime.start()
        threading.Thread(target=self.detect_system, daemon=True, name="system-info").start()
        self.timer = QTimer(self); self.timer.timeout.connect(self.refresh); self.timer.start(100)
        self.metrics_timer = QTimer(self); self.metrics_timer.timeout.connect(self.refresh_metrics); self.metrics_timer.start(1000)

    def page(self, name):
        widget = QWidget(); layout = QVBoxLayout(widget); layout.setSpacing(12); layout.setContentsMargins(20,20,20,20)
        self.tabs.addTab(widget, name); return layout

    def dashboard(self):
        layout = self.page("Dashboard")
        title = QLabel("MotoAssist  /  MONITOR & RECORD"); title.setStyleSheet("font-size:22px; font-weight:bold;"); layout.addWidget(title)
        self.connection = QLabel(); layout.addWidget(self.connection)
        self.gpu = QLabel("Detecting system hardware…"); self.gpu.setWordWrap(True); layout.addWidget(self.gpu)
        self.preview = QLabel("Waiting for frames"); self.preview.setAlignment(Qt.AlignCenter); self.preview.setMinimumHeight(250); layout.addWidget(self.preview, 1)
        self.analog = {}
        form = QFormLayout()
        for name in ("lx", "ly", "rx", "ry", "lt", "rt"):
            bar = QProgressBar(); bar.setRange(-100 if name[0] in "lr" and name[1] in "xy" else 0,100)
            self.analog[name] = bar; form.addRow(name.upper(),bar)
        layout.addLayout(form)
        self.buttons = QLabel(); layout.addWidget(self.buttons)
        layout.addWidget(QLabel("Speed, target speed and lap timing: unavailable until gameplay recognition is implemented."))
        row = QHBoxLayout()
        for text, fn in (("Start recording",self.record), ("Stop recording",self.stop_record), ("Emergency stop",self.emergency_stop), ("Hide to tray",self.hide_to_tray)):
            button = QPushButton(text); button.clicked.connect(fn); row.addWidget(button)
        layout.addLayout(row)

    def assistance(self):
        layout = self.page("Riding Assistance")
        label = QLabel("Live riding assistance is not available in Phase 1. The controls below exercise synthetic decisions only.")
        label.setWordWrap(True); layout.addWidget(label)
        self.mode = QComboBox(); self.mode.addItems(MODES); layout.addWidget(self.mode)
        self.sim_enabled = QCheckBox("Enable simulated decisions (never sent to a game)"); layout.addWidget(self.sim_enabled)
        form = QFormLayout(); self.sim_values = {}
        for name, limits, value in (("Speed (km/h)",(0,400),180),("Target speed (km/h)",(0,400),120),("Curvature",(-1,1),0.4),("Confidence",(0,1),0.95)):
            spin = QDoubleSpinBox(); spin.setRange(*limits); spin.setValue(value); spin.setSingleStep(0.05 if limits[1] == 1 else 5)
            self.sim_values[name] = spin; form.addRow(name,spin)
        layout.addLayout(form)
        self.sim_result = QLabel(); self.sim_result.setWordWrap(True); layout.addWidget(self.sim_result)
        self.flags = {}
        for name in ("Automatic braking", "Steering correction", "Throttle correction", "Trail braking", "Racing line correction", "Corner speed management", "Crash prevention", "Automatic tuck-in"):
            row = QHBoxLayout(); check=QCheckBox(name+" — future live feature"); check.setEnabled(False)
            slider=QSlider(Qt.Horizontal); slider.setRange(0,100); slider.setEnabled(False)
            row.addWidget(check); row.addWidget(slider); layout.addLayout(row)
        layout.addStretch()

    def learning(self):
        layout = self.page("Track Learning")
        label=QLabel("Reference recording is available. Automatic profile generation, landmarks and HUD recognition are planned for later phases.\nGame-assisted reference laps contain physical input only; internal game corrections are unknown.")
        label.setWordWrap(True); layout.addWidget(label)
        self.circuit=QLineEdit(); self.circuit.setPlaceholderText("Circuit label (user supplied)"); layout.addWidget(self.circuit)
        self.category=QLineEdit(); self.category.setPlaceholderText("Motorcycle / category / weather notes"); layout.addWidget(self.category)
        self.builtin=QCheckBox("In-game assists enabled or unknown (not controller ground truth)"); self.builtin.setChecked(True); layout.addWidget(self.builtin)
        row=QHBoxLayout()
        for text, fn in (("Start reference recording",self.record),("Stop recording",self.stop_record),("Refresh history",self.history)):
            button=QPushButton(text); button.clicked.connect(fn); row.addWidget(button)
        layout.addLayout(row)
        self.record_status=QLabel("Not recording"); self.record_status.setWordWrap(True); layout.addWidget(self.record_status)
        self.sessions=QListWidget(); layout.addWidget(self.sessions); self.history()
        layout.addWidget(QLabel("Sessions are portable folders containing JPEG frames, frames.jsonl and manifest.json."))

    def performance(self):
        layout=self.page("Performance")
        self.metrics=QLabel(); self.metrics.setWordWrap(True); layout.addWidget(self.metrics)
        layout.addWidget(QLabel("Inference and controller output latency: N/A (no model or virtual output).\nPer-process GPU usage: unavailable. Capture targets are not guarantees.\nProcessing overruns lower the capture target; OBS/GPU contention detection is a later feature."))
        layout.addStretch()

    def preferences(self):
        layout=self.page("Settings"); form=QFormLayout(); self.fields={}
        for name in ("game_title", "preset", "device_idx", "output_idx", "monitor_left", "monitor_top", "deadzone", "controller_stop_mask"):
            value=getattr(self.settings,name)
            if name=="preset": field=QComboBox(); field.addItems(PRESETS); field.setCurrentText(value)
            elif isinstance(value,float): field=QDoubleSpinBox(); field.setRange(0,0.89); field.setSingleStep(0.01); field.setValue(value)
            elif isinstance(value,int): field=QSpinBox(); field.setRange(-32768,65535); field.setValue(value)
            else: field=QLineEdit(value)
            self.fields[name]=field; form.addRow(name.replace("_"," ").title(),field)
        self.key_fields={}
        for action,key in self.settings.hotkeys.items():
            field=QLineEdit(key); self.key_fields[action]=field; form.addRow("Shortcut: "+action,field)
        layout.addLayout(form)
        button=QPushButton("Save settings (restart application to apply)"); button.clicked.connect(self.save_settings); layout.addWidget(button)
        label=QLabel(f"Data folder: {self.directory}\nDead zone is for future mapping; dashboard and recordings preserve raw axes.\nCapture requires the game on the selected DXcam output. Set its Windows desktop origin if it is not (0, 0).\nF12 is reserved by Windows on some systems; configure another key if registration fails. Back + Start also stops recording.")
        label.setWordWrap(True); layout.addWidget(label); layout.addStretch()

    def save_settings(self):
        try:
            values=asdict(self.settings)
            for name,field in self.fields.items():
                values[name]=field.currentText() if isinstance(field,QComboBox) else field.text() if isinstance(field,QLineEdit) else field.value()
            values["hotkeys"]={action:field.text().strip().upper() for action,field in self.key_fields.items()}
            Settings(**values).save(self.directory/"settings.json")
            self.statusBar().showMessage("Settings saved. Restart MotoAssist to apply.")
        except Exception as exc: self.error(exc)

    def detect_system(self): self.info=system_info()
    def history(self):
        self.sessions.clear()
        for created,source,path in self.db.sessions(): self.sessions.addItem(f"{created} • {source} • {path}")

    def record(self):
        try:
            path=self.runtime.start_recording(self.directory/"recordings", {"circuit_label": self.circuit.text(), "conditions": self.category.text(), "builtin_assists_enabled_or_unknown": self.builtin.isChecked()})
            recorder=self.runtime.recorder
            self.db.record_session(path,recorder.meta["source"])
            self.history(); logging.info("Recording started %s; assistance_active=false",path)
        except Exception as exc: self.error(exc)

    def stop_record(self):
        try:
            recorder=self.runtime.recorder
            path=self.runtime.stop_recording()
            if recorder and recorder.error: raise RuntimeError(recorder.error)
            if path: self.record_status.setText(f"Saved {path}"); logging.info("Recording stopped %s",path)
        except Exception as exc: self.error(exc)

    def emergency_stop(self):
        self.runtime.emergency=False
        self.sim_enabled.setChecked(False); self.mode.setCurrentText("Manual")
        self.stop_record(); self.statusBar().showMessage("Emergency stop: recording stopped; manual control. No virtual output exists.")
        logging.warning("Emergency stop; assistance_active=false")

    def shortcut(self,action):
        if action=="record": self.stop_record() if self.runtime.recorder else self.record()
        elif action=="stop": self.emergency_stop()
        elif action=="assist": self.sim_enabled.setChecked(not self.sim_enabled.isChecked())
        elif action=="mode": self.mode.setCurrentIndex((self.mode.currentIndex()+1)%len(MODES))
        else: self.statusBar().showMessage(f"{action.title()} live assistance is unavailable in Phase 1.")

    def refresh(self):
        if self.runtime.emergency: self.emergency_stop()
        frame,sample,status,fps=self.runtime.snapshot()
        age=time.perf_counter()-sample.timestamp
        connected=sample.connected and age<=0.1
        self.connection.setText(f"{'SIMULATION' if self.simulate else 'VIDEO REPLAY' if self.video else 'WINDOW MONITOR'} • {status} • Controller: {'connected' if connected else 'disconnected / stale'}")
        self.connection.setStyleSheet("color:#48d89b" if connected else "color:#f4bd64")
        for name,bar in self.analog.items():
            value=getattr(sample,name) if connected else 0
            bar.setValue(round(value*100)); bar.setFormat(f"{value:+.3f}")
        self.buttons.setText("Buttons: "+(", ".join(label for bit,label in BUTTONS.items() if sample.buttons & bit) if connected else "none"))
        if frame and time.perf_counter()-frame.timestamp<=0.5:
            if frame.sequence!=self.last_sequence:
                image=frame.image; h,w,_=image.shape
                qimage=QImage(image.data,w,h,image.strides[0],QImage.Format_BGR888).copy()
                self.preview.setPixmap(QPixmap.fromImage(qimage).scaled(760,300,Qt.KeepAspectRatio,Qt.SmoothTransformation)); self.last_sequence=frame.sequence
        else: self.preview.clear(); self.preview.setText("No fresh gameplay frame")
        if self.info:
            self.gpu.setText("GPU: "+", ".join(g.get("Name","Unknown") for g in self.info["gpus"])+f"  |  RAM: {self.info['ram_gib']} GiB"+(" • "+self.info["gpu_error"] if self.info["gpu_error"] else ""))
        now=time.perf_counter(); values=[v.value() for v in self.sim_values.values()]
        decision=decide(Observation(now,*values),InputState(now,True,lx=0.1,rt=0.8),now,self.mode.currentText(),self.sim_enabled.isChecked())
        self.sim_result.setText(f"SYNTHETIC DECISION: {decision.reason} | steering {decision.steering:.3f} | throttle {decision.throttle:.3f} | brake {decision.brake:.3f}")
        if self.runtime.recorder:
            r=self.runtime.recorder; self.record_status.setText(f"Recording: {r.saved} frames • {r.dropped} dropped • {r.path}"+(f" • ERROR: {r.error}" if r.error else ""))

    def refresh_metrics(self):
        frame,_,_,fps=self.runtime.snapshot()
        fresh=frame and time.perf_counter()-frame.timestamp<0.5
        self.metrics.setText(f"Capture: {fps if fresh else 0:.1f} FPS • current target {self.runtime.target_fps:.1f} FPS\nLast capture call: {frame.capture_ms if fresh else 0:.2f} ms\nProcess CPU: {self.process.cpu_percent():.1f}% (may exceed 100% across cores)\nProcess RAM: {self.process.memory_info().rss/1024**2:.1f} MiB\nDetection confidence: unavailable; no gameplay recognition yet")

    def error(self,exc):
        logging.error("UI operation: %s",exc); QMessageBox.warning(self,"MotoAssist",str(exc))
    def restore(self): self.showNormal(); self.raise_(); self.activateWindow()
    def hide_to_tray(self):
        if QSystemTrayIcon.isSystemTrayAvailable(): self.hide()
        else: self.statusBar().showMessage("No system tray is available; window remains visible.")
    def quit(self): self.quitting=True; self.close()
    def closeEvent(self,event):
        if not self.quitting and self.settings.minimize_to_tray and QSystemTrayIcon.isSystemTrayAvailable(): self.hide(); event.ignore(); return
        self.timer.stop(); self.metrics_timer.stop(); self.hotkeys.close()
        try: self.runtime.stop()
        except Exception as exc: self.error(exc); event.ignore(); return
        self.db.close(); self.tray.hide(); event.accept(); QApplication.instance().quit()
