"""No hardware used: verify selected-only preparation with one reusable port."""
import pytest
from PySide6 import QtWidgets as W
from uwb_board_programmer.gui import Window

def window_with_fake_flasher(tmp_path,monkeypatch,mode):
    app=W.QApplication.instance() or W.QApplication([]);calls=[]
    monkeypatch.setattr('uwb_board_programmer.gui.ports',lambda:[])
    class Flasher:
        def __init__(self,*args):pass
        def flash(self,image,port,revision,model):calls.append((image,port,revision,model))
        def setup_tag(self,images,port,revision,profile):calls.append(('tag',port,revision,profile.tag_mac,profile.blink_interval_ms))
    monkeypatch.setattr('uwb_board_programmer.gui.Flasher',Flasher)
    window=Window(tmp_path);window.mode_combo.setCurrentIndex(1 if mode=='tdoa_4' else 0)
    monkeypatch.setattr(window,'available_images',lambda:{'master':'master-image','slave':'slave-image','tag_setup':'setup-image','tag_battery':'battery-image'})
    monkeypatch.setattr(window,'job',lambda fn,*args:fn())
    return window,calls

@pytest.mark.parametrize('mode',['hybrid_3','tdoa_4'])
def test_one_usb_port_reused_for_every_anchor_then_tag(tmp_path,monkeypatch,mode):
    window,calls=window_with_fake_flasher(tmp_path,monkeypatch,mode);count=len(window.profile.anchors)
    # Deliberately incomplete survey and invalid bounds must not block flashing.
    window.bounds.setText('survey not entered yet');window.anchor_table.item(0,3).setText('1.2')
    window.anchor_table.item(1,6).setText('orientation not entered yet');window.tag_mac.setText('tag settings not ready')
    for selected in range(count):
        for i in range(count+1):window.port_boxes[i].setCurrentText('');window.rev_boxes[i].setCurrentIndex(0)
        window.target.setCurrentIndex(selected);window.port_boxes[selected].setCurrentText('COM9 — only connected EVK');window.rev_boxes[selected].setCurrentIndex(3)
        before=window.profile.to_dict();window.flash_selected();assert window.profile.to_dict()==before
        assert calls[-1]==('master-image' if selected==0 else 'slave-image','COM9',3,'Type2BP')
    # Another board can occupy the same named USB port after the prior job ends.
    for i in range(count+1):window.port_boxes[i].setCurrentText('');window.rev_boxes[i].setCurrentIndex(0)
    window.target.setCurrentIndex(count);window.port_boxes[count].setCurrentText('COM9');window.rev_boxes[count].setCurrentIndex(3)
    window.tag_mac.setText('0200000000000101');window.blink.setValue(750);window.flash_selected()
    assert calls[-1]==('tag','COM9',3,'0200000000000101',750) and len(calls)==count+1;window.close()

def test_single_board_still_checks_selected_revision_and_port(tmp_path,monkeypatch):
    window,calls=window_with_fake_flasher(tmp_path,monkeypatch,'tdoa_4');window.target.setCurrentIndex(3)
    with pytest.raises(ValueError,match='revision'):window.flash_selected()
    window.rev_boxes[3].setCurrentIndex(3)
    with pytest.raises(ValueError,match='COM port'):window.flash_selected()
    window.port_boxes[3].setCurrentText('invalid-port')
    with pytest.raises(ValueError,match='COM port'):window.flash_selected()
    assert calls==[];window.close()

def test_tag_mac_is_validated_before_programming(tmp_path,monkeypatch):
    window,calls=window_with_fake_flasher(tmp_path,monkeypatch,'tdoa_4');window.target.setCurrentIndex(4)
    window.rev_boxes[4].setCurrentIndex(3);window.port_boxes[4].setCurrentText('COM9');window.tag_mac.setText('invalid')
    with pytest.raises(ValueError,match='tag MAC'):window.flash_selected()
    assert calls==[];window.close()

def test_live_acquisition_still_requires_all_anchor_ports(tmp_path,monkeypatch):
    window,calls=window_with_fake_flasher(tmp_path,monkeypatch,'tdoa_4');window.port_boxes[0].setCurrentText('COM9')
    with pytest.raises(ValueError,match='COM port'):window.open_anchors(False)
    assert window.controller is None and calls==[];window.close()
