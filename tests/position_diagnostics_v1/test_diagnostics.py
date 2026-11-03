import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import math
from types import SimpleNamespace
import pytest
from PySide6 import QtWidgets as W
from uwb_board_programmer.models import Profile
from uwb_board_programmer.positioning import Solver
from uwb_board_programmer.engine import Pipeline
from uwb_board_programmer.ble_controller import BleController
from uwb_board_programmer.diagnostics import diagnostic_lines
from uwb_board_programmer.gui import Window


@pytest.fixture
def profile():
    p=Profile.for_mode('tdoa_4');p.survey_verified=True;p.bounds=[[-2,-2,0],[2,2,3]]
    for anchor,position in zip(p.anchors,[[-1,1,1],[1,1,2],[1,-1,1],[-1,-1,1]]):anchor.position=position
    return p


def test_exact_reference_still_reports_configured_uncertainty_limit(profile):
    # At (0,0,1.5), every anchor is exactly 1.5 m away. The application's
    # 0.30 m pairwise noise assumption still predicts Z95 > its 1 m limit.
    solver=Solver(profile)
    observations={a.id:SimpleNamespace(status=0,nlos=False) for a in profile.anchors}
    with pytest.raises(ValueError,match='uncertainty exceeds'):
        solver.solve(observations,{a.id:10**15 for a in profile.anchors})
    assert solver.last_diagnostic['z_uncertainty_m']==pytest.approx(1.247336,rel=1e-4)
    assert solver.previous is None


def test_rejection_explanation_survives_later_sync_status(profile):
    pipe=Pipeline(profile)
    pipe.reject('Fix uncertainty exceeds threshold',{'z_uncertainty_m':5.2,'max_z_uncertainty_m':1.0})
    pipe.last_solver_rejection=pipe.last_rejection
    pipe.reason='SYNC synced'
    state={**pipe.snapshot(),'running':True,'diagnostic':False}
    lines='\n'.join(diagnostic_lines(state))
    assert 'Fix uncertainty exceeds threshold' in lines and '5.20 m' in lines
    assert pipe.fix_count==0 and pipe.rejection_counts=={'Fix uncertainty exceeds threshold':1}


def test_repeated_start_retains_clock_epoch(profile,tmp_path):
    controller=BleController(tmp_path,profile,lambda _:None,lambda _:None,autostart_threads=False)
    try:
        controller.handle_event('__processing__','start',{})
        clock=controller.pipe.clocks[profile.anchors[1].id]
        controller.handle_event('__processing__','start',{})
        controller.command('start')
        assert controller.pipe.clocks[profile.anchors[1].id] is clock
        assert controller.queue.empty() and controller.running
    finally:controller.close()


def test_diagnostics_distinguish_capture_and_not_started():
    assert 'Close capture' in diagnostic_lines({'diagnostic':True})[0]
    assert 'Press Start' in diagnostic_lines({'running':False})[0]
    text='\n'.join(diagnostic_lines({'running':True,'clocks':{
        'A3':{'ready':False,'not_ready_reason':'Clock validation exceeds 2 ns','rms_ns':2.794}}}))
    assert '2.79 ns' in text and 'A3' in text


def test_live_start_button_and_failure_text(profile,tmp_path,monkeypatch):
    app=W.QApplication.instance() or W.QApplication([])
    monkeypatch.setattr('uwb_board_programmer.legacy_gui.ports',lambda:[])
    window=Window(tmp_path);window.profile=profile;window.populate_profile()
    controller=BleController(tmp_path,profile,lambda _:None,lambda _:None,autostart_threads=False)
    window.controller=controller
    try:
        controller.running=True
        controller.pipe.reject('Fix uncertainty exceeds threshold',{'z_uncertainty_m':5.2,'max_z_uncertainty_m':1.})
        controller.pipe.last_solver_rejection=controller.pipe.last_rejection
        window.refresh_status()
        assert not window.start_button.isEnabled() and window.stop_button.isEnabled()
        assert '5.20 m' in window.position_issue.text()
        controller.running=False;window.refresh_status()
        assert window.start_button.isEnabled() and not window.stop_button.isEnabled()
        window.language_combo.setCurrentIndex(1);controller.running=True;window.refresh_status()
        assert 'ความไม่แน่นอน' in window.position_issue.text()
    finally:window.close();app.processEvents()
