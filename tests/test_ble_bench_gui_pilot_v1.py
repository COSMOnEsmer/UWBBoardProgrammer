import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import sys
from pathlib import Path
from PySide6 import QtWidgets as W
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app/ble_prototype/v1'))
from standalone_bench_gui_v3 import Window,Worker,Signals
from uwb_board_programmer.models import Profile


def test_preview_opens_without_connections_and_blocks_cloud_without_live_geometry(tmp_path,monkeypatch):
    app=W.QApplication.instance() or W.QApplication([]);messages=[]
    monkeypatch.setattr(W.QMessageBox,'warning',lambda *args:messages.append(args[-1]))
    window=Window(tmp_path)
    assert window.worker is None and window.cloud is None and window.table.rowCount()==4
    window.languages.setCurrentIndex(1)
    assert window.start.text()=='เชื่อมต่อ BLE'
    window.toggle_cloud();assert window.cloud is None and messages
    window.position.setChecked(True);window.start_capture()
    assert window.worker is None and len(messages)==2
    window.close();app.processEvents()


def test_stop_requests_ble_cleanup_before_processor_finishes_recording(tmp_path):
    app=W.QApplication.instance() or W.QApplication([])
    worker=Worker(tmp_path,Profile.for_mode('tdoa_4'),False,Signals())
    worker.stop()
    assert worker.stop_requested.is_set()
    assert not worker.end.is_set()  # Receiver sets this only after disconnect cleanup.
    worker.file.close()
