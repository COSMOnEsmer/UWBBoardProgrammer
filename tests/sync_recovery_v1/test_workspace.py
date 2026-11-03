import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6 import QtWidgets as W
import pytest
from uwb_board_programmer.gui import Window


@pytest.fixture
def window(tmp_path,monkeypatch):
    app=W.QApplication.instance() or W.QApplication([])
    monkeypatch.setattr('uwb_board_programmer.legacy_gui.ports',lambda:[])
    w=Window(tmp_path)
    yield w
    w.close();app.processEvents()


def test_full_workspace_and_survey_confirmation(window):
    assert window.tabs.count()==6 and window.anchor_table.rowCount()==4
    assert not window.survey_confirm.isChecked() and not window.collect().survey_verified
    window.survey_confirm.setChecked(True)
    assert window.collect().survey_verified
    assert window.clock_table.horizontalHeaderItem(3).text()=='VALIDATION ns'


def test_thai_confirmation_and_legacy_controls(window):
    window.language_combo.setCurrentIndex(1)
    assert 'ยืนยัน' in window.survey_confirm.text()
    window.language_combo.setCurrentIndex(0)
    window.transport_combo.setCurrentIndex(1)
    assert window.start_button.text()=='Start anchors'


def test_unverified_survey_blocks_cloud_before_network(window,monkeypatch):
    monkeypatch.setattr('uwb_board_programmer.legacy_gui.CloudClient',lambda *a,**k:pytest.fail('No cloud before survey'))
    with pytest.raises(ValueError,match='confirmed measured'):window.connect_cloud()


def test_profile_confirmation_saved_and_loaded(window):
    from uwb_board_programmer.models import Profile
    window.survey_confirm.setChecked(True)
    value=window.collect().to_dict()
    assert Profile.from_dict(value).survey_verified
    value.pop('survey_verified')
    assert not Profile.from_dict(value).survey_verified
