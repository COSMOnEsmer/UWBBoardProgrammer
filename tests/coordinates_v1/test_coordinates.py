import copy,json
from pathlib import Path
import numpy as np
import pytest
from PySide6 import QtWidgets as W
from uwb_board_programmer.models import Profile
from uwb_board_programmer.coordinates import *
from uwb_board_programmer.alignment_dialog import AlignmentDialog
from uwb_board_programmer.cloud import validate_scope,position_payload

POSITIONS=[[-.444,.452,.891],[.881,.469,1.891],[1.318,-.389,.779],[-1.132,-.426,.518]]
EXPECTED=[[.688,.878,.891],[2.013,.895,1.891],[2.450,.037,.779],[0.,0.,.518]]
GEOMETRY=dict(origin_x=0,origin_y=0,length=4,width=4,height=2,elevation=0,level_index=0,meters_per_pixel=.01)

def survey():
    p=Profile.for_mode('tdoa_4');p.coordinate_frame='survey';p.survey_verified=True;p.site_id='test-site';p.floor_id='test-floor';p.bounds=[[-2,-2,0],[2,2,2]]
    for i,(a,xyz) in enumerate(zip(p.anchors,POSITIONS),1):a.id=f'TP-A{i}';a.position=list(xyz)
    return p

def aligned(p=None,yaw=0,offset=(1.132,.426,0)):
    return align_profile(p or survey(),yaw,offset,GEOMETRY,True)

def config(p):
    return dict(site=dict(id=p.site_id),floors=[dict(id=p.floor_id,originXM=0,originYM=0,lengthM=4,widthM=4,heightM=2)],anchors=[dict(id=a.id,floorId=p.floor_id,role=a.role,posXM=a.position[0],posYM=a.position[1],posZM=a.position[2]) for a in p.anchors])

def test_user_a4_xy_offset_matches_all_four_rtls_coordinates():
    p=survey();original=copy.deepcopy(p.to_dict());q=aligned(p)
    assert np.allclose([a.position for a in q.anchors],EXPECTED,atol=1e-12)
    assert q.anchors[-1].position[2]==.518 and q.bounds==[[0,0,0],[4,4,2]]
    assert p.to_dict()==original and q.alignment['source_profile']['anchors'][3]['position']==POSITIONS[3]
    assert q.coordinate_frame=='floor' and q.floor_verified
    validate_scope(q,config(q));assert not outside_floor(q)

def test_realign_is_idempotent_and_retains_raw_survey():
    first=aligned();second=aligned(first)
    assert np.allclose([a.position for a in first.anchors],[a.position for a in second.anchors])
    assert source_profile(second).anchors[-1].position==POSITIONS[-1]
    assert 'source_profile' not in second.alignment['source_profile']['alignment']

@pytest.mark.parametrize('yaw',[0,90,-90,37])
def test_round_trip_and_distance_invariance(yaw):
    p=survey();q=aligned(p,yaw,(2,2,1.25));r=matrix(yaw)
    for a,b in zip(p.anchors,q.anchors):assert np.allclose(inverse(b.position,yaw,[2,2,1.25]),a.position)
    tag=np.array([.2,.3,1.1]);tag_f=transform(tag,yaw,[2,2,1.25])
    before=[np.linalg.norm(tag-a.position) for a in p.anchors];after=[np.linalg.norm(np.array(tag_f)-a.position) for a in q.anchors]
    assert np.allclose(before,after)
    for a,b in zip(p.anchors,q.anchors):assert np.allclose(a.rotation().T@(tag-a.position),b.rotation().T@(np.array(tag_f)-b.position))

def test_z_reference_and_elevation_are_not_added_twice():
    g={**GEOMETRY,'elevation':12,'level_index':4};q=align_profile(survey(),0,[1.132,.426,1],g,True)
    assert q.anchors[-1].position==[0,0,1.518]
    assert q.alignment['translation_m'][2]==1 and 'TP-A2' in outside_floor(q)
    assert q.floor_geometry['elevation']==12

def test_unmapped_profiles_cannot_pass_cloud_gate():
    p=survey();p.coordinate_frame='unmapped'
    with pytest.raises(ValueError,match='Align survey'):validate_scope(p,config(p))
    q=aligned();q.floor_verified=False
    with pytest.raises(ValueError,match='Align survey'):validate_scope(q,config(q))

