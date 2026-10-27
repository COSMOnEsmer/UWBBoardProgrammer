import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
from types import SimpleNamespace
import sys,time
import pytest
from PySide6 import QtWidgets as W
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app/ble_prototype/v1'))
import uwb_ble_flasher as flash
from standalone_bench_gui_v7 import Window


def prepare(tmp_path,monkeypatch):
    app=W.QApplication.instance() or W.QApplication([])
    entry=dict(anchor_slot='A1',model='Type2BP',image_label='master',provisioned_mac='0200000000000001')
    monkeypatch.setattr(flash,'latest_bundle',lambda root:(tmp_path/'bundle.json',[entry]))
    monkeypatch.setattr(flash,'inventory',lambda:[SimpleNamespace(device='COM99',serial_number='TEST-ONLY')])
    return app,Window(tmp_path)


def test_flash_does_not_default_an_anchor_image_onto_the_first_usb_device(tmp_path,monkeypatch):
    app,window=prepare(tmp_path,monkeypatch);warnings=[]
    monkeypatch.setattr(W.QDialog,'exec',lambda self:W.QDialog.Accepted)
    monkeypatch.setattr(W.QMessageBox,'warning',lambda *args:warnings.append(args[-1]))
    monkeypatch.setattr(flash,'flash_selected',lambda *a:pytest.fail('No explicit board selection'))
    window.flash_button.click()
    assert not window.flashing and warnings and 'explicitly' in warnings[0]
    window.close();app.processEvents()


def test_explicit_one_board_selection_does_not_require_other_ports_or_survey(tmp_path,monkeypatch):
    app,window=prepare(tmp_path,monkeypatch);calls=[]
    def choose(dialog):
        boxes=dialog.findChildren(W.QComboBox)
        boxes[0].setCurrentIndex(0);boxes[1].setCurrentIndex(0)
        return W.QDialog.Accepted
    monkeypatch.setattr(W.QDialog,'exec',choose)
    def program(root,image,port,serial,log):calls.append((port,serial));return dict(program_verify_passed=True)
    monkeypatch.setattr(flash,'flash_selected',program)
    window.flash_button.click();deadline=time.monotonic()+2
    while window.flashing and time.monotonic()<deadline:app.processEvents();time.sleep(.01)
    assert calls==[('COM99','TEST-ONLY')] and not window.flashing
    assert all(a.position is None for a in window.profile.anchors)
    window.close();app.processEvents()
