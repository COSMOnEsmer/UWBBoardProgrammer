import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from pathlib import Path
from types import SimpleNamespace
from PySide6 import QtWidgets as W
from uwb_board_programmer.gui import Window
from uwb_board_programmer.cloud import CloudClient
from uwb_board_programmer.models import Profile

APP=W.QApplication.instance() or W.QApplication([])
ROOT=Path(__file__).resolve().parents[2]

def test_accepted_fix_updates_live_metrics_and_keeps_gui_timer_running():
    w=Window(ROOT)
    try:
        f=dict(x_m=1.155,y_m=.181,z_m=1.306,time="2026-11-04T09:43:31.865Z",num_anchors_used=4,accuracy_m=1.066,z_uncertainty_m=.994,residual=0.)
        w.show_fix(f)
        w.refresh_status()
        assert w.position_values["X"].text()=="1.155"
        assert w.position_values["Z"].text()=="1.306"
        assert w.latest_fix==f
        APP.processEvents()
    finally:w.close()

def test_position_ack_is_distinct_from_heartbeat_and_rejection():
    log=[];c=CloudClient(Profile.for_mode("tdoa_4"),"test-token","test-gateway",log.append,lambda:{})
    c.sio=SimpleNamespace(call=lambda *a,**k:{"ok":True})
    assert c.ack("edge:heartbeat",{})
    assert c.ack_events.get("edge:position",0)==0
    assert c.ack("edge:position",{"tag_id":"T1","time":"now"})
    assert c.ack_events["edge:position"]==1 and c.ack_ok==2
    assert "position acknowledged" in log[-1]
    c.sio=SimpleNamespace(call=lambda *a,**k:{"ok":False})
    assert not c.ack("edge:position",{})
    assert c.error_events["edge:position"]==1 and c.ack_events["edge:position"]==1
