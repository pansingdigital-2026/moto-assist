import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
import time
from PySide6.QtWidgets import QApplication
from motoassist.config import Settings
from motoassist.ui import Window

def test_desktop_workflow(tmp_path):
    app=QApplication.instance() or QApplication([])
    window=Window(Settings(),tmp_path,simulate=True);window.show()
    try:
        end=time.perf_counter()+3
        while window.runtime.frame is None and time.perf_counter()<end:
            app.processEvents();time.sleep(0.02)
        window.refresh()
        assert window.tabs.count()==5
        assert "SIMULATION" in window.connection.text()
        assert window.preview.pixmap() and not window.preview.pixmap().isNull()
        window.record(); assert window.runtime.recorder
        end=time.perf_counter()+0.3
        while time.perf_counter()<end:app.processEvents();time.sleep(0.02)
        window.mode.setCurrentText("Balanced");window.sim_enabled.setChecked(True);window.refresh()
        assert "simulation only" in window.sim_result.text()
        window.emergency_stop()
        assert not window.runtime.recorder and not window.sim_enabled.isChecked()
        assert len(window.db.sessions())==1
        window.save_settings(); assert (tmp_path/"settings.json").exists()
    finally:window.quit();app.processEvents()
    assert all(not t.is_alive() for t in window.runtime.threads)
