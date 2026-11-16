from dataclasses import replace
import json
import math
import time
import cv2
import numpy as np
import pytest
from motoassist.config import Settings
from motoassist.decisions import decide
from motoassist.models import Frame, InputState, Observation
from motoassist.recording import Recorder
from motoassist.runtime import Runtime
from motoassist.windows import axis

@pytest.mark.parametrize("raw,expected",[(-32768,-1),(0,0),(32767,1)])
def test_axis_endpoints(raw,expected): assert axis(raw)==expected

def test_deadzone():
    assert axis(3000,0.12)==0
    assert 0 < axis(20000,0.12) < 1

@pytest.mark.parametrize("change,reason",[
    ({"timestamp":9},"stale frame"),({"timestamp":11},"stale frame"),
    ({"confidence":0.2},"low confidence"),({"gameplay":False},"gameplay unavailable"),
    ({"focused":False},"gameplay unavailable"),({"speed":float("nan")},"invalid data"),
    ({"target_speed":-1},"invalid speed")])
def test_fail_closed_observations(change,reason):
    obs=replace(Observation(10,180,100,0.5,0.9),**change)
    result=decide(obs,InputState(10,True,rt=1),10,"Maximum")
    assert not result.active and result.reason==reason
    assert result.throttle==result.brake==result.steering==0

@pytest.mark.parametrize("sample,reason",[(InputState(10),"controller disconnected"),(InputState(9,True),"stale controller"),(InputState(10,True,lx=1),"manual override"),(InputState(10,True,buttons=0x30),"manual override")])
def test_controller_failures(sample,reason):
    assert decide(Observation(10,180,100,0.5,0.9),sample,10,"Balanced").reason==reason

def test_decision_adapts_and_emergency():
    obs=Observation(10,180,100,0.5,0.9); sample=InputState(10,True,rt=1)
    fast=decide(obs,sample,10,"Balanced")
    slow=decide(replace(obs,speed=90),sample,10,"Balanced")
    assert fast.brake>slow.brake and fast.throttle<slow.throttle
    assert -1<=fast.steering<=1 and 0<=fast.brake<=1 and 0<=fast.throttle<=1
    assert not decide(obs,sample,10,"Balanced",emergency=True).active
    assert not decide(obs,sample,10,"Manual").active
    assert not decide(obs,sample,10,"Experimental Autopilot").active

def test_config_roundtrip_and_validation(tmp_path):
    path=tmp_path/"settings.json"; settings=Settings(); settings.save(path)
    assert Settings.load(path)==settings
    with pytest.raises(ValueError): Settings(deadzone=1).save(path)
    with pytest.raises(ValueError): Settings(game_title=" ").validate()
    assert Settings.load(path)==settings

def test_recording_timing_and_images(tmp_path):
    recorder=Recorder(tmp_path,"simulation",{})
    image=np.full((20,30,3),120,np.uint8)
    for i,stamp in enumerate([1,1.05,1.3]):
        assert recorder.submit(Frame(i,stamp,image),InputState(1,True,rt=0.75))
    path=recorder.stop()
    rows=[json.loads(line) for line in (path/"frames.jsonl").read_text().splitlines()]
    assert [r["input_valid"] for r in rows]==[True,True,False]
    assert rows[1]["input_age_ms"]==pytest.approx(50)
    assert all(cv2.imread(str(path/r["file"])).shape==(20,30,3) for r in rows)
    meta=json.loads((path/"manifest.json").read_text())
    assert meta["complete"] and not meta["assistance_active"] and meta["saved_frames"]==3
    assert not recorder.submit(Frame(9,1,image),None)

def test_recording_disk_error(tmp_path,monkeypatch):
    monkeypatch.setattr(cv2,"imwrite",lambda *a:False)
    recorder=Recorder(tmp_path,"simulation",{})
    recorder.submit(Frame(1,1,np.zeros((5,5,3),np.uint8)),None)
    recorder.stop()
    assert recorder.error=="JPEG write failed"
    assert not json.loads((recorder.path/"manifest.json").read_text())["complete"]

def wait_frame(runtime, minimum=1):
    end=time.perf_counter()+5
    while time.perf_counter()<end:
        frame=runtime.snapshot()[0]
        if frame and frame.sequence>=minimum:return frame
        time.sleep(0.02)
    raise AssertionError(runtime.status)

def test_runtime_recording_and_shutdown(tmp_path):
    runtime=Runtime(Settings(),simulate=True);runtime.start()
    try:
        frame=wait_frame(runtime)
        assert frame.image.shape==(540,960,3)
        assert runtime.sample_for(frame.timestamp).timestamp<=frame.timestamp
        path=runtime.start_recording(tmp_path)
        wait_frame(runtime,frame.sequence+5)
        runtime.stop_recording()
        rows=[json.loads(line) for line in (path/"frames.jsonl").read_text().splitlines()]
        assert len(rows)>=4 and all(r["input_valid"] for r in rows)
    finally:runtime.stop()
    assert all(not t.is_alive() for t in runtime.threads)

def test_stale_recording_rejected(tmp_path):
    runtime=Runtime(Settings(),simulate=True)
    with pytest.raises(RuntimeError): runtime.start_recording(tmp_path)

def test_video_replay(tmp_path):
    path=tmp_path/"clip.avi"
    writer=cv2.VideoWriter(str(path),cv2.VideoWriter_fourcc(*"MJPG"),10,(64,48))
    assert writer.isOpened()
    for i in range(4):writer.write(np.full((48,64,3),i*50,np.uint8))
    writer.release()
    runtime=Runtime(Settings(),video=str(path));runtime.start()
    try:
        assert wait_frame(runtime).image.shape==(48,64,3)
        end=time.perf_counter()+3
        while runtime.status!="Video ended" and time.perf_counter()<end:time.sleep(0.02)
        assert runtime.status=="Video ended" and runtime.frame is None
    finally:runtime.stop()

def test_bounded_queue(tmp_path,monkeypatch):
    import threading
    entered=threading.Event(); release=threading.Event(); original=cv2.imwrite
    def slow(*args):entered.set();release.wait(3);return original(*args)
    monkeypatch.setattr(cv2,"imwrite",slow)
    recorder=Recorder(tmp_path,"simulation",{},capacity=1)
    image=np.zeros((5,5,3),np.uint8)
    try:
        recorder.submit(Frame(1,1,image),None);assert entered.wait(2)
        assert recorder.submit(Frame(2,2,image),None)
        assert not recorder.submit(Frame(3,3,image),None)
        assert recorder.dropped==1
    finally:release.set();recorder.stop()

def test_sample_association_never_uses_future_sample():
    runtime=Runtime(Settings(),simulate=True)
    runtime.inputs.extend([InputState(1,True,rt=0.1),InputState(2,True,rt=0.2),InputState(3,True,rt=0.3)])
    assert runtime.sample_for(0.5) is None
    assert runtime.sample_for(2.5).rt==0.2
    assert runtime.sample_for(3).rt==0.3
