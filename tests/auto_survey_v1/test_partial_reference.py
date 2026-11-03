import asyncio
from itertools import combinations
import threading
import numpy as np
from uwb_board_programmer.models import Profile
from uwb_board_programmer.survey_geometry import recover_anchors
import uwb_board_programmer.survey_workflow as workflow


def test_reference_accumulates_ranges_across_power_subsets(monkeypatch):
    profile=Profile.for_mode('tdoa_4')
    positions={a.id:np.array(xyz,float) for a,xyz in zip(profile.anchors,[[-1,1,1],[1,1,2],[1,-1,1],[-1,-1,1]])}
    edges={tuple(sorted((a,b))):{'distance_m':float(np.linalg.norm(positions[a]-positions[b]))} for a,b in combinations(positions,2)}
    geometry=recover_anchors(list(positions),edges);point=np.array([0.,0.,.1])
    available=set(list(positions)[:3]);calls=[]
    class Tag:
        def __init__(self,*args):self.hello={'model':'Type2DK'}
        def open(self):return self
        def close(self):pass
    class Network:
        def __init__(self,bindings,log,*,allow_partial):
            assert allow_partial
            self.clients={aid:None for aid in available};self.last_restore_acknowledged=True
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def measure_tag(self,aid,tag,seconds):
            calls.append(aid)
            distance=float(np.linalg.norm(positions[aid]-point))
            return {'records':[{'distance_m':distance,'status':0,'nlos':False} for _ in range(20)]}
    monkeypatch.setattr(workflow,'UsbSurveyTag',Tag);monkeypatch.setattr(workflow,'SurveyNetwork',Network)
    first=asyncio.run(workflow.capture_reference(profile,geometry,'COM-test','test',lambda _:None,threading.Event()))
    assert len(first['ranges'])==3 and first['point'] is None
    fourth=list(positions)[3];available.clear();available.add(fourth)
    second=asyncio.run(workflow.capture_reference(profile,geometry,'COM-test','test',lambda _:None,threading.Event(),previous=first))
    assert second['point'] is not None and second['missing']==[] and len(calls)==4
    assert len(first['ranges'])==3  # The previous capture is immutable.
    estimate=np.array(second['point']['position'])
    for aid,xyz in geometry['anchors'].items():
        assert abs(np.linalg.norm(estimate-xyz)-second['ranges'][aid]['distance_m'])<1e-5
