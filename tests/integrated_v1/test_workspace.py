import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import json
from types import SimpleNamespace
from PySide6 import QtWidgets as W
import pytest
pytest.importorskip('uwb_board_programmer.ble_controller',reason='Select the v5 test environment with tests/integrated_v1/pytest.ini')
from uwb_board_programmer.gui import Window
from uwb_board_programmer.models import Profile
from uwb_board_programmer import standalone_flashing as flash


@pytest.fixture
def window(tmp_path,monkeypatch):
    app=W.QApplication.instance() or W.QApplication([])
    monkeypatch.setattr('uwb_board_programmer.legacy_gui.ports',lambda:[])
    w=Window(tmp_path)
    yield w
    w.close();app.processEvents()


def test_full_original_workflow_and_ble_settings_are_present(window):
    assert window.tabs.count()==6 and window.navigation.count()==6
    assert window.device_table.rowCount()==5 and window.anchor_table.rowCount()==4
    assert window.transport_combo.currentData()=='ble'
    assert window.controller is None and window.cloud is None
    assert window.plot and window.clock_table and window.publish_raw and window.token
    assert not window.flash_all_button.isVisible()
    assert window.start_button.text()=='Start positioning'


def test_language_and_transport_switch_preserve_ids_and_original_usb_controls(window):
    window.language_combo.setCurrentIndex(1)
    assert window.page_title.text()=='บอร์ดและเฟิร์มแวร์'
    window.navigation.setCurrentRow(1)
    assert window.page_title.text()=='BLE / GATT' and window.ble_scan_button.text()=='ค้นหา Anchor BLE'
    mac=window.tag_mac.text();window.transport_combo.setCurrentIndex(1)
    assert window.collect().transport=='usb' and not window.tag_mac.isReadOnly()
    window.language_combo.setCurrentIndex(0)
    assert window.start_button.text()=='Start anchors' and window.tag_mac.text()==mac
    window.transport_combo.setCurrentIndex(0)
    assert window.tag_mac.isReadOnly() and window.start_button.text()=='Start positioning'


def test_ble_scan_mapping_and_settings_roundtrip_in_profile(window):
    window.scan_finished([dict(mac='0200000000000001',role='master',address='AA:BB:CC:DD:EE:FF',rssi=-55)])
    assert window.ble_table.rowCount()==1
    window.ble_table.setCurrentCell(0,0);window.assign_ble()
    window.ble_scan_mode.setCurrentIndex(1);window.ble_scan_seconds.setValue(9)
    p=Profile.from_dict(window.collect().to_dict())
    assert p.transport=='ble' and p.ble_scan_mode=='active' and p.ble_scan_seconds==9
    assert p.anchors[0].mac=='0200000000000001'
    window.ble_bind_target.setCurrentIndex(1)
    with pytest.raises(ValueError,match='role'):window.assign_ble()


def test_single_board_flash_uses_native_workflow_without_other_ports_or_geometry(window,tmp_path,monkeypatch):
    images=[dict(image_label='slave4',model='Type2BP',role='slave',provisioned_mac='0200000000000004',interval_ms=500)]
    path=tmp_path/'bundle.json';path.write_text(json.dumps(dict(images=images)))
    window.firmware_combo.addItem('test',str(path));window.target.setCurrentIndex(3)
    window.port_boxes[3].setCurrentText('COM99');window.rev_boxes[3].setCurrentText('4.1')
    window.bounds.setText('survey not entered');window.anchor_table.item(0,3).setText('incomplete')
    monkeypatch.setattr(flash,'inventory',lambda:[SimpleNamespace(device='COM99',serial_number='TEST-ONLY')])
    calls=[]
    monkeypatch.setattr(flash,'flash_selected',lambda root,entry,port,serial,log:calls.append((entry['image_label'],port,serial)))
    monkeypatch.setattr(window,'job',lambda function,*args:function())
    window.flash_selected()
    assert calls==[('slave4','COM99','TEST-ONLY')]


def test_flash_slot_mismatch_is_rejected_before_hardware(window,tmp_path,monkeypatch):
    path=tmp_path/'bundle.json';path.write_text(json.dumps(dict(images=[dict(image_label='master',model='Type2BP',role='master',provisioned_mac='0200000000000001')])))
    window.firmware_combo.addItem('test',str(path));window.target.setCurrentIndex(0)
    window.port_boxes[0].setCurrentText('COM99');window.rev_boxes[0].setCurrentText('4.1')
    window.anchor_table.item(0,1).setText('0200000000000099')
    monkeypatch.setattr(flash,'inventory',lambda:pytest.fail('Mismatch must stop before hardware access'))
    with pytest.raises(ValueError,match='provisions'):window.flash_selected()


def test_live_positioning_requires_survey_without_opening_com_ports(window,monkeypatch):
    monkeypatch.setattr('uwb_board_programmer.gui.BleController',lambda *a,**k:pytest.fail('No receiver before valid survey'))
    with pytest.raises(ValueError,match='surveyed'):window.open_anchors(False)
    assert window.controller is None


def test_original_usb_controller_is_used_when_usb_mode_is_selected(window,monkeypatch):
    window.transport_combo.setCurrentIndex(1)
    for index,xyz in enumerate([(0,0,0),(10,0,0),(0,8,0),(0,0,4)]):
        window.port_boxes[index].setCurrentText('COM'+str(index+81))
        for column,value in zip((3,4,5),xyz):window.anchor_table.item(index,column).setText(str(value))
    calls=[]
    class Controller:
        def __init__(self,root,profile,*args,**kwargs):
            calls.append((profile.transport,[a.port for a in profile.anchors],kwargs['diagnostic']))
            self.record=SimpleNamespace(path='test-session');self.cloud=None
        def close(self):pass
    monkeypatch.setattr('uwb_board_programmer.legacy_gui.Controller',Controller)
    monkeypatch.setattr(window,'refresh_status',lambda:None)
    window.open_anchors(False)
    assert calls==[('usb',['COM81','COM82','COM83','COM84'],False)]


def test_ble_capture_can_open_without_ports_or_coordinates(window,monkeypatch):
    calls=[]
    class Controller:
        def __init__(self,root,profile,*args,**kwargs):
            calls.append((profile.transport,kwargs['diagnostic']))
            self.record=SimpleNamespace(path='test-session');self.cloud=None
        def close(self):pass
    monkeypatch.setattr('uwb_board_programmer.gui.BleController',Controller)
    monkeypatch.setattr(window,'refresh_status',lambda:None)
    window.open_anchors(True)
    assert calls==[('ble',True)]


def test_credential_reload_from_original_app_remains_available(tmp_path,monkeypatch):
    app=W.QApplication.instance() or W.QApplication([]);calls=[]
    monkeypatch.setattr(Window,'load_latest_credentials',lambda self:calls.append(True))
    w=Window(tmp_path)
    assert calls==[True]
    w.close();app.processEvents()
