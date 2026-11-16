import cv2
import numpy as np
import pytest
from motoassist.vision import Analyzer,LocalOCR,parse_hud,validate_rois,auto_hud

class EmptyOCR:
    def read(self,image,detect=True):return []

@pytest.mark.parametrize("name,text,value",[("speed","180 km/h",180),("speed","100 MPH",160.93),("gear","N","N"),("gear","GEAR 4","4"),("lap_timer","1:23.456",83.456),("lap_number","LAP 2/10",2),("speed","999",None),("lap_timer","1:73.2",None),("gear","8",None),("lap_number","4/3",None)])
def test_hud_parsing(name,text,value):assert parse_hud(name,text)==value

def scene(scale=1):
    im=np.zeros((540,960,3),np.uint8)
    cv2.fillPoly(im,[np.array([[100,539],[390,200],[570,200],[860,539]])],(70,70,70))
    for y,color in [(470,(0,255,0)),(420,(0,255,255)),(370,(0,0,255))]:cv2.rectangle(im,(475,y),(485,y+20),color,-1)
    cv2.putText(im,"180 km/h",(710,80),cv2.FONT_HERSHEY_SIMPLEX,1,(255,255,255),2)
    cv2.putText(im,"GEAR 3",(710,125),cv2.FONT_HERSHEY_SIMPLEX,1,(255,255,255),2)
    cv2.putText(im,"1:23.456",(30,60),cv2.FONT_HERSHEY_SIMPLEX,1,(255,255,255),2)
    cv2.putText(im,"LAP 2/10",(30,110),cv2.FONT_HERSHEY_SIMPLEX,1,(255,255,255),2)
    cv2.ellipse(im,(100,270),(40,60),0,0,360,(255,255,255),3)
    cv2.circle(im,(100,210),4,(255,0,0),-1)
    if scale!=1:im=cv2.resize(im,None,fx=scale,fy=scale)
    return im

ROIS={"road_sample":[.3,.77,.34,.8],"road_search":[.03,.35,.97,.98],"bike_anchor":[.49,.90,.51,.94],"minimap":[.05,.37,.16,.63]}

@pytest.mark.parametrize("scale",[1,2,4])
def test_road_line_minimap_at_multiple_resolutions(scale):
    a=Analyzer(ROIS,EmptyOCR());reading=a.analyze(scene(scale),1,1)["modules"]
    assert reading["track_surface"]["value"] is not None
    assert len(reading["road_boundaries"]["value"]["left"])>=5
    assert reading["corner"]["value"]["direction"]=="straight"
    assert abs(reading["bike_position"]["value"]["offset"])<.1
    assert reading["racing_line"]["value"]["colors"]==["green","red","yellow"]
    assert reading["minimap"]["value"]["outline"]
    assert reading["landmarks"]["value"]["descriptors"]

def test_unknown_without_calibration_or_visible_evidence():
    reading=Analyzer({},EmptyOCR()).analyze(np.zeros((540,960,3),np.uint8),1,1)
    for name in ("speed","gear","track_surface","minimap","crash_recovery","gameplay_state"):
        assert reading["modules"][name]["value"] is None

def test_actual_bundled_ocr_on_synthetic_hud():
    analyzer=Analyzer(ROIS,LocalOCR())
    reading=analyzer.analyze(scene(),1,1)
    modules=reading["modules"]
    assert modules["speed"]["value"]==180
    assert modules["gear"]["value"]=="3"
    assert modules["lap_timer"]["value"]==83.456
    assert modules["lap_number"]["value"]==2
    assert reading["hud_proposals"]["speed"]

@pytest.mark.parametrize("word,state",[("PAUSED","pause"),("LOADING","loading"),("RIDER DOWN","crash"),("RESPAWNING","recovery")])
def test_explicit_state_evidence_requires_confirmation(word,state):
    class OCR:
        def read(self,image,detect=True):return [{"text":word,"confidence":.99,"box":[0,0,100,40]}]
    analyzer=Analyzer({},OCR());image=np.zeros((300,600,3),np.uint8)
    assert analyzer.analyze(image,1,1)["modules"]["gameplay_state"]["value"] is None
    assert analyzer.analyze(image,2,2)["modules"]["gameplay_state"]["value"]==state
    if state in ("crash","recovery"):assert analyzer.analyze(image,3,3)["modules"]["crash_recovery"]["value"]==state

def test_low_confidence_text_and_ambiguous_auto_detection():
    class OCR:
        def read(self,image,detect=True):return [{"text":"180 km/h","confidence":.3,"box":[0,0,100,40]}]
    assert Analyzer({},OCR()).analyze(scene(),1,1)["modules"]["speed"]["value"] is None
    tokens=[{"text":"180 km/h","confidence":.99,"box":[0,0,100,40]}]*2
    assert "speed" not in auto_hud(tokens,scene().shape)

@pytest.mark.parametrize("rois",[{"speed":[0,0,0,1]},{"bad":[0,0,1,1]},{"speed":[0,float("nan"),1,1]}])
def test_invalid_calibration(rois):
    with pytest.raises(ValueError):validate_rois(rois)


def test_auto_speed_label_without_whitespace():
    tokens=[{"text":"180km/h","confidence":.99,"box":[10,10,150,40]}]
    assert auto_hud(tokens,(540,960,3))["speed"][0]["text"]=="180km/h"
