from itertools import combinations
import struct
import zlib
import numpy as np
import pytest
from uwb_board_programmer.survey_geometry import estimate_range,recover_anchors,locate_reference,register_frame,check_reference_distances,solve_reference_survey
from uwb_board_programmer.survey_protocol import command,status,ranging,TWR,STATUS


def checksum(payload):return payload[:-4]+struct.pack('<I',zlib.crc32(payload[:-4])&0xffffffff)


def test_leased_control_and_cross_request_rejection():
    assert len(command(3,15,'0200000000000002',27,10000))==20
    with pytest.raises(ValueError):command(3,15,'0200000000000002',27,31000)
    packet=checksum(TWR.pack(1,0x54,15,1,1250,0,0,27,0))
    assert ranging(packet,request=15,session=27)['distance_m']==1.25
    with pytest.raises(ValueError,match='unrelated'):ranging(packet,request=16,session=27)
    with pytest.raises(ValueError,match='CRC'):ranging(packet[:-1]+bytes([packet[-1]^1]),request=15,session=27)
    raw=checksum(STATUS.pack(1,3,0,15,27,bytes.fromhex('0200000000000002'),0))
    assert status(raw)['peer']=='0200000000000002'


def test_range_quality_does_not_accept_nlos_or_status_failure():
    samples=[dict(distance_m=1.5+(i%3-1)*.01,nlos=False,status=0) for i in range(20)]
    assert estimate_range(samples)['distance_m']==pytest.approx(1.5)
    assert estimate_range(samples)['model_sigma_m']>=.05
    with pytest.raises(ValueError,match='LOS'):estimate_range([{**sample,'nlos':True} for sample in samples])
    with pytest.raises(ValueError,match='LOS'):estimate_range([{**sample,'status':1} for sample in samples])


def geometry_data(coplanar=False):
    actual={'A1':[-1,1,1],'A2':[1,1,1 if coplanar else 2],'A3':[1,-1,1],'A4':[-1,-1,1]}
    edges={tuple(sorted((a,b))):{'distance_m':float(np.linalg.norm(np.array(actual[a])-actual[b]))} for a,b in combinations(actual,2)}
    return actual,edges


def test_complete_survey_recovers_axes_height_and_origin():
    actual,edges=geometry_data();relative=recover_anchors(list(actual),edges)
    refs={}
    for name,point in [('origin',[0,0,.1]),('x',[1,0,.1]),('y',[0,1,.1])]:
        distances={aid:{'distance_m':float(np.linalg.norm(np.array(position)-point)),'model_sigma_m':.05} for aid,position in actual.items()}
        refs[name]=locate_reference(relative['anchors'],distances)
    result=register_frame(relative['anchors'],refs,'A2')
    for aid,position in actual.items():assert result['anchors'][aid]==pytest.approx(np.array(position)-[0,0,.1],abs=1e-5)
    assert check_reference_distances(result,1,1)['passed']
    assert result['independent_accuracy_verified'] is False
    with pytest.raises(ValueError,match='failed'):check_reference_distances(result,2,1)


def test_one_tag_point_and_flat_geometry_are_not_auto_calibration():
    actual,edges=geometry_data(True)
    with pytest.raises(ValueError,match='non-coplanar'):recover_anchors(list(actual),edges)
    with pytest.raises(ValueError,match='two plane'):register_frame(actual,{'origin':{'position':[0,0,0]}},'A2')
    _,edges=geometry_data();edges.pop(('A1','A2'))
    with pytest.raises(ValueError,match='Missing'):recover_anchors(list(actual),edges)


def test_four_known_tag_points_locate_anchors_without_inter_anchor_ranges():
    actual,_=geometry_data()
    refs={name:dict(known_position=point,ranges={aid:dict(distance_m=float(np.linalg.norm(np.array(xyz)-point)),model_sigma_m=.05)
          for aid,xyz in actual.items()}) for name,point in [('origin',[0,0,0]),('x',[1,0,0]),('y',[0,1,0]),('z',[0,0,1])]}
    result=solve_reference_survey(list(actual),refs)
    for aid,point in actual.items():assert result['anchors'][aid]==pytest.approx(point,abs=1e-5)
    assert all(min(q['model_std_m'])>0 for q in result['anchor_quality'].values())
    assert not result['independent_accuracy_verified']
    with pytest.raises(ValueError,match='all four'):solve_reference_survey(list(actual),{'origin':refs['origin']})
    refs['z']['known_position']=[1,1,0]
    with pytest.raises(ValueError,match='three dimensions'):solve_reference_survey(list(actual),refs)
