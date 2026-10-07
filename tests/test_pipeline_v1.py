import json,math,time
from pathlib import Path
import numpy as np
import pytest
from uwb_board_programmer.models import Profile,Observation,C_M_S,TICK_S
from uwb_board_programmer.protocol import parse_line,Counter
from uwb_board_programmer.positioning import ClockFit,Solver,bearing,calibrate_rotation
from uwb_board_programmer.engine import Pipeline
from uwb_board_programmer.recording import Recorder,replay
from uwb_board_programmer.cloud import validate_scope,position_payload
from uwb_board_programmer import credentials

@pytest.fixture
def profile():
    p=Profile();p.bounds=[[0,0,0],[10,8,4]]
    for a,pos in zip(p.anchors,[[0,0,2.7],[9,0,2.9],[0,7,1.5]]):a.position=pos;a.aoa_verified=True
    return p

def observation(p,a,rx,tx=None,frame='BLINK',bits=64,az=0,el=0,counter=0):
    return Observation(a.id,p.anchors[0].mac if frame=='SYNC' else p.tag_mac,frame,counter,rx,tx,bits,az,el,95,95,False,'abcd1234',tx_bits=64 if tx is not None else 0)

def measurements(p,xyz,base=(1<<62)+176):
    xyz=np.array(xyz);obs={};corrected={}
    for a in p.anchors:
        local=a.rotation().T@(xyz-a.position);az=math.degrees(math.atan2(local[1],local[0]));el=math.degrees(math.atan2(local[2],np.hypot(local[0],local[1])))
        rx=base+round(np.linalg.norm(xyz-a.position)/(C_M_S*TICK_S));corrected[a.id]=rx;obs[a.id]=observation(p,a,rx,az=az,el=el)
    return obs,corrected

def synced_pipeline(p,record=lambda *a:None,fix=lambda *a:None,compute=True):
    pipe=Pipeline(p,record,fix,compute=compute);base=(1<<61)+34512
    offsets={p.anchors[1].id:base-(1<<40)+10000,p.anchors[2].id:base-(1<<40)+50000};scales={p.anchors[1].id:1.000008,p.anchors[2].id:.999992}
    # Only relative quantities enter float arithmetic; full RF epochs remain integers.
    for k in range(8):
        tx=base+round(k*.5/TICK_S)
        for a in p.anchors[1:]:
            flight=round(np.linalg.norm(np.array(a.position)-p.anchors[0].position)/(C_M_S*TICK_S))
            local=round(((tx-base)+flight+(base-offsets[a.id]))/scales[a.id])
            pipe.accept(observation(p,a,local% (1<<40),tx,frame='SYNC',bits=40))
    assert pipe.clock_status()=='synced'
    return pipe,base,offsets,scales

def feed_blink(pipe,p,base,offsets,scales,xyz,seconds=4,counter=0):
    obs,times=measurements(p,xyz,base+round(seconds/TICK_S))
    for a in p.anchors:
        o=obs[a.id];o.frame_number=counter
        if a.id in offsets:
            o.rx=round(((times[a.id]-base)+(base-offsets[a.id]))/scales[a.id])% (1<<40);o.bits=40
        pipe.accept(o)

def test_protocol_preserves_uint64():
    d={'v':1,'kind':'rx','peer_mac':'0200000000000101','frame_type':'BLINK','frame_number':str((1<<63)+71),'timestamp_bits':64,'rx_timestamp_hex':f'{(1<<63)+5:016x}','azimuth_deg':15.5,'elevation_deg':-20,'az_fom':90,'el_fom':80,'boot':'abc'}
    o=parse_line(json.dumps(d),'A1');assert o.rx==(1<<63)+5;assert o.frame_number==(1<<63)+71
    assert isinstance(o.raw_payload(Profile())['rx_timestamp_raw'],str)
    d.pop('rx_timestamp_hex');d['rx_timestamp_raw']=float(1<<63)
    with pytest.raises(ValueError):parse_line(json.dumps(d),'A1')

