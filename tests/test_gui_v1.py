import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
from PySide6 import QtWidgets as W
from uwb_board_programmer.gui import Window

def test_desktop_default_blocks_missing_geometry_and_flash(tmp_path,monkeypatch):
    app=W.QApplication.instance() or W.QApplication([]);messages=[]
    monkeypatch.setattr(W.QMessageBox,'warning',lambda *a:messages.append(a[-1]))
    window=Window(tmp_path);window.show();app.processEvents()
    assert window.tabs.count()==5;assert window.controller is None;assert window.cloud is None
    window.open_button.click();assert window.controller is None;assert any('COM' in x or 'พิกัด' in x for x in messages)
    window.flash_button.click();assert any('revision' in x for x in messages);assert not window.busy
    window.save_profile();saved=list((tmp_path/'config/profiles').glob('*.json'));assert len(saved)==1
    window.save_profile();assert len(list((tmp_path/'config/profiles').glob('*.json')))==2
    window.close();app.processEvents()
