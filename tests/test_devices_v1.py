import io,time,hashlib
from pathlib import Path
from uwb_board_programmer.models import Profile
from uwb_board_programmer import controller,flashing

def test_start_config_ack_stop_with_mock_serial_never_real_ports(tmp_path,monkeypatch):
    class FakeReader:
        def __init__(self,a,baud,on_line,log):self.anchor=a;self.cb=on_line;self.connected=True;self.mac=a.mac;self.history=[]
        def hello(self):return {'v':1,'kind':'hello','model':'Type2BP','role':self.anchor.role,'version':'1.0.0','state':'ready','mac':self.mac,'boot':'1234'}
        def start(self):self.cb(self.anchor.id,self.hello())
        def send(self,cmd):
            self.history.append(cmd)
            if cmd.startswith('E2E CONFIG '):
                self.mac=cmd.split()[2];self.cb(self.anchor.id,{'kind':'status','state':'configured_restart_required','code':0});self.cb(self.anchor.id,self.hello())
            elif cmd=='E2E START':self.cb(self.anchor.id,{'kind':'status','state':'running','code':0})
            elif cmd=='E2E STOP':self.cb(self.anchor.id,{'kind':'status','state':'stopped','code':0})
        def close(self):self.connected=False
    monkeypatch.setattr(controller,'SerialReader',FakeReader);p=Profile()
    for a,xyz in zip(p.anchors,[[0,0,2],[8,0,2],[0,6,3]]):a.position=xyz;a.aoa_verified=True
    logs=[];c=controller.Controller(tmp_path,p,logs.append,lambda *a:None)
    try:
        deadline=time.monotonic()+3
        while len(c.hello)<3 and time.monotonic()<deadline:time.sleep(.01)
        c.command('start')
        while not c.running and time.monotonic()<deadline:time.sleep(.01)
        assert c.running,logs
        for reader in c.readers.values():assert reader.history[0].startswith('E2E CONFIG ');assert reader.history[1]=='E2E START'
        c.command('stop')
        while c.running and time.monotonic()<deadline:time.sleep(.01)
        assert not c.running;assert c.pipe.clock_status()=='unknown'
    finally:c.close()

def test_flasher_verify_flag_and_hello_without_programming_hardware(tmp_path,monkeypatch):
    path=tmp_path/'test-image.bin';path.write_bytes(b'UNIT TEST ONLY');exe=tmp_path/'tools/dk6/DK6Programmer.exe';exe.parent.mkdir(parents=True);exe.write_bytes(b'NOT EXECUTABLE')
    calls=[]
    class FakeProcess:
        def __init__(self,cmd,**kwargs):calls.append(cmd);self.stdout=io.BytesIO(b'Programming...\nVerify OK\n')
        def wait(self,**kwargs):return 0
        def kill(self):pass
    monkeypatch.setattr(flashing.subprocess,'Popen',FakeProcess)
    monkeypatch.setattr(flashing,'exchange',lambda *a,**k:{'model':'Type2BP','role':'master','version':'1.0.0'})
    entry={'path':path,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'model':'Type2BP','role':'master','version':'1.0.0','baud':3000000,'minimum_evk_revision':3}
    f=flashing.Flasher(tmp_path,lambda *a:None);log=f.flash(entry,'COM99',3,'Type2BP')
    assert log.exists();assert calls[0][-1]=='-v';assert '-e' not in calls[0];assert '--unlockmode' not in calls[0]
