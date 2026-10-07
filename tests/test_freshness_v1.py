from datetime import datetime,timezone,timedelta
from uwb_board_programmer.models import Profile,Observation
from uwb_board_programmer.engine import Pipeline
def test_old_rf_input_never_becomes_live_fix():
    p=Profile()
    for a,xyz in zip(p.anchors,[[0,0,2],[8,0,2],[0,6,3]]):a.position=xyz;a.aoa_verified=True
    pipe=Pipeline(p);o=Observation(p.anchors[0].id,p.tag_mac,'BLINK',0,100,None,40,0,0,90,90,False,'1',received_utc=(datetime.now(timezone.utc)-timedelta(seconds=5)).isoformat())
    pipe.accept(o);assert pipe.rejected==1;assert pipe.fix_count==0;assert 'older' in pipe.reason
