import json
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
import time
import cv2
import pytest
from PySide6.QtCore import Qt,QPoint
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from motoassist.calibration import RegionCanvas
from motoassist.config import Settings
from motoassist.runtime import Runtime
from motoassist.analyze_video import analyze_video
from motoassist.learning import generate_profile
from motoassist.ui import Window
from test_vision import scene,ROIS
from test_learning import reference_session


def test_calibration_drag_normalized_coordinates():
    app=QApplication.instance() or QApplication([])
    canvas=RegionCanvas(scene(),{});canvas.resize(960,540);canvas.show();app.processEvents()
    QTest.mousePress(canvas,Qt.LeftButton,pos=QPoint(96,54))
    QTest.mouseRelease(canvas,Qt.LeftButton,pos=QPoint(288,162));app.processEvents()
    assert canvas.rois['speed']==pytest.approx([.1,.1,.3,.3],abs=.005)
    canvas.close()


def test_live_recording_associates_recognition_and_inputs(tmp_path):
    runtime=Runtime(Settings(),simulate=True);runtime.start()
    try:
        end=time.perf_counter()+30  # Allow first model initialization; this is not an FPS test.
        while runtime.frame is None and time.perf_counter()<end:time.sleep(.02)
        path=runtime.start_recording(tmp_path)
        start_sequence=runtime.frame.sequence
        while time.perf_counter()<end:
            observation=runtime.observation
            if observation and observation['sequence']>start_sequence and observation['modules']['speed']['value']==180:break
            time.sleep(.05)
        else:raise AssertionError(runtime.recognition_error or runtime.observation)
        runtime.mark_lap();runtime.stop_recording()
        readings=[json.loads(line) for line in (path/'observations.jsonl').read_text().splitlines()]
        assert readings and any(r['modules']['speed']['value']==180 for r in readings)
        for row in readings:
            assert row['input_kind']=='synthetic'
            assert row['input']['timestamp']<=row['timestamp']
            assert row['input_valid']
        assert len((path/'events.jsonl').read_text().splitlines())==1
        assert json.loads((path/'manifest.json').read_text())['complete']
    finally:runtime.stop()


def test_actual_video_ocr_to_multilap_profile(tmp_path):
    video=tmp_path/'synthetic-reference.avi';writer=cv2.VideoWriter(str(video),cv2.VideoWriter_fourcc(*'MJPG'),2,(960,540))
    assert writer.isOpened()
    for _ in range(42):writer.write(scene())
    writer.release()
    output=analyze_video(video,tmp_path/'analysis',Settings(hud_rois=ROIS),interval=1)
    (output/'events.jsonl').write_text('\n'.join(json.dumps({'type':'lap_boundary','timestamp':t}) for t in (0,10,20)))
    profile=generate_profile([output],'Synthetic test camera')
    assert len(profile['reference_laps'])==2
    assert all(p['speed_kmh']==180 for p in profile['reference_speed_profile'])
    assert profile['racing_line'] and profile['landmarks'] and profile['visual_braking_zones']
    assert profile['source']=='video-replay'


def test_profile_generation_through_desktop_worker(tmp_path):
    app=QApplication.instance() or QApplication([])
    session=reference_session(tmp_path/'session')
    window=Window(Settings(),tmp_path,simulate=True)
    try:
        window.db.record_session(session,'simulation');window.history()
        window.sessions.item(0).setSelected(True);window.circuit.setText('Synthetic test circuit')
        window.generate_selected()
        end=time.perf_counter()+5
        while window.job_thread.is_alive() and time.perf_counter()<end:app.processEvents();time.sleep(.02)
        window.update_phase2()
        assert window.profiles_list.count()==1
        window.profiles_list.setCurrentRow(0)
        assert len(window.selected_profile()['reference_laps'])==2
    finally:window.quit();app.processEvents()
