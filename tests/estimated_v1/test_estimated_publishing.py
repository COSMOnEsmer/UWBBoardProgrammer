import time
from types import SimpleNamespace
from uwb_board_programmer.ble_controller import BleController
from uwb_board_programmer.engine import Pipeline
from uwb_board_programmer.models import Profile
from uwb_board_programmer.cloud import position_payload

def controller():
 c=BleController.__new__(BleController);c.profile=Profile.for_mode('tdoa_4');c.running=True;c.diagnostic=False;c.publish_position=True
 c.sent=[];c.records=[];c.cloud=SimpleNamespace(publish_fix=c.sent.append);c.record=SimpleNamespace(write=lambda k,v:c.records.append((k,v)))
 c.pipe=Pipeline.__new__(Pipeline);c.pipe.continuous_display=True;c.pipe.continuity=SimpleNamespace(latest=dict(x_m=1.,y_m=.5,z_m=1.2,born=time.monotonic(),time='2026-11-04T10:00:00Z',residual_m=.2,warning='Unverified 3D estimate'))
 return c

def test_fresh_estimate_is_published_once_with_warning_not_accepted():
 c=controller();c.publish_estimate();c.publish_estimate();assert len(c.sent)==1
 f=c.sent[0];assert f['quality']=='estimated' and f['accepted'] is False and f['accuracy_m']>1
 assert c.records[0][0]=='estimated_position'
 payload=position_payload(f,'gateway');assert payload['quality']=='estimated' and payload['x_m']==1

def test_stale_missing_or_nonfinite_estimate_is_not_sent():
 c=controller();c.pipe.continuity.latest['born']-=3;c.publish_estimate();assert not c.sent
 c.pipe.continuity.latest=None;c.publish_estimate();assert not c.sent
 c=controller();c.pipe.continuity.latest['x_m']=float('nan');c.publish_estimate();assert not c.sent

def test_pause_diagnostic_opt_out_and_disconnect_stop_publishing():
 for field,value in [('running',False),('diagnostic',True),('publish_position',False),('cloud',None)]:
  c=controller();setattr(c,field,value);c.publish_estimate();assert not c.sent
 c=controller();c.pipe.continuous_display=False;c.publish_estimate();assert not c.sent
