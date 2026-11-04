import asyncio
import os
import threading
import pytest
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from uwb_board_programmer.models import Profile
import uwb_battery_calibration.capture as backend

@pytest.mark.parametrize('restore_ok',[True,False])
def test_ble_capture_retains_quality_and_reports_restore_failure(monkeypatch,restore_ok):
    profile=Profile.for_mode('tdoa_4');ids=[a.id for a in profile.anchors];links=[]
    class Tag:
        def __init__(self,*args):self.info={'firmware':'1.5.0-pilot'}
        async def __aenter__(self):return self
        async def __aexit__(self,*args):
            if not restore_ok:raise ConnectionError('Tag restore not acknowledged')
        def remaining(self):return 500
    class Network:
        def __init__(self,bindings,log,**kwargs):
            links.append([b.anchor_id for b in bindings]);self.clients={b.anchor_id:None for b in bindings}
            self.info={};self.last_restore_acknowledged=True
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def measure_tag(self,aid,tag,seconds):
            assert seconds==20
            return {'records':[dict(distance_m=1.5,status=0,nlos=False) for _ in range(20)]}
    async def discover(*args):return [dict(mac=a.mac) for a in profile.anchors]
    monkeypatch.setattr(backend,'BleSurveyTag',Tag);monkeypatch.setattr(backend,'SurveyNetwork',Network);monkeypatch.setattr(backend,'discover',discover)
    value=asyncio.run(backend.capture_reference_ble(profile,lambda _:None,threading.Event(),known_position=[0,0,0]))
    assert set(value['ranges'])==set(ids)
    assert all(len(link)<=2 for link in links)  # Plus the Tag: <=3 GATT links.
    assert value['complete'] is restore_ok and value['radio_restoration_acknowledged'] is restore_ok
    assert ('Tag BLE' in value['errors']) is not restore_ok

def test_battery_wizard_does_not_require_com_to_start_capture(tmp_path,monkeypatch):
    from PySide6 import QtWidgets as W
    from uwb_board_programmer.survey_wizard import AutoSurveyDialog
    app=W.QApplication.instance() or W.QApplication([])
    monkeypatch.setattr('uwb_board_programmer.survey_wizard.inventory',lambda:[])
    dialog=AutoSurveyDialog(tmp_path,Profile.for_mode('tdoa_4'))
    try:
        assert dialog.tag_control.currentData()=='ble' and not dialog.restore_battery.isChecked()
        for field in (dialog.measured_x,dialog.measured_y,dialog.measured_z):field.setText('1')
        dialog.axes_confirm.setChecked(True);dialog.fixed_positions.setChecked(True)
        operations=[];dialog.run_job=lambda operation,callback:operations.append(operation)
        dialog.capture_point('origin')
        assert len(operations)==1 and dialog.tag_port.count()==0
        dialog.tag_control.setCurrentIndex(1)
        with pytest.raises(ValueError,match='USB'):dialog.capture_point('origin')
    finally:dialog.close();app.processEvents()