def test_protocol_separate_rx_tx_widths():
    d={'v':1,'kind':'rx','peer_mac':'0200000000000001','frame_type':'SYNC','frame_number':'0','timestamp_bits':40,'tx_timestamp_bits':64,'rx_timestamp_hex':'000000FFFFFFFFFF','tx_timestamp_hex':'8123456789abcdef'}
    o=parse_line(json.dumps(d),'A2');assert o.bits==40 and o.tx_bits==64 and o.tx>1<<63
    d['tx_timestamp_bits']=40
    with pytest.raises(ValueError):parse_line(json.dumps(d),'A2')

def test_counter_rollover_and_reordered_packets():
    c=Counter();m=1<<40
    assert c.unwrap(m-5,40)==m-5;assert c.unwrap(3,40)==m+3;assert c.unwrap(m-2,40)==m-2;assert c.unwrap(10,40)==m+10
    with pytest.raises(ValueError):c.unwrap(2,64)

def test_clock_centres_before_float_and_bias_once():
    c=ClockFit();xbase=(1<<62)+173;ybase=(1<<61)+191;flight=13.2;bias=.25
    for k in range(12):
        x=xbase+round(k*.5/TICK_S);y=ybase+round((x-xbase)*1.000012);c.add(x,y,flight,rx_bias_m=bias)
    assert c.ready();x=xbase+round(6.2/TICK_S)
    truth=ybase+round((x-xbase)*1.000012+(flight-bias)/(C_M_S*TICK_S))
    assert abs(c.correct(x,bias)-truth)<=2
    c.last-=3;assert not c.ready()

def test_corrupt_sync_disables_clock():
    c=ClockFit()
    for k in range(8):
        x=round(k*.5/TICK_S);c.add(x,x+(10000 if k==3 else 0),10)
    assert not c.ready()

@pytest.mark.parametrize('xyz',[[4,3,.8],[4,3,2],[2.3,4.1,3.2]])
def test_solver_measures_height(profile,xyz):
    obs,times=measurements(profile,xyz);fix=Solver(profile).solve(obs,times)
    assert np.linalg.norm(np.array([fix['x_m'],fix['y_m'],fix['z_m']])-xyz)<.025
    assert fix['num_anchors_used']==3;assert fix['z_uncertainty_m']>0

def test_solver_one_3d_aoa_plus_two_tdoas(profile):
    profile.anchors[1].aoa_verified=False;profile.anchors[2].aoa_verified=False
    obs,times=measurements(profile,[4,3,1.1]);fix=Solver(profile).solve(obs,times)
    assert abs(fix['z_m']-1.1)<.03

def test_no_elevation_no_3d_fix(profile):
    obs,times=measurements(profile,[4,3,1.1])
    for o in obs.values():o.el=None
    with pytest.raises(ValueError,match='AoA'):Solver(profile).solve(obs,times)

def test_uncertainty_gate(profile):
    profile.max_z_uncertainty_m=.0001;obs,times=measurements(profile,[4,3,1.1])
    with pytest.raises(ValueError,match='uncertainty'):Solver(profile).solve(obs,times)

def test_impossible_tdoa(profile):
    obs,times=measurements(profile,[4,3,1.1]);times[profile.anchors[1].id]+=1000000
    with pytest.raises(ValueError,match='baseline'):Solver(profile).solve(obs,times)

def test_fom_and_geometry_gates(profile):
    obs,times=measurements(profile,[4,3,1.1])
    for o in obs.values():o.el_fom=0
    with pytest.raises(ValueError,match='AoA'):Solver(profile).solve(obs,times)
    for a,pos in zip(profile.anchors,[[0,0,2],[1,0,2],[2,0,2]]):a.position=pos
    with pytest.raises(ValueError):profile.validate()

