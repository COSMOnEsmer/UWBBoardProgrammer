import json
import math
from types import SimpleNamespace
import numpy as np
import pytest
pytest.importorskip('uwb_board_programmer.ble_controller',reason='Select the v5 test environment with tests/integrated_v1/pytest.ini')
from uwb_board_programmer.ble_controller import BleController,CaptureState
from uwb_board_programmer.models import Profile,TICK_S,C_M_S
from uwb_board_programmer import standalone_flashing as flash


def observation(peer,rx,*,kind='BLINK',tx=None,number=1):
    return dict(v=1,kind='rx',peer_mac=peer,frame_type=kind,frame_number=str(number),
                status=0,message_control=16,timestamp_bits=64,tx_timestamp_bits=64 if tx is not None else 0,
                rx_timestamp_hex=f'{rx:016x}',tx_timestamp_hex=f'{tx:016x}' if tx is not None else None,
                azimuth_deg=0.,elevation_deg=0.,az_fom=100,el_fom=100,nlos=0,boot='12345678',dropped=0)


def connected(controller):
    for a in controller.profile.anchors:
        controller.handle_event(a.id,'connected',dict(firmware='1.3.4-pilot',radio_state='running',boot='12345678',config_crc='12345678'))


def test_capture_one_board_without_survey_never_constructs_serial_or_position(tmp_path,monkeypatch):
    p=Profile.for_mode('tdoa_4');fixes=[]
    c=BleController(tmp_path,p,lambda *a:None,fixes.append,diagnostic=True,autostart_threads=False)
    try:
        assert isinstance(c.pipe,CaptureState)
        connected(c);c.handle_event(p.anchors[0].id,'observation',observation(p.tag_mac,(1<<62)+123))
        s=c.snapshot();assert s['rf_total']==1 and s['fixes']==0 and not fixes
        c.handle_event('__processing__','stop',{})
        assert not c.running and c.central is None
        assert c.latest[p.anchors[0].id].rx==(1<<62)+123
    finally:c.close()
    rows=[json.loads(line) for line in c.record.path.read_text(encoding='utf8').splitlines()]
    assert any(r['kind']=='processing' and r['data']['radio_commands_sent']==0 for r in rows)


def test_corrected_rf_clocks_produce_3d_fix_then_pause_blocks_publishing(tmp_path):
    p=Profile.for_mode('tdoa_4');p.bounds=[[0,0,0],[10,8,4]];p.tdoa_sigma_m=.03
    for a,xyz in zip(p.anchors,[(0,0,0),(10,0,0),(0,8,0),(0,0,4)]):a.position=list(xyz)
    fixes=[];published=[]
    c=BleController(tmp_path,p,lambda *a:None,fixes.append,autostart_threads=False)
    c.cloud=SimpleNamespace(publish_fix=published.append);c.publish_position=True
    master=p.anchors[0];base=1<<62;local_base=1<<61
    try:
        connected(c);c.handle_event('__processing__','start',{})
        for index in range(7):
            delta=round(index*.5/TICK_S);tx=base+delta
            for j,a in enumerate(p.anchors[1:],1):
                alpha=1+j*20e-6;flight=np.linalg.norm(a.position)/(C_M_S*TICK_S)
                rx=local_base+j*100000+round((delta+flight)/alpha)
                c.handle_event(a.id,'observation',observation(master.mac,rx,kind='SYNC',tx=tx,number=index))
        assert c.pipe.clock_status()=='synced'
        truth=np.array([4.,3.,1.])
        def blink(seconds):
            for j,a in enumerate(p.anchors):
                delta=round(seconds/TICK_S)+round(np.linalg.norm(truth-a.position)/(C_M_S*TICK_S))
                rx=base+delta if j==0 else local_base+j*100000+round(delta/(1+j*20e-6))
                c.handle_event(a.id,'observation',observation(p.tag_mac,rx))
        blink(4)
        assert len(fixes)==len(published)==1
        assert np.linalg.norm(np.array([fixes[0][k] for k in ['x_m','y_m','z_m']])-truth)<.04
        assert fixes[0]['aoa_anchors_used']==[]
        c.handle_event('__processing__','stop',{});blink(5)
        assert len(fixes)==len(published)==1
        assert c.snapshot()['rf_total']==29
    finally:c.close()


def test_failed_backup_prevents_programmer_in_packaged_path(tmp_path,monkeypatch):
    entry=dict(file='unused',bytes=44,sha256='x',image_label='master',provisioned_mac='0200000000000001')
    monkeypatch.setattr(flash,'validate_image',lambda *a:tmp_path/'image.bin')
    monkeypatch.setattr(flash,'_identity',lambda *a:None)
    def fail(*args):raise RuntimeError('Backup unavailable')
    monkeypatch.setattr('uwb_board_programmer.host_backup.backup_host',fail)
    monkeypatch.setattr(flash.subprocess,'run',lambda *a,**k:pytest.fail('Programmer must not run'))
    result=flash.flash_selected(tmp_path,entry,'COM99','TEST-ONLY')
    assert not result['program_verify_passed'] and 'Backup unavailable' in result['error']
