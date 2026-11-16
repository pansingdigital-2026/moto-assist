import argparse
import json
import logging
from logging.handlers import RotatingFileHandler
import os
import sys
from .config import Settings, data_dir

def main():
    parser=argparse.ArgumentParser(description="MotoAssist monitoring and recording")
    sources=parser.add_mutually_exclusive_group()
    sources.add_argument("--simulate",action="store_true",help="Synthetic frames and controller")
    sources.add_argument("--video",help="Replay a local video with synthetic controller inputs")
    parser.add_argument("--smoke-seconds",type=float,help="Automatically close UI after a smoke test")
    args=parser.parse_args()
    directory=data_dir(); directory.mkdir(parents=True,exist_ok=True)
    (directory/"logs").mkdir(exist_ok=True)
    handler=RotatingFileHandler(directory/"logs/motoassist.log",maxBytes=2_000_000,backupCount=3,encoding="utf-8")
    logging.basicConfig(level=logging.INFO,handlers=[handler],format="%(asctime)s %(levelname)s %(threadName)s %(message)s")
    controller_log=RotatingFileHandler(directory/"logs/controller-detection.log",maxBytes=2_000_000,backupCount=3,encoding="utf-8")
    controller_log.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(threadName)s %(message)s"))
    logging.getLogger("motoassist.controllers").addHandler(controller_log)
    from .windows import enable_dpi_awareness
    enable_dpi_awareness()
    from PySide6.QtWidgets import QApplication, QMessageBox
    from PySide6.QtCore import QTimer
    from .ui import Window
    app=QApplication(sys.argv); app.setApplicationName("MotoAssist")
    try: settings=Settings.load(directory/"settings.json")
    except Exception as exc:
        QMessageBox.critical(None,"Invalid MotoAssist settings",f"{exc}\nCorrect or rename {directory / 'settings.json'} and relaunch."); return 1
    if os.name!="nt" and not args.simulate and not args.video:
        QMessageBox.information(None,"Windows integration unavailable","Starting simulation on this non-Windows host."); args.simulate=True
    window=Window(settings,directory,args.simulate,args.video); window.show()
    if args.smoke_seconds: QTimer.singleShot(int(args.smoke_seconds*1000),window.quit)
    logging.info("Application started; simulation=%s video=%s assistance_active=false",args.simulate,bool(args.video))
    return app.exec()

if __name__=="__main__": raise SystemExit(main())
