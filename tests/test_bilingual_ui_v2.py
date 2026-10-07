import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6 import QtWidgets as W
from uwb_board_programmer.gui import Window
from uwb_board_programmer.models import Profile

def test_mode_switch_rebuilds_device_rows_and_preserves_tag_port(tmp_path,monkeypatch):
    app=W.QApplication.instance() or W.QApplication([])
    monkeypatch.setattr('uwb_board_programmer.gui.ports',lambda:[])
    window=Window(tmp_path);window.port_boxes[3].setCurrentText('COM91');window.rev_boxes[3].setCurrentIndex(3)
    window.port_boxes[0].setCurrentText('COM81');window.rev_boxes[0].setCurrentIndex(4)
    window.mode_combo.setCurrentIndex(1);app.processEvents()
    assert window.profile.mode=='tdoa_4' and window.device_table.rowCount()==5 and window.anchor_table.rowCount()==4
    assert window.clock_table.rowCount()==3 and window.target.count()==5
    assert window.collect().tag_port=='COM91' and window.port_boxes[4].currentText()=='COM91'
    assert window.rev_boxes[4].currentIndex()==3 and window.rev_boxes[0].currentIndex()==4
    window.port_boxes[3].setCurrentText('COM84')
    for col,value in zip((3,4,5),('1','2','3.1')):window.anchor_table.item(3,col).setText(value)
    window.mode_combo.setCurrentIndex(0);app.processEvents()
    assert window.device_table.rowCount()==4 and window.port_boxes[3].currentText()=='COM91'
    window.mode_combo.setCurrentIndex(1);app.processEvents()
    assert window.port_boxes[3].currentText()=='COM84' and window.anchor_table.item(3,5).text()=='3.1'
    window.close()

def test_thai_toggle_keeps_machine_values_and_persists_new_settings(tmp_path,monkeypatch):
    app=W.QApplication.instance() or W.QApplication([]);monkeypatch.setattr('uwb_board_programmer.gui.ports',lambda:[])
    window=Window(tmp_path);window.port_boxes[0].setCurrentText('COM82');original_mac=window.tag_mac.text()
    window.language_combo.setCurrentIndex(1);app.processEvents()
    assert window.page_title.text()=='บอร์ดและเฟิร์มแวร์'
    assert window.mode_combo.currentData()=='hybrid_3' and window.rev_boxes[0].currentText()=='ยังไม่ทราบ'
    assert window.anchor_table.item(0,2).text()=='master' and window.tag_mac.text()==original_mac
    assert window.port_boxes[0].currentText()=='COM82' and window.blink.cleanText().isascii()
    assert 'ค้นหาพอร์ต' in ' '.join(b.text() for b in window.findChildren(W.QPushButton))
    window.language_combo.setCurrentIndex(0);app.processEvents()
    assert window.page_title.text()=='Devices & firmware' and window.rev_boxes[0].currentText()=='Unknown'
    assert len(list((tmp_path/'data/ui-settings').glob('*.json')))==2
    window.language_combo.setCurrentIndex(1);window.close();again=Window(tmp_path)
    assert again.language=='th' and again.page_title.text()=='บอร์ดและเฟิร์มแวร์';again.close()

def test_loaded_four_profile_and_mode_locked_while_cloud_connected(tmp_path,monkeypatch):
    app=W.QApplication.instance() or W.QApplication([]);messages=[]
    monkeypatch.setattr(W.QMessageBox,'warning',lambda *args:messages.append(args[-1]))
    window=Window(tmp_path);window.profile=Profile.for_mode('tdoa_4');window.populate_profile()
    assert window.mode_combo.currentData()=='tdoa_4' and window.port_boxes[4].currentText()==''
    class Cloud:
        connected=False;ready=False;ack_ok=0;ack_error=0;dropped=0
        def close(self):pass
    window.cloud=Cloud();window.refresh_status();assert not window.mode_combo.isEnabled()
    window.mode_combo.setCurrentIndex(0);app.processEvents()
    assert window.profile.mode=='tdoa_4' and window.mode_combo.currentData()=='tdoa_4' and messages
    window.close()
