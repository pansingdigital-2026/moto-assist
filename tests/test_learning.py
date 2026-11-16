import json
from pathlib import Path
import cv2
import numpy as np
import pytest
from motoassist.learning import generate_profile,export_profile,import_profile,lap_intervals
from motoassist.database import Database
from motoassist.analyze_video import analyze_video
from motoassist.config import Settings
from motoassist.vision import result


def reference_session(path,source="simulation"):
    path.mkdir()
    (path/"manifest.json").write_text(json.dumps({"complete":True,"source":source,"reference_labels":{"circuit_label":"Synthetic test circuit"}}))
    (path/"events.jsonl").write_text("\n".join(json.dumps({"type":"lap_boundary","timestamp":t}) for t in [0,10,20]))
    rows=[]
    for i in range(20):
        corner={"direction":"left" if 3<=i%10<6 else "straight","curvature":-.3}
        line={"colors":["red"],"sections":[{"color":"red","point":[.5,.6]}]}
        rows.append({"sequence":i,"timestamp":i+.1,"modules":{"speed":result(100+i%10,.95),"corner":result(corner,.7),"racing_line":result(line,.7),"landmarks":result({"image_hash":str(i),"points":[],"descriptors":[]},.6),"gameplay_state":result("gameplay",.7)}})
    (path/"observations.jsonl").write_text("\n".join(json.dumps(r) for r in rows));return path


def test_multilap_profile_generation_exchange_and_database_crud(tmp_path):
    path=reference_session(tmp_path/"session")
    profile=generate_profile([path],"Synthetic test circuit")
    assert len(profile["reference_laps"])==2 and profile["reference_speed_profile"]
    assert len(profile["corners"])==2 and profile["corners"][0]["direction"]=="left"
    assert profile["visual_braking_zones"] and profile["landmarks"] and profile["racing_line"]
    assert "NOT world position" in profile["progress_basis"]
    exported=tmp_path/"profile.json";export_profile(profile,exported);assert import_profile(exported)==profile
    db=Database(tmp_path/"tracks.db")
    try:
        db.save_profile(profile);assert len(db.profiles())==1
        assert db.get_profile(profile["id"])==profile
        db.delete_profile(profile["id"]);assert not db.profiles()
    finally:db.close()

def test_incomplete_and_mixed_provenance_rejected(tmp_path):
    first=reference_session(tmp_path/"one");second=reference_session(tmp_path/"two","windows")
    with pytest.raises(ValueError,match="Do not combine"):generate_profile([first,second],"Synthetic test circuit")
    (first/"manifest.json").write_text('{"complete":false}')
    with pytest.raises(ValueError,match="incomplete"):generate_profile([first],"Synthetic test circuit")

def test_corrupt_or_unknown_import_rejected(tmp_path):
    path=tmp_path/"profile.json";path.write_text('{"schema_version":999}')
    with pytest.raises(ValueError):import_profile(path)
    profile=generate_profile([reference_session(tmp_path/"session")],"Synthetic test circuit")
    profile["reference_speed_profile"][0]["speed_kmh"]=float("nan");path.write_text(json.dumps(profile))
    with pytest.raises(ValueError):import_profile(path)

def test_lap_ocr_changes_need_two_observations():
    rows=[{"timestamp":i*5,"modules":{"lap_number":result(lap,.9)}} for i,lap in enumerate([1,1,9,2,2,3,3,4,4])]
    intervals=lap_intervals(rows,[])
    assert intervals==[(15,25,"ocr_lap_number"),(25,35,"ocr_lap_number")]

def test_offline_video_media_timestamps_and_no_invented_inputs(tmp_path,monkeypatch):
    class Analyzer:
        def __init__(self,*a,**kw):pass
        def analyze(self,image,sequence,timestamp):return {"sequence":sequence,"timestamp":timestamp,"modules":{}}
    monkeypatch.setattr("motoassist.analyze_video.Analyzer",Analyzer)
    video=tmp_path/"sample.avi";writer=cv2.VideoWriter(str(video),cv2.VideoWriter_fourcc(*"MJPG"),10,(64,48))
    assert writer.isOpened()
    for i in range(10):writer.write(np.full((48,64,3),i*20,np.uint8))
    writer.release();out=analyze_video(video,tmp_path/"analyzed",Settings(),.2)
    rows=[json.loads(line) for line in (out/"frames.jsonl").read_text().splitlines()]
    assert len(rows)==5 and [r["timestamp"] for r in rows]==[0,.2,.4,.6,.8]
    assert all(r["input"] is None and not r["input_valid"] for r in rows)
    assert json.loads((out/"manifest.json").read_text())["complete"]
    with pytest.raises(FileExistsError):analyze_video(video,out)
