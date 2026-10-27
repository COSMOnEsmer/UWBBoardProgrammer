import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app/ble_prototype/v1'))
from uwb_ble_positioning import CorrelatedSolver, tdoa_covariance
from uwb_board_programmer.models import Profile
from test_pipeline_v1 import measurements


def room():
    p=Profile.for_mode('tdoa_4');p.bounds=[[0,0,0],[10,8,4]];p.tdoa_sigma_m=.03
    for anchor,xyz in zip(p.anchors,[(0,0,0),(10,0,0),(0,8,0),(0,0,4)]):anchor.position=list(xyz)
    return p


def test_master_noise_is_shared_and_slave_clock_uncertainty_is_independent():
    p=room();obs,times=measurements(p,[4,3,1]);ids=[a.id for a in p.anchors]
    covariance=tdoa_covariance(p,obs,{ids[1]:.1})
    assert np.allclose(covariance-np.diag(np.diag(covariance)),np.ones((3,3))*.00045-np.eye(3)*.00045)
    assert np.allclose(np.diag(covariance),[.0109,.0009,.0009])
    obs[ids[0]].nlos=True
    increased=tdoa_covariance(p,obs,{ids[1]:.1})-covariance
    assert np.allclose(increased,np.full((3,3),.00045*15))
    with pytest.raises(ValueError):tdoa_covariance(p,obs,{ids[1]:float('nan')})


@pytest.mark.parametrize('point',[[4,3,1],[2,2,2],[3,4,3]])
def test_correlated_solver_retains_height_and_ignores_angles_in_four_anchor_mode(point):
    p=room();obs,times=measurements(p,point)
    for o in obs.values():o.az=170;o.el=80
    fix=CorrelatedSolver(p).solve(obs,times)
    assert np.linalg.norm(np.array([fix['x_m'],fix['y_m'],fix['z_m']])-point)<.04
    assert not fix['aoa_anchors_used']
