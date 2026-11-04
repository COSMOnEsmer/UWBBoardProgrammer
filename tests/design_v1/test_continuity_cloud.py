import time
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
from PySide6 import QtWidgets as W
from uwb_board_programmer.models import Profile,TICK_S,C_M_S
from uwb_board_programmer.continuity import PreviewClock,ContinuousDisplay
from uwb_board_programmer.cloud import CloudClient
from uwb_board_programmer.gateway_setup import GatewaySetup
from uwb_board_programmer.panels import Panel

def profile():
    p=Profile.for_mode('tdoa_4');p.survey_verified=True;p.bounds=[[-2,-2,0],[2,2,3]]
    for a,xyz in zip(p.anchors,[[-1,1,1],[1,1,2],[1,-1,1],[-1,-1,1]]):a.position=xyz
    return p

def config(p):return dict(site=dict(id='my-site'),floors=[dict(id='my-floor',name='My floor')],anchors=[dict(id=a.id,floorId='my-floor',role=a.role,posXM=a.position[0],posYM=a.position[1],posZM=a.position[2]) for a in p.anchors])

def test_preview_clock_is_bounded_and_separate_from_strict_validation():
    c=PreviewClock();one=round(1/TICK_S);c.add(0,100,0);c.add(one,one+100,0)
    assert abs(c.correct(one//2)-(one//2+100))<2
    with pytest.raises(ValueError):c.correct(3*one)
    c.last=time.monotonic()-3
    with pytest.raises(ValueError):c.correct(one)

def test_continuity_uses_real_matching_frames_and_never_accepts_them():
    p=profile();d=ContinuousDisplay(p);one=round(1/TICK_S);offsets={a.id:i*10000 for i,a in enumerate(p.anchors)}
    for a in p.anchors[1:]:d.sync(a.id,offsets[a.id],0,0);d.sync(a.id,one+offsets[a.id],one,0)
    target=np.array([.2,.3,1.4])
    for a in p.anchors:
        rx=one//2+round(np.linalg.norm(target-a.position)/(TICK_S*C_M_S))+offsets[a.id]
        d.blink(SimpleNamespace(anchor_id=a.id,frame_number=7,received_utc='2026-11-04T00:00:00Z'),rx)
    assert d.count==1 and d.latest['accepted'] is False and d.latest['display_only'] is True
    assert np.linalg.norm(np.array([d.latest[k] for k in ('x_m','y_m','z_m')])-target)<.02
    d.reset(p.anchors[0].id);assert d.latest is None and all(not c.samples for c in d.clocks.values())

def test_gateway_auth_configuration_and_publish_gate_are_separate():
    p=profile();client=CloudClient(p,'unit-test-token','gateway-id',lambda _:None,lambda:{})
    client.apply_config(config(p));assert not client.ready and client.config_issue
    client.connected=True;client.enqueue('edge:position',{'x_m':1});assert client.queue.empty()
    p.site_id='my-site';p.floor_id='my-floor';client.apply_config(config(p));assert client.ready

def test_gateway_mapping_uses_server_scope_without_asserting_measurements():
    app=W.QApplication.instance() or W.QApplication([]);p=profile();dlg=GatewaySetup(p,config(p))
    dlg.coordinates.setChecked(True);dlg.apply()
    assert dlg.result_profile.site_id=='my-site' and dlg.result_profile.floor_id=='my-floor'
    assert not dlg.result_profile.survey_verified
    assert p.site_id!='my-site';dlg.close()

def test_floating_window_has_its_own_attach_button():
    app=W.QApplication.instance() or W.QApplication([]);owner=W.QMainWindow();panel=Panel('Live panel',owner);owner.setCentralWidget(panel);owner.show()
    panel.float_or_dock();app.processEvents();button=next(b for b in panel.dialog.findChildren(W.QPushButton) if b.text()=='Attach')
    button.click();app.processEvents();assert panel.dialog is None and panel.body.parentWidget()==panel;owner.close()

def test_application_has_no_site_branding_constants():
    source=Path(__file__).resolve().parents[2]/'app/revisions/v15'
    assert all('KMUTNB' not in p.read_text(encoding='utf8') for p in source.rglob('*.py'))
