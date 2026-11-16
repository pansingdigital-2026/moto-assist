"""Local, confidence-bearing image observations; never hidden physics or telemetry."""
from dataclasses import dataclass
import hashlib
import math
import re
import time
import cv2
import numpy as np

# Bound OpenCV worker demand alongside the game and OBS.
cv2.setNumThreads(2)

MODULES=("speed","gear","lap_timer","lap_number","minimap","track_surface","road_boundaries","corner","bike_position","racing_line","landmarks","gameplay_state","crash_recovery")
ROI_NAMES=("speed","gear","lap_timer","lap_number","minimap","road_sample","road_search","bike_anchor","state_text")

def result(value=None, confidence=0.0, reason="No reliable observation", status=None):
    return {"value":value,"confidence":round(float(confidence),4),"status":status or ("detected" if value is not None else "unknown"),"reason":reason}

def rectangle(roi, shape):
    h,w=shape[:2];x1,y1,x2,y2=roi
    return max(0,int(x1*w)),max(0,int(y1*h)),min(w,int(math.ceil(x2*w))),min(h,int(math.ceil(y2*h)))

def crop(image, roi):
    x1,y1,x2,y2=rectangle(roi,image.shape)
    return image[y1:y2,x1:x2]

def validate_rois(rois):
    if not isinstance(rois,dict): raise ValueError("HUD regions must be an object")
    for name,roi in rois.items():
        if name not in ROI_NAMES or not isinstance(roi,(list,tuple)) or len(roi)!=4: raise ValueError(f"Invalid region {name}")
        if not all(isinstance(v,(int,float)) and math.isfinite(v) and 0<=v<=1 for v in roi): raise ValueError(f"Region {name} must use normalized coordinates")
        if roi[0]>=roi[2] or roi[1]>=roi[3]: raise ValueError(f"Region {name} is empty")
    return rois

class LocalOCR:
    """The pinned wheel contains its models. No runtime downloads or GPU allocation."""
    def __init__(self):
        import onnxruntime
        onnxruntime.disable_telemetry_events()
        from rapidocr_onnxruntime import RapidOCR
        self.engine=RapidOCR(intra_op_num_threads=2,inter_op_num_threads=1,det_limit_side_len=640,det_limit_type="max",use_cls=False)

    def read(self,image,detect=True):
        if image.size==0:return []
        rows,_=self.engine(image,use_det=detect,use_cls=False,use_rec=True)
        tokens=[]
        for row in rows or []:
            if len(row)>=3 and isinstance(row[1],str):
                points=np.asarray(row[0]);box=[float(points[:,0].min()),float(points[:,1].min()),float(points[:,0].max()),float(points[:,1].max())]
                tokens.append({"text":row[1],"confidence":float(row[2]),"box":box})
            elif len(row)>=2 and isinstance(row[0],str):
                tokens.append({"text":row[0],"confidence":float(row[1]),"box":[0,0,image.shape[1],image.shape[0]]})
        return tokens

def parse_hud(name,text,unit="km/h"):
    text=text.strip().upper().replace("，",",").replace("：",":")
    if name=="speed":
        match=re.fullmatch(r"\s*(\d{1,3})(?:\s*(KM/?H|KPH|MPH))?\s*",text)
        if match:
            speed=float(match[1]);units=match[2] or unit.upper()
            if units=="MPH":speed*=1.609344
            if 0<=speed<=400:return round(speed,2)
    elif name=="gear":
        match=re.fullmatch(r"(?:GEAR\s*)?([1-6N])",text)
        if match:return match[1]
    elif name=="lap_timer":
        match=re.fullmatch(r"(?:TIME\s*)?(\d{1,2})[:']([0-5]\d)[.,:](\d{2,3})",text)
        if match:return round(int(match[1])*60+int(match[2])+int(match[3])/10**len(match[3]),3)
    elif name=="lap_number":
        match=re.fullmatch(r"(?:LAP\s*)?(\d{1,2})(?:\s*/\s*(\d{1,2}))?",text)
        if match and 1<=int(match[1])<=99 and (not match[2] or int(match[1])<=int(match[2])):return int(match[1])
    return None

