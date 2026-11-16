"""Offline video analysis, using media time, with no made-up physical inputs."""
import argparse
import json
from pathlib import Path
import time
import cv2
from .config import Settings
from .vision import Analyzer

def analyze_video(video_path, output, settings=None, interval=.5, progress=None, cancel=None):
    if interval<=0:raise ValueError("Analysis interval must be positive")
    settings=settings or Settings();output=Path(output)
    output.mkdir(parents=True,exist_ok=False)
    cap=cv2.VideoCapture(str(video_path));count=0
    meta={"schema_version":2,"source":"video-replay","input_kind":"unavailable","assistance_active":False,"complete":False,"clock":"video presentation seconds based on source frame index and FPS","reference_labels":{},"video_name":Path(video_path).name}
    try:
        if not cap.isOpened():raise ValueError("Cannot open video")
        fps=cap.get(cv2.CAP_PROP_FPS)
        if not 0<fps<1000:raise ValueError("Video does not report a valid FPS")
        stride=max(1,round(fps*interval));sequence=0
        analyzer=Analyzer(settings.hud_rois,unit=settings.speed_unit,min_confidence=settings.recognition_confidence)
        with (output/"observations.jsonl").open("w",encoding="utf-8") as observations,(output/"frames.jsonl").open("w",encoding="utf-8") as frames:
            while cap.grab():
                if cancel and cancel.is_set():raise RuntimeError("Video analysis cancelled; partial session retained")
                if sequence%stride==0:
                    ok,image=cap.retrieve()
                    if not ok:raise ValueError("Video frame decode failed")
                    stamp=sequence/fps;reading=analyzer.analyze(image,sequence,stamp)
                    filename=f"{sequence:09d}.jpg"
                    if not cv2.imwrite(str(output/filename),image):raise OSError("Could not write reference image")
                    frames.write(json.dumps({"sequence":sequence,"timestamp":stamp,"file":filename,"input":None,"input_valid":False,"assistance_active":False})+"\n")
                    observations.write(json.dumps(reading,allow_nan=False)+"\n");count+=1
                    if progress:progress(count,stamp)
                sequence+=1
        meta.update(complete=True,saved_frames=count,source_fps=fps)
    except Exception as exc:meta["error"]=str(exc);raise
    finally:
        cap.release();(output/"manifest.json").write_text(json.dumps(meta,indent=2),encoding="utf-8")
    return output

def main():
    parser=argparse.ArgumentParser(description="Analyze a prerecorded local gameplay video")
    parser.add_argument("video");parser.add_argument("--output",required=True);parser.add_argument("--settings");parser.add_argument("--interval",type=float,default=.5)
    args=parser.parse_args();settings=Settings.load(Path(args.settings)) if args.settings else Settings()
    analyze_video(args.video,args.output,settings,args.interval,lambda n,t:print(f"Analyzed {n} frames at {t:.2f}s",flush=True))
    return 0
if __name__=="__main__":raise SystemExit(main())