def test_pipeline_uses_rf_time_even_when_counter_repeats(profile):
    fixes=[];pipe,base,offsets,scales=synced_pipeline(profile,fix=fixes.append)
    feed_blink(pipe,profile,base,offsets,scales,[4,3,1.2],4,counter=0)
    feed_blink(pipe,profile,base,offsets,scales,[4,3,2.2],5,counter=0)
    assert len(fixes)==2;assert abs(fixes[1]['z_m']-2.2)<.04;assert fixes[0]['frame_numbers']=={a.id:'0' for a in profile.anchors}

def test_reset_invalidates_sync_and_pending(profile):
    pipe,base,offsets,scales=synced_pipeline(profile);pipe.pending.append({'born':time.monotonic(),'ref':0})
    pipe.reset(profile.anchors[0].id);assert pipe.clock_status()=='unknown';assert pipe.pending==[]
    feed_blink(pipe,profile,base,offsets,scales,[4,3,1.2]);assert pipe.fix_count==0

def test_incomplete_and_ambiguous_frames_are_rejected(profile):
    pipe,base,offsets,scales=synced_pipeline(profile);a=profile.anchors[0]
    pipe.accept(observation(profile,a,base+round(4/TICK_S)));assert pipe.fix_count==0
    pipe.accept(observation(profile,a,base+round(4/TICK_S)+10));assert pipe.rejected==1;assert not pipe.pending

def test_diagnostic_allows_unverified_aoa_without_fixes(profile):
    for a in profile.anchors:a.aoa_verified=False
    pipe,base,offsets,scales=synced_pipeline(profile,compute=False)
    feed_blink(pipe,profile,base,offsets,scales,[4,3,1.2]);assert pipe.fix_count==0;assert len(pipe.latest_angles)==3

def test_orientation_reference_fit(profile):
    a=profile.anchors[0];a.yaw=37;a.pitch=-15;a.roll=8;rows=[]
    for xyz in [[4,3,1],[2,5,3],[6,1,2],[3,2,3.8]]:
        o,_=measurements(profile,xyz);rows.append({'position':xyz,'az':o[a.id].az,'el':o[a.id].el})
    result=calibrate_rotation(a,rows);assert abs(result['yaw']-37)<1e-8;assert abs(result['pitch']+15)<1e-8
    with pytest.raises(ValueError):calibrate_rotation(a,[rows[0]]*3)

def test_record_replay_offline(profile,tmp_path):
    rec=Recorder(tmp_path,profile);fixes=[];pipe,base,offsets,scales=synced_pipeline(profile,rec.write,fixes.append)
    feed_blink(pipe,profile,base,offsets,scales,[4,3,1.2]);rec.close();replayed=[]
    result=replay(rec.path,replayed.append);assert result['fixes']==1;assert len(replayed)==1;assert replayed[0]['z_m']==fixes[0]['z_m']

def test_cloud_scope_coordinates_and_wire(profile):
    cfg={'site':{'id':profile.site_id},'floors':[{'id':profile.floor_id}],'anchors':[{'id':a.id,'floorId':profile.floor_id,'role':a.role,'posXM':a.position[0],'posYM':a.position[1],'posZM':a.position[2]} for a in profile.anchors]}
    assert validate_scope(profile,cfg);cfg['anchors'][0]['posZM']+=.1
    with pytest.raises(ValueError,match='surveyed'):validate_scope(profile,cfg)
    obs,times=measurements(profile,[4,3,1.2]);fix=Solver(profile).solve(obs,times);fix.update(site_id=profile.site_id,floor_id=profile.floor_id,tag_id=profile.tag_id,time='2026-10-07T00:00:00Z')
    payload=position_payload(fix,'test-gateway');assert payload['z_m']>0;assert payload['engine_id']=='test-gateway';assert 'frame_numbers' not in payload

def test_dpapi_round_trip_no_plaintext(tmp_path):
    path=credentials.save(tmp_path,'unit-test-token-123','local-test-gateway');assert 'unit-test-token-123' not in path.read_text()
    assert credentials.load(path)['token']=='unit-test-token-123'