def auto_hud(tokens,shape):
    """Labelled text is evidence. Bare speed/gear digits are not auto-assigned."""
    h,w=shape[:2];found={}
    for token in tokens:
        text=token["text"].upper()
        name=None
        if re.search(r"(KM/?H|KPH|MPH)\b",text):name="speed"
        elif re.match(r"GEAR\s*[1-6N]$",text):name="gear"
        elif re.match(r"LAP\s*\d",text):name="lap_number"
        elif re.match(r"(?:TIME\s*)?\d{1,2}[:'][0-5]\d[.,:]\d{2,3}$",text):name="lap_timer"
        if name:
            x1,y1,x2,y2=token["box"]
            found.setdefault(name,[]).append((token,[max(0,(x1-4)/w),max(0,(y1-4)/h),min(1,(x2+4)/w),min(1,(y2+4)/h)]))
    return {name:items[0] for name,items in found.items() if len(items)==1}

class Analyzer:
    def __init__(self, rois=None, ocr=None, unit="km/h", min_confidence=.8):
        self.rois=validate_rois(dict(rois or {}));self.unit=unit;self.minimum=min_confidence
        self.ocr=ocr;self.ocr_error=None;self.previous_gray=None;self.previous_state="unknown";self.state_streak=0
        self.orb=cv2.ORB_create(nfeatures=100)

    def analyze(self,image,sequence,timestamp):
        started=time.perf_counter()
        out={name:result() for name in MODULES};tokens=[];proposals={}
        if self.ocr is None and self.ocr_error is None:
            try:self.ocr=LocalOCR()
            except Exception as exc:self.ocr_error=str(exc)
        if self.ocr:
            try:
                # A downscaled full-frame pass supplies state labels and conservative HUD proposals.
                scale=min(1,960/image.shape[1]);small=cv2.resize(image,None,fx=scale,fy=scale) if scale<1 else image
                tokens=self.ocr.read(small)
                for t in tokens:t["box"]=[v/scale for v in t["box"]]
                if "state_text" in self.rois:
                    tokens.extend(self.ocr.read(crop(image,self.rois["state_text"])))
                automatic=auto_hud([t for t in tokens if t["confidence"]>=self.minimum],image.shape)
                proposals={name:roi for name,(token,roi) in automatic.items()}
                for name in ("speed","gear","lap_timer","lap_number"):
                    if name in self.rois:
                        values=self.ocr.read(crop(image,self.rois[name]),detect=False)
                    else:values=[automatic[name][0]] if name in automatic else []
                    matches=[]
                    for t in values:
                        value=parse_hud(name,t["text"],self.unit)
                        if value is not None and t["confidence"]>=self.minimum:matches.append((value,t["confidence"]))
                    if len(matches)==1:out[name]=result(matches[0][0],matches[0][1],"Calibrated OCR" if name in self.rois else "Unambiguous labelled HUD OCR")
                    else:out[name]=result(reason="Calibrate this HUD region; text missing, ambiguous or low-confidence")
            except Exception as exc:
                self.ocr_error=str(exc)
                for name in ("speed","gear","lap_timer","lap_number"):out[name]=result(reason=str(exc),status="error")
        else:
            for name in ("speed","gear","lap_timer","lap_number"):out[name]=result(reason=self.ocr_error or "OCR unavailable",status="error")
        road=self._road(image,out)
        self._line(image,out,road)
        self._minimap(image,out)
        self._landmarks(image,out)
        self._state(image,tokens,out)
        return {"schema_version":1,"sequence":int(sequence),"timestamp":float(timestamp),"latency_ms":(time.perf_counter()-started)*1000,"modules":out,"hud_proposals":proposals}

    def _road(self,image,out):
        if "road_sample" not in self.rois:
            for name in ("track_surface","road_boundaries","corner","bike_position"):out[name]=result(reason="Calibrate a clear asphalt sample and bike anchor for this camera")
            return None
        scale=640/image.shape[1];small=cv2.resize(image,None,fx=scale,fy=scale);h,w=small.shape[:2]
        lab=cv2.cvtColor(small,cv2.COLOR_BGR2LAB).astype(np.float32)
        sample=crop(lab,self.rois["road_sample"])
        median=np.median(sample.reshape(-1,3),axis=0)
        deviation=float(np.median(np.linalg.norm(sample-median,axis=2)))
        if deviation>35:
            out["track_surface"]=result(reason="Asphalt sample is too varied; recalibrate");return None
        distance=np.linalg.norm(lab-median,axis=2)
        mask=(distance<max(18,min(38,deviation*2+18))).astype(np.uint8)*255
        search=self.rois.get("road_search",[.03,.35,.97,.98]);x1,y1,x2,y2=rectangle(search,small.shape)
        allowed=np.zeros_like(mask);allowed[y1:y2,x1:x2]=255;mask=cv2.bitwise_and(mask,allowed)
        mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((7,7),np.uint8))
        count,labels,stats,centers=cv2.connectedComponentsWithStats(mask)
        sx1,sy1,sx2,sy2=rectangle(self.rois["road_sample"],small.shape)
        sample_labels=labels[sy1:sy2,sx1:sx2];ids,counts=np.unique(sample_labels[sample_labels>0],return_counts=True)
        if not len(ids):return None
        component=int(ids[np.argmax(counts)]);mask=(labels==component).astype(np.uint8)*255
        coverage=float(np.count_nonzero(mask)/max(1,(y2-y1)*(x2-x1)))
        if not .08<coverage<.93:
            out["track_surface"]=result(reason="Road mask covers implausibly little or most of view");return None
        left=[];right=[]
        for yy in np.linspace(y1+(.2*(y2-y1)),y2-1,12).astype(int):
            xs=np.flatnonzero(mask[yy])
            if len(xs)>w*.07 and xs[-1]-xs[0]<w*.94:
                left.append([float(xs[0]/w),float(yy/h)]);right.append([float(xs[-1]/w),float(yy/h)])
        confidence=min(.78,.55+len(left)*.015)
        out["track_surface"]=result({"coverage":round(coverage,3),"sample_lab":[float(v) for v in median]},confidence,"Calibrated appearance segmentation; not semantic road certainty")
        if len(left)<5:return None
        out["road_boundaries"]=result({"left":left,"right":right},confidence,"Image-space edges of connected asphalt candidate")
        near=(left[-1][0]+right[-1][0])/2;far=(left[0][0]+right[0][0])/2
        curvature=float(np.clip((far-near)*3,-1,1))
        direction="left" if curvature<-.12 else "right" if curvature>.12 else "straight"
        out["corner"]=result({"direction":direction,"curvature":curvature,"approaching":direction!="straight"},confidence,"Perspective centreline bend; not world curvature")
        if "bike_anchor" in self.rois:
            anchor=self.rois["bike_anchor"];bike_x=(anchor[0]+anchor[2])/2
            offset=(bike_x-near)/max(.01,(right[-1][0]-left[-1][0])/2)
            out["bike_position"]=result({"offset":round(offset,3),"anchor_x":bike_x},min(confidence,.65),"Calibrated fixed-camera bike anchor relative to near road edges")
        return (left,right)

    def _line(self,image,out,road):
        small=cv2.resize(image,(640,round(image.shape[0]*640/image.shape[1])));h,w=small.shape[:2]
        hsv=cv2.cvtColor(small,cv2.COLOR_BGR2HSV)
        area=np.zeros((h,w),np.uint8)
        if road:
            points=np.array([[int(x*w),int(y*h)] for x,y in road[0]+list(reversed(road[1]))]);cv2.fillPoly(area,[points],255)
        else:
            x1,y1,x2,y2=rectangle(self.rois.get("road_search",[.1,.4,.9,.95]),small.shape);area[y1:y2,x1:x2]=255
        masks={"green":cv2.inRange(hsv,(35,85,90),(90,255,255)),"yellow":cv2.inRange(hsv,(18,90,100),(34,255,255)),"red":cv2.inRange(hsv,(0,100,100),(10,255,255))|cv2.inRange(hsv,(170,100,100),(179,255,255))}
        sections=[]
        for color,mask in masks.items():
            mask=cv2.bitwise_and(mask,area)
            contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
            for contour in contours:
                x,y,cw,ch=cv2.boundingRect(contour);size=cv2.contourArea(contour)
                if size<8 or size>h*w*.07 or cw>w*.25 or ch<4:continue
                moments=cv2.moments(contour)
                if moments["m00"]:
                    sections.append({"color":color,"point":[moments["m10"]/moments["m00"]/w,moments["m01"]/moments["m00"]/h],"area":float(size/(h*w))})
        sections.sort(key=lambda s:s["point"][1],reverse=True)
        if len(sections)>=2:
            confidence=.7 if road else .45
            out["racing_line"]=result({"sections":sections[:80],"colors":sorted(set(s["color"] for s in sections))},confidence,"Colored road-region candidates; verify visually before profile use",status="candidate")
        else:out["racing_line"]=result(reason="No coherent colored line candidates; line may be disabled")

    def _minimap(self,image,out):
        if "minimap" not in self.rois:
            out["minimap"]=result(reason="Select the minimap region; arbitrary HUD shapes are not assumed to be a map");return
        region=crop(image,self.rois["minimap"]);h,w=region.shape[:2]
        gray=cv2.cvtColor(region,cv2.COLOR_BGR2GRAY)
        binary=cv2.inRange(gray,170,255)
        contours,_=cv2.findContours(binary,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
        contours=[c for c in contours if cv2.arcLength(c,True)>min(w,h)*.7]
        if not contours:return
        contour=max(contours,key=lambda c:cv2.arcLength(c,True))
        points=cv2.approxPolyDP(contour,1.5,True).reshape(-1,2)
        hsv=cv2.cvtColor(region,cv2.COLOR_BGR2HSV);markers=cv2.inRange(hsv,(0,130,130),(179,255,255))
        n,labels,stats,centers=cv2.connectedComponentsWithStats(markers)
        marker=[float(v) for v in centers[1+np.argmax(stats[1:,cv2.CC_STAT_AREA])]/[w,h]] if n>1 else None
        out["minimap"]=result({"outline":[[float(x/w),float(y/h)] for x,y in points[:300]],"marker_candidate":marker},.65,"Calibrated bright map outline and colored marker candidate")

    def _landmarks(self,image,out):
        small=cv2.resize(image,(320,180));gray=cv2.cvtColor(small,cv2.COLOR_BGR2GRAY)
        mask=np.zeros_like(gray);mask[35:140,25:295]=255
        keypoints,descriptors=self.orb.detectAndCompute(gray,mask)
        if descriptors is None or len(keypoints)<5:return
        thumb=cv2.resize(gray,(9,8));bits=(thumb[:,1:]>thumb[:,:-1]).flatten();hash_value=f"{sum(int(bit)<<i for i,bit in enumerate(bits)):016x}"
        out["landmarks"]=result({"image_hash":hash_value,"points":[[k.pt[0]/320,k.pt[1]/180] for k in keypoints[:40]],"descriptors":descriptors[:40].tolist()},min(.8,len(keypoints)/100),"Visual reference features; not identified world landmarks")

    def _state(self,image,tokens,out):
        words=" ".join(t["text"].upper() for t in tokens if t["confidence"]>=self.minimum)
        state="unknown";confidence=0;reason="Insufficient visible evidence"
        if re.search(r"\b(PAUSED|PAUSE MENU|RESUME RACE|RESUME GAME)\b",words):state="pause";confidence=.9;reason="Visible pause/resume text"
        elif re.search(r"\bLOADING\b",words):state="loading";confidence=.9;reason="Visible loading text"
        elif re.search(r"\b(CRASHED|RIDER DOWN)\b",words):state="crash";confidence=.9;reason="Explicit visible crash text"
        elif re.search(r"\b(RECOVERING|RESETTING BIKE|RESPAWNING)\b",words):state="recovery";confidence=.9;reason="Explicit visible recovery text"
        elif out["speed"]["value"] is not None and out["road_boundaries"]["value"] is not None:
            state="gameplay";confidence=min(out["speed"]["confidence"],out["road_boundaries"]["confidence"]);reason="Visible speed and road evidence; static race/replay ambiguity remains"
        if state==self.previous_state:self.state_streak+=1
        else:self.previous_state=state;self.state_streak=1
        if self.state_streak<2:
            out["gameplay_state"]=result(reason=f"Awaiting confirmation of {state}")
        else:out["gameplay_state"]=result(state,confidence,reason) if state!="unknown" else result(reason=reason)
        if state in ("crash","recovery") and self.state_streak>=2:out["crash_recovery"]=result(state,confidence,reason)
        else:out["crash_recovery"]=result(reason="No reliable crash/recovery evidence; not a guarantee of no crash")


def annotate(image, observation):
    """Render observations in MotoAssist only, never onto the captured game window."""
    canvas=image.copy();h,w=canvas.shape[:2];modules=observation["modules"]
    boundaries=modules["road_boundaries"]["value"]
    if boundaries:
        for side in ("left","right"):
            points=np.array([[int(x*w),int(y*h)] for x,y in boundaries[side]],np.int32)
            cv2.polylines(canvas,[points],False,(255,180,40),2)
    line=modules["racing_line"]["value"]
    if line:
        for section in line["sections"]:
            x,y=section["point"];color={"red":(0,0,255),"yellow":(0,255,255),"green":(0,255,0)}[section["color"]]
            cv2.circle(canvas,(int(x*w),int(y*h)),6,color,2)
    bike=modules["bike_position"]["value"]
    if bike:cv2.circle(canvas,(int(bike["anchor_x"]*w),int(.9*h)),8,(255,0,255),2)
    text=" | ".join(f"{key}: {modules[key]['value']}" for key in ("speed","gear","gameplay_state"))
    cv2.putText(canvas,text,(10,25),cv2.FONT_HERSHEY_SIMPLEX,.5,(255,255,255),1)
    return canvas