def test_edited_geometry_or_floor_cannot_reuse_alignment():
    p=aligned();p.anchors[0].position[0]+=.1
    with pytest.raises(ValueError,match='edited'):require_floor(p)
    p=aligned();p.floor_id='another-floor'
    with pytest.raises(ValueError,match='another site/floor'):require_floor(p)
    p=aligned();p.anchors[0].yaw+=10
    with pytest.raises(ValueError,match='orientation'):require_floor(p)

def test_reference_fit_and_independent_error():
    s=np.array([[0,0,0],[1,0,0],[0,1,1]],float);t=np.array([transform(p,90,[2,1,.8]) for p in s])
    result=fit_references(s,t)
    assert result['yaw_deg']==pytest.approx(90) and np.allclose(result['translation_m'],[2,1,.8]) and result['rms_m']<1e-10
    assert np.allclose(transform([.3,.2,1],result['yaw_deg'],result['translation_m']),[1.8,1.3,1.8])

@pytest.mark.parametrize('bad', ['scale','reflection','height'])
def test_fit_rejects_inconsistent_reference_geometry(bad):
    s=np.array([[0,0,0],[2,0,0],[0,2,1]],float);t=s.copy()
    if bad=='scale':t*=1.5
    elif bad=='reflection':t[:,0]*=-1
    else:t[2,2]+=1
    with pytest.raises(ValueError):fit_references(s,t)

def test_rotated_bounds_include_all_eight_corners():
    b=transform_bounds([[0,0,0],[2,1,3]],45,[1,2,4]);assert np.allclose(b,[[1-np.sqrt(.5),2,4],[1+np.sqrt(2),2+3*np.sqrt(.5),7]])

def test_legacy_profile_migrates_as_unmapped_not_assumed_floor():
    data=survey().to_dict()
    for key in ('coordinate_frame','schema_version','floor_verified','alignment','floor_geometry','survey_archive'):data.pop(key,None)
    p=Profile.from_dict(data);assert p.coordinate_frame=='unmapped' and not p.floor_verified

def test_dialog_a4_preset_and_confirmation():
    app=W.QApplication.instance() or W.QApplication([]);dlg=AlignmentDialog(survey())
    assert np.allclose([a.position for a in dlg.preview.anchors],EXPECTED)
    dlg.apply();assert dlg.result_profile is None
    dlg.confirm.setChecked(True);dlg.apply();assert dlg.result_profile.floor_verified
    dlg.close()

def test_display_and_payload_use_same_floor_point_without_offset_again():
    from uwb_board_programmer.spatial_view import FloorPlot
    app=W.QApplication.instance() or W.QApplication([]);p=aligned()
    fix=dict(site_id=p.site_id,floor_id=p.floor_id,tag_id=p.tag_id,x_m=.8,y_m=.9,z_m=1.1,accuracy_m=.2,num_anchors_used=4,residual=.1,time='2026-11-04T00:00:00Z')
    plot=FloorPlot();plot.profile=p;plot.set_fix(fix);payload=position_payload(fix,'gateway')
    assert plot.live['x_m']==payload['x_m']==.8 and plot.live['z_m']==payload['z_m']==1.1
    plot.close()

def test_aligned_profile_round_trip_can_replay_without_live_changes():
    p=aligned();q=Profile.from_dict(json.loads(json.dumps(p.to_dict())));q.validate(require_aoa=False)
    assert q.coordinate_frame=='floor';check_alignment(q)


def test_cloud_rejects_changed_floor_dimensions():
    p=aligned();cfg=config(p);cfg['floors'][0]['lengthM']=5
    with pytest.raises(ValueError,match='Floor geometry changed'):validate_scope(p,cfg)

def test_gui_collect_keeps_alignment_valid_after_numeric_formatting():
    from uwb_board_programmer.gui import Window
    app=W.QApplication.instance() or W.QApplication([])
    root=Path(__file__).resolve().parents[2];w=Window(root);w.profile=aligned(yaw=37,offset=(2,2,0));w.populate_profile()
    p=w.collect();check_alignment(p);assert p.coordinate_frame=='floor';w.close()
