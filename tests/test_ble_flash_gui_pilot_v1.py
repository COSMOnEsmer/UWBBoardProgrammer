import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
from types import SimpleNamespace
import sys,time
from PySide6 import QtWidgets as W
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app/ble_prototype/v1'))
import uwb_ble_flasher as flash
from standalone_bench_gui_v6 import Window


def test_flash_button_accepts_one_port_without_survey_or_other_boards(tmp_path,monkeypatch):
    app=W.QApplication.instance() or W.QApplication([]);calls=[]
    entry=dict(anchor_slot='A1',model='Type2BP',image_label='master',provisioned_mac='0200000000000001')
    monkeypatch.setattr(flash,'latest_bundle',lambda root:(tmp_path/'bundle.json',[entry]))
    monkeypatch.setattr(flash,'inventory',lambda:[SimpleNamespace(device='COM99',serial_number='TEST-ONLY')])
    def program(root,image,port,serial,log):
        calls.append((port,serial,image['image_label']));return dict(program_verify_passed=True,configuration_acknowledged=True)
    monkeypatch.setattr(flash,'flash_selected',program)
    monkeypatch.setattr(W.QDialog,'exec',lambda self:W.QDialog.Accepted)
    window=Window(tmp_path)
    assert all(a.position is None for a in window.profile.anchors)
    window.flash_button.click()
    deadline=time.monotonic()+2
    while window.flashing and time.monotonic()<deadline:app.processEvents();time.sleep(.01)
    assert calls==[('COM99','TEST-ONLY','master')]
    assert not window.flashing and window.flash_button.isEnabled()
    window.close();app.processEvents()
