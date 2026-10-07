"""Software fixtures only: no serial port, RF board or production cloud access."""
import math,time
import numpy as np
import pytest
from uwb_board_programmer.models import Profile,TICK_S,C_M_S
from uwb_board_programmer.positioning import Solver
from uwb_board_programmer.engine import Pipeline
from uwb_board_programmer.recording import Recorder,replay
from uwb_board_programmer.cloud import position_payload,validate_scope
from test_pipeline_v1 import observation,measurements

@pytest.fixture
def four():
    p=Profile.for_mode('tdoa_4');p.bounds=[[0,0,0],[10,8,4]];p.tdoa_sigma_m=.03
    for a,pos in zip(p.anchors,[[0,0,0],[10,0,0],[0,8,0],[0,0,4]]):a.position=pos
    return p

def synced_four(p,record=lambda *a:None,fix=lambda *a:None):
    pipe=Pipeline(p,record,fix);base=(1<<61)+34512
    offsets={a.id:base-(1<<40)+10000*(i+1) for i,a in enumerate(p.anchors[1:])}
    scales={a.id:1+(i-1)*8e-6 for i,a in enumerate(p.anchors[1:])}
    for k in range(8):
        tx=base+round(k*.5/TICK_S)
        for a in p.anchors[1:]:
            flight=round(np.linalg.norm(np.array(a.position)-p.anchors[0].position)/(C_M_S*TICK_S))
            local=round(((tx-base)+flight+(base-offsets[a.id]))/scales[a.id])
            pipe.accept(observation(p,a,local%(1<<40),tx,frame='SYNC',bits=40))
    assert pipe.clock_status()=='synced'
    return pipe,base,offsets,scales

def blink_four(pipe,p,base,offsets,scales,xyz):
    obs,times=measurements(p,xyz,base+round(4/TICK_S))
    for a in p.anchors:
        o=obs[a.id];o.az=None;o.el=None;o.az_fom=0;o.el_fom=0
        if a.id in offsets:o.rx=round(((times[a.id]-base)+(base-offsets[a.id]))/scales[a.id])%(1<<40);o.bits=40
        pipe.accept(o)

@pytest.mark.parametrize('xyz',[[4,3,1],[2,2,2],[3,4,3]])
def test_four_anchor_height_without_any_angles(four,xyz):
    obs,times=measurements(four,xyz)
    for o in obs.values():o.az=None;o.el=None
    fix=Solver(four).solve(obs,times)
    assert np.linalg.norm(np.array([fix['x_m'],fix['y_m'],fix['z_m']])-xyz)<.04
    assert fix['num_anchors_used']==4 and fix['aoa_anchors_used']==[]

def test_four_ignores_even_verified_wrong_angles(four):
    obs,times=measurements(four,[4,3,1])
    for a in four.anchors:a.aoa_verified=True
    for o in obs.values():o.az=170;o.el=80
    fix=Solver(four).solve(obs,times)
    assert abs(fix['z_m']-1)<.04 and not fix['aoa_anchors_used']

def test_four_rejects_coplanar_geometry_and_incorrect_count(four):
    four.anchors[3].position=[10,8,0]
    with pytest.raises(ValueError,match='non-coplanar'):four.validate()
    four.anchors.pop()
    with pytest.raises(ValueError,match='4 anchors'):four.validate()

def test_four_freshness_all_slaves_and_all_blinks(four):
    fixes=[];pipe,base,offsets,scales=synced_four(four,fix=fixes.append)
    blink_four(pipe,four,base,offsets,scales,[4,3,1]);assert len(fixes)==1
    assert fixes[0]['num_anchors_used']==4 and len(fixes[0]['frame_numbers'])==4
    pipe.clocks[four.anchors[3].id].last-=3
    assert pipe.clock_status()!='synced'
    blink_four(pipe,four,base,offsets,scales,[4,3,2]);assert len(fixes)==1

def test_four_replay_and_platform_anchor_count(four,tmp_path):
    rec=Recorder(tmp_path,four);fixes=[];pipe,base,offsets,scales=synced_four(four,rec.write,fixes.append)
    blink_four(pipe,four,base,offsets,scales,[4,3,1]);rec.close()
    replayed=[];summary=replay(rec.path,replayed.append)
    assert summary['fixes']==1 and len(replayed)==1 and replayed[0]['num_anchors_used']==4
    payload=position_payload(fixes[0],'unit-test-only');assert payload['num_anchors_used']==4
    cfg={'site':{'id':four.site_id},'floors':[{'id':four.floor_id}],'anchors':[{'id':a.id,'floorId':four.floor_id,'role':a.role,'posXM':a.position[0],'posYM':a.position[1],'posZM':a.position[2]} for a in four.anchors]}
    assert validate_scope(four,cfg)
    cfg['anchors'].pop()
    with pytest.raises(ValueError):validate_scope(four,cfg)

def test_legacy_profile_mode_inference(four):
    data=four.to_dict();data.pop('mode');assert Profile.from_dict(data).mode=='tdoa_4'
    data=Profile().to_dict();data.pop('mode');assert Profile.from_dict(data).mode=='hybrid_3'

def test_four_preserves_uncertainty_rejection(four):
    four.max_z_uncertainty_m=.0001;obs,times=measurements(four,[4,3,1])
    with pytest.raises(ValueError,match='uncertainty'):Solver(four).solve(obs,times)
