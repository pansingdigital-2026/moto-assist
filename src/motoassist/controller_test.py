"""Run without Qt, game capture or OCR: python -m motoassist.controller_test."""
import argparse
from dataclasses import asdict
import json
import logging
from logging.handlers import RotatingFileHandler
import math
import platform
import time
from .config import data_dir
from .controllers import ControllerManager
from .models import InputState

def main():
    parser=argparse.ArgumentParser(description="Xbox controller diagnostic; Ctrl+C to stop")
    parser.add_argument("--backend",choices=("auto","xinput","sdl2"),default="auto")
    parser.add_argument("--device",default="auto")
    parser.add_argument("--seconds",type=float,default=30)
    parser.add_argument("--simulate",action="store_true")
    args=parser.parse_args()
    folder=data_dir()/"logs";folder.mkdir(parents=True,exist_ok=True)
    logging.basicConfig(level=logging.INFO,handlers=[RotatingFileHandler(folder/"controller-diagnostic.log",maxBytes=2_000_000,backupCount=2,encoding="utf-8")],format="%(asctime)s %(levelname)s %(message)s")
    logging.info("Diagnostic platform=%s python=%s backend=%s simulated=%s",platform.platform(),platform.python_version(),args.backend,args.simulate)
    print(f"Move sticks, triggers and buttons. Log: {folder / 'controller-diagnostic.log'}",flush=True)
    manager=None if args.simulate else ControllerManager(args.backend,args.device)
    until=time.perf_counter()+args.seconds;last=None;next_print=0
    try:
        while time.perf_counter()<until:
            now=time.perf_counter()
            sample=InputState(now,True,lx=math.sin(now),rt=.5,buttons=4096 if int(now)%2 else 0) if args.simulate else manager.poll()
            report={"simulated":True} if args.simulate else manager.report()
            if report!=last: print(json.dumps(report,indent=2),flush=True);last=report
            if now>=next_print:
                print(json.dumps(asdict(sample)),flush=True);logging.info("input %s",asdict(sample));next_print=now+.1
            time.sleep(.008)
    except KeyboardInterrupt: pass
    finally:
        if manager: manager.close()
    print("Diagnostic finished. Share controller-diagnostic.log when reporting an issue.")
    return 0

if __name__=="__main__": raise SystemExit(main())
