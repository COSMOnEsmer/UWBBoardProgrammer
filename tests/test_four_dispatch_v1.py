import time
from PySide6 import QtWidgets as W
from uwb_board_programmer.models import Profile
from uwb_board_programmer import controller
from uwb_board_programmer.gui import Window
from test_four_anchor_v1 import four

def test_four_waits_for_all_config_acks_before_start(four,tmp_path,monkeypatch):
    readers={}
    class Reader:
        def __init__(self,a,baud,on_line,log):self.anchor=a;self.cb=on_line;self.connected=True;self.history=[];readers[a.id]=self
        def hello(self):return {'v':1,'kind':'hello','model':'Type2BP','role':self.anchor.role,'version':'1.0.0','state':'ready','mac':self.anchor.mac,'boot':'1234'}
        def start(self):self.cb(self.anchor.id,self.hello())
        def send(self,cmd):
            self.history.append(cmd)
            if cmd=='E2E START':self.cb(self.anchor.id,{'kind':'status','state':'running','code':0})
        def close(self):self.connected=False
    monkeypatch.setattr(controller,'SerialReader',Reader);c=controller.Controller(tmp_path,four,lambda *a:None,lambda *a:None)
    try:
        deadline=time.monotonic()+3
        while len(c.hello)<4 and time.monotonic()<deadline:time.sleep(.01)
        c.command('start')
        while not all(r.history for r in readers.values()) and time.monotonic()<deadline:time.sleep(.01)
        for a in four.anchors[:3]:
            readers[a.id].cb(a.id,{'kind':'status','state':'configured_restart_required','code':0});readers[a.id].cb(a.id,readers[a.id].hello())
        time.sleep(.1)
        assert not c.running and not any('E2E START' in r.history for r in readers.values())
        a=four.anchors[3];readers[a.id].cb(a.id,{'kind':'status','state':'configured_restart_required','code':0});readers[a.id].cb(a.id,readers[a.id].hello())
        while not c.running and time.monotonic()<deadline:time.sleep(.01)
        assert c.running and all('E2E START' in r.history for r in readers.values())
    finally:c.close()

def test_four_flash_all_and_tag_row_dispatch(tmp_path,monkeypatch):
    app=W.QApplication.instance() or W.QApplication([]);calls=[]
    monkeypatch.setattr('uwb_board_programmer.gui.ports',lambda:[])
    class Flasher:
        def __init__(self,*args):pass
        def flash(self,image,port,revision,model):calls.append((image,port,revision,model))
        def setup_tag(self,images,port,revision,profile):calls.append(('tag',port,revision,profile.mode))
    monkeypatch.setattr('uwb_board_programmer.gui.Flasher',Flasher)
    window=Window(tmp_path);window.mode_combo.setCurrentIndex(1)
    for i in range(5):window.port_boxes[i].setCurrentText(f'COM{80+i}');window.rev_boxes[i].setCurrentIndex(3)
    monkeypatch.setattr(window,'available_images',lambda:{'master':'master-image','slave':'slave-image'})
    monkeypatch.setattr(window,'job',lambda fn,*args:fn())
    window.flash_all();assert len(calls)==4
    assert [r[0] for r in calls]==['master-image','slave-image','slave-image','slave-image']
    assert [r[1] for r in calls]==['COM80','COM81','COM82','COM83']
    window.target.setCurrentIndex(4);window.flash_selected();assert calls[-1]==('tag','COM84',3,'tdoa_4');window.close()

def test_thai_page_titles_update_immediately(tmp_path):
    app=W.QApplication.instance() or W.QApplication([]);window=Window(tmp_path);window.language_combo.setCurrentIndex(1)
    for index,title in [(2,'ตำแหน่งแบบเรียลไทม์'),(1,'สำรวจและสอบเทียบ'),(4,'บันทึกและเล่นย้อนหลัง')]:
        window.tabs.setCurrentIndex(index)
        assert window.page_title.text()==title
    window.close()
