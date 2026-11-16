"""Recognition, controller diagnostics and reference-profile desktop workflows."""
import json
from pathlib import Path
import queue
import threading
import time
import uuid
import cv2
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage,QPixmap
from PySide6.QtWidgets import (QLabel,QPushButton,QHBoxLayout,QComboBox,QTableWidget,QTableWidgetItem,QPlainTextEdit,
    QFileDialog,QDialog,QVBoxLayout,QListWidget,QListWidgetItem,QMessageBox,QAbstractItemView,QLineEdit,QInputDialog)
from .calibration import CalibrationDialog
from .learning import generate_profile,import_profile,export_profile,load_jsonl
from .analyze_video import analyze_video
from .vision import MODULES,annotate

class Phase2UI:
    def phase2_pages(self):
        self.job_queue=queue.Queue();self.job_thread=None;self.job_cancel=threading.Event();self._controller_ids=None
        layout=self.page("Recognition")
        label=QLabel("Local OCR and calibrated visual estimates. Values remain unknown when evidence is weak. Nothing controls the game.");label.setWordWrap(True);layout.addWidget(label)
        self.analysis_preview=QLabel("Analyzed frame preview");self.analysis_preview.setAlignment(Qt.AlignCenter);layout.addWidget(self.analysis_preview)
        self._shown_observation=None
        self.hud_values=QLabel("Waiting for analysis…");self.hud_values.setWordWrap(True);layout.addWidget(self.hud_values)
        row=QHBoxLayout()
        for text,fn in (("Calibrate last captured frame",self.calibrate_current),("Calibrate screenshot",self.calibrate_image),("Analyze video to reference session",self.analyze_file)):
            button=QPushButton(text);button.clicked.connect(fn);row.addWidget(button)
        layout.addLayout(row)
        self.recognition_table=QTableWidget(len(MODULES),5);self.recognition_table.setHorizontalHeaderLabels(["Module","Status","Confidence","Value","Details"])
        for row,name in enumerate(MODULES):
            for col,text in enumerate((name,"waiting","—","unknown","Waiting for a fresh analyzed frame")):
                self.recognition_table.setItem(row,col,QTableWidgetItem(text))
        self.recognition_table.setEditTriggers(QAbstractItemView.NoEditTriggers);layout.addWidget(self.recognition_table)
        self.recognition_table.horizontalHeader().setStretchLastSection(True)
        layout=self.page("Diagnostics")
        row=QHBoxLayout();self.backend_choice=QComboBox();self.backend_choice.addItems(("auto","xinput","sdl2"));self.backend_choice.setCurrentText(self.settings.controller_backend)
        self.device_choice=QComboBox();self.device_choice.addItem("Automatic Xbox selection","auto")
        row.addWidget(QLabel("Backend"));row.addWidget(self.backend_choice);row.addWidget(self.device_choice,1)
        refresh=QPushButton("Refresh / reconnect");refresh.clicked.connect(self.refresh_controller);row.addWidget(refresh)
        select=QPushButton("Use selected controller");select.clicked.connect(self.choose_controller);row.addWidget(select);layout.addLayout(row)
        self.hardware_report=QPlainTextEdit();self.hardware_report.setReadOnly(True);layout.addWidget(self.hardware_report)
        label=QLabel("XInput slots 0–3 and SDL2 Xbox-compatible devices are enumerated. The same controller may appear under both APIs; only one backend is read. SDL2 allows background input. No driver is installed. Run controller_test.bat for an independent diagnostic log.")
        label.setWordWrap(True);layout.addWidget(label)
        self.job_status=QLabel("No background task");layout.addWidget(self.job_status)
        self.profile_controls()

    def profile_controls(self):
        layout=self.sessions.parentWidget().layout()
        self.sessions.setSelectionMode(QAbstractItemView.ExtendedSelection)
        row=QHBoxLayout()
        self.bike_category=QLineEdit("MotoGP");self.bike_model=QLineEdit("unspecified");self.weather=QLineEdit("dry")
        for name,field in (("Category",self.bike_category),("Bike",self.bike_model),("Weather",self.weather)):row.addWidget(QLabel(name));row.addWidget(field)
        layout.addLayout(row)
        row=QHBoxLayout()
        for text,fn in (("Mark lap boundary ("+self.settings.hotkeys["lap"]+")",self.mark_lap),("Generate profile from selected sessions",self.generate_selected),("Edit recorded lap boundaries",self.edit_boundaries)):
            button=QPushButton(text);button.clicked.connect(fn);row.addWidget(button)
        layout.addLayout(row)
        layout.addWidget(QLabel("Mark the start/finish line before lap 1, after lap 1 and after lap 2. Select stopped sessions above. Profiles use elapsed-lap-time alignment, not world position."))
        self.profiles_list=QListWidget();layout.addWidget(self.profiles_list)
        row=QHBoxLayout()
        for text,fn in (("Review",self.review_profile),("Import",self.import_selected),("Export",self.export_selected),("Delete",self.delete_selected)):
            button=QPushButton(text);button.clicked.connect(fn);row.addWidget(button)
        layout.addLayout(row);self.refresh_profiles()

    def calibrate_current(self):
        frame=self.runtime.calibration_frame
        if frame is None:self.error("Capture a gameplay frame first, or calibrate a screenshot.");return
        self.calibrate(frame.image)
    def calibrate_image(self):
        path,_=QFileDialog.getOpenFileName(self,"Choose gameplay screenshot","","Images (*.png *.jpg *.jpeg *.bmp)")
        if path:
            image=cv2.imread(path)
            if image is None:self.error("Image could not be decoded")
            else:self.calibrate(image)
    def calibrate(self,image):
        observation=self.runtime.observation
        dialog=CalibrationDialog(image,self.settings.hud_rois,observation.get("hud_proposals") if observation else None,self)
        if dialog.exec()==QDialog.Accepted:
            try:
                self.runtime.update_calibration(dialog.canvas.rois);self.settings.save(self.directory/"settings.json")
                self.statusBar().showMessage("Calibration saved and applied. Keep the same camera/HUD layout.")
            except Exception as exc:self.error(exc)

    def refresh_controller(self):
        self.runtime.select_controller(self.backend_choice.currentText(),"auto")
        self._controller_ids=None
    def choose_controller(self):
        selected=self.device_choice.currentData() or "auto"
        self.settings.controller_backend=self.backend_choice.currentText();self.settings.controller_device=selected
        self.runtime.select_controller(self.settings.controller_backend,selected)
        try:self.settings.save(self.directory/"settings.json")
        except Exception as exc:self.error(exc)

    def update_phase2(self):
        report=self.runtime.controller_report
        ids=[(d["id"],d["name"],d["backend"]) for d in report.get("devices",[])]
        if ids!=self._controller_ids:
            previous=self.device_choice.currentData() or self.settings.controller_device
            self.device_choice.clear();self.device_choice.addItem("Automatic Xbox selection","auto")
            for identity,name,backend in ids:self.device_choice.addItem(f"{name} ({backend})",identity)
            index=self.device_choice.findData(previous);self.device_choice.setCurrentIndex(max(0,index));self._controller_ids=ids
        self.hardware_report.setPlainText(json.dumps(report,indent=2))
        observation=self.runtime.observation
        if observation:
            age=time.perf_counter()-observation["timestamp"];stale=age>max(1.5,2/self.settings.recognition_hz)
            modules=observation["modules"]
            analyzed=self.runtime.observation_frame
            if stale:
                self.analysis_preview.clear();self.analysis_preview.setText("Analyzed frame is stale")
                self._shown_observation=None
            elif analyzed and analyzed.sequence==observation["sequence"] and self._shown_observation!=analyzed.sequence:
                image=annotate(analyzed.image,observation);h,w=image.shape[:2]
                qimage=QImage(image.data,w,h,image.strides[0],QImage.Format_BGR888).copy()
                self.analysis_preview.setPixmap(QPixmap.fromImage(qimage).scaled(760,260,Qt.KeepAspectRatio,Qt.SmoothTransformation));self._shown_observation=analyzed.sequence
            summary=[]
            for field in ("speed","gear","lap_timer","lap_number","gameplay_state"):
                v=modules[field]["value"] if not stale else None
                summary.append(f"{field}: {v if v is not None else 'unknown'}")
            self.hud_values.setText(" • ".join(summary)+f"\nObservation age: {age:.2f}s • analysis: {observation['latency_ms']:.1f}ms")
            self.live_hud.setText(" • ".join(summary))
            for row,name in enumerate(MODULES):
                reading=modules[name]
                values=(name,"stale" if stale else reading["status"],f"{reading['confidence']:.0%}",str(reading["value"])[:180],reading["reason"])
                for col,text in enumerate(values):
                    item=QTableWidgetItem(text);item.setToolTip(json.dumps(reading,indent=2));self.recognition_table.setItem(row,col,item)
        elif self.runtime.recognition_error:self.hud_values.setText("Recognition error: "+self.runtime.recognition_error)
        while True:
            try:kind,payload,callback=self.job_queue.get_nowait()
            except queue.Empty:break
            if kind=="progress":self.job_status.setText(payload)
            elif kind=="error":self.job_status.setText("Task failed: "+payload);self.error(payload)
            else:
                try:callback(payload);self.job_status.setText("Task complete")
                except Exception as exc:self.error(exc)

    def mark_lap(self):
        try:
            count=self.runtime.mark_lap();self.statusBar().showMessage(f"Lap boundary {count} recorded")
        except Exception as exc:self.error(exc)
    def start_job(self,fn,done):
        if self.job_thread and self.job_thread.is_alive():self.error("A video or profile task is already running");return
        self.job_cancel.clear();self.job_status.setText("Working…")
        def work():
            try:self.job_queue.put(("done",fn(),done))
            except Exception as exc:self.job_queue.put(("error",str(exc),None))
        self.job_thread=threading.Thread(target=work,name="reference-job",daemon=True);self.job_thread.start()
    def analyze_file(self):
        path,_=QFileDialog.getOpenFileName(self,"Analyze a local gameplay video","","Video (*.mp4 *.mkv *.avi *.mov)")
        if not path:return
        folder=self.directory/"recordings"/("video-"+uuid.uuid4().hex[:12])
        def work():
            return analyze_video(path,folder,self.settings,1/self.settings.recognition_hz,lambda n,t:self.job_queue.put(("progress",f"Analyzed {n} frames at {t:.1f}s",None)),self.job_cancel)
        def done(output):self.db.record_session(output,"video-replay");self.history();self.statusBar().showMessage(f"Video session saved: {output}")
        self.start_job(work,done)
    def edit_boundaries(self):
        items=self.sessions.selectedItems()
        if len(items)!=1:self.error("Select exactly one stopped session");return
        session=Path(items[0].data(Qt.UserRole))
        try:
            manifest=json.loads((session/"manifest.json").read_text(encoding="utf-8"))
            if not manifest.get("complete"):raise ValueError("Stop recording or finish video analysis first")
            frames=load_jsonl(session/"frames.jsonl")
            if not frames:raise ValueError("Session has no frames")
            start=frames[0]["timestamp"];end=frames[-1]["timestamp"]
            existing=load_jsonl(session/"events.jsonl")
            default=", ".join(f"{e['timestamp']-start:.3f}" for e in existing if e.get("type")=="lap_boundary")
            text,ok=QInputDialog.getText(self,"Lap boundaries",f"Start/finish timestamps in seconds after first recorded frame (0 to {end-start:.2f}).\nExample: 0, 92.4, 185.1 — yields two complete reference laps. Existing markers will be replaced.",text=default)
            if not ok:return
            values=[float(v.strip()) for v in text.split(",") if v.strip()]
            if len(values)<3 or len(values)>2048 or any(not 0<=v<=end-start for v in values) or any(b-a<5 for a,b in zip(values,values[1:])):raise ValueError("Supply at least three increasing boundaries, five seconds apart, inside the recording")
            events=[e for e in existing if e.get("type")!="lap_boundary"]+[ {"type":"lap_boundary","timestamp":start+v,"method":"manual_review"} for v in values]
            temp=session/"events.tmp";temp.write_text("\n".join(json.dumps(e) for e in events)+"\n",encoding="utf-8");temp.replace(session/"events.jsonl")
            self.statusBar().showMessage(f"Saved {len(values)} lap boundaries")
        except Exception as exc:self.error(exc)

    def generate_selected(self):
        paths=[item.data(Qt.UserRole) for item in self.sessions.selectedItems()]
        if not paths:self.error("Select one or more completed reference sessions");return
        circuit=self.circuit.text();category=self.bike_category.text();model=self.bike_model.text();weather=self.weather.text()
        def done(profile):self.db.save_profile(profile);self.refresh_profiles();self.statusBar().showMessage("Profile generated. Review before using as a reference.")
        self.start_job(lambda:generate_profile(paths,circuit,category,model,weather),done)
    def refresh_profiles(self):
        self.profiles_list.clear()
        for identity,circuit,category,weather,confidence in self.db.profiles():
            item=QListWidgetItem(f"{circuit} • {category} • {weather} • confidence {confidence:.0%}");item.setData(Qt.UserRole,identity);self.profiles_list.addItem(item)
    def selected_profile(self):
        item=self.profiles_list.currentItem()
        if item is None:raise ValueError("Select a track profile first")
        return self.db.get_profile(item.data(Qt.UserRole))
    def review_profile(self):
        try:profile=self.selected_profile()
        except Exception as exc:self.error(exc);return
        dialog=QDialog(self);dialog.setWindowTitle("Review reference track profile");dialog.resize(850,650);layout=QVBoxLayout(dialog)
        label=QLabel(f"{profile['circuit']} • {len(profile['reference_laps'])} laps • confidence {profile['confidence']:.0%}\n{profile['progress_basis']}\n{profile['assisted_reference_warning']}");label.setWordWrap(True);layout.addWidget(label)
        text=QPlainTextEdit();text.setReadOnly(True);text.setPlainText(json.dumps(profile,indent=2));layout.addWidget(text)
        close=QPushButton("Close");close.clicked.connect(dialog.accept);layout.addWidget(close);dialog.exec()
    def import_selected(self):
        path,_=QFileDialog.getOpenFileName(self,"Import track profile","","Track profiles (*.json)")
        if path:
            try:self.db.save_profile(import_profile(path));self.refresh_profiles()
            except Exception as exc:self.error(exc)
    def export_selected(self):
        try:profile=self.selected_profile()
        except Exception as exc:self.error(exc);return
        path,_=QFileDialog.getSaveFileName(self,"Export track profile","track-profile.json","Track profiles (*.json)")
        if path:
            try:export_profile(profile,path)
            except Exception as exc:self.error(exc)
    def delete_selected(self):
        try:profile=self.selected_profile()
        except Exception as exc:self.error(exc);return
        if QMessageBox.question(self,"Delete profile",f"Delete profile for {profile['circuit']}? Reference recordings will be retained.")==QMessageBox.Yes:
            self.db.delete_profile(profile["id"]);self.refresh_profiles()
