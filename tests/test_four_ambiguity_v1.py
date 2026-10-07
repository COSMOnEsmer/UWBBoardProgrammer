import pytest
from uwb_board_programmer.models import Profile
from uwb_board_programmer.positioning import Solver
from test_pipeline_v1 import measurements

def test_two_physical_roots_inside_bounds_are_not_silently_selected():
    p=Profile.for_mode('tdoa_4');p.bounds=[[0,0,0],[10,8,4]];p.tdoa_sigma_m=.001;p.max_z_uncertainty_m=10;p.max_horizontal_uncertainty_m=10
    positions=[[9.171225725476024,6.917522008750199,1.1544286197499638],[8.66127430738243,5.84601549097003,1.3335958708967834],[7.970435531834646,6.921773702749892,1.3983136869123718],[5.27042084030297,.5718944529871752,2.249715230453174]]
    truth=[2.9032511970369406,5.58978187662189,1.0208949085262078]
    for a,xyz in zip(p.anchors,positions):a.position=xyz
    obs,times=measurements(p,truth)
    with pytest.raises(ValueError,match='Ambiguous 3D fix'):Solver(p).solve(obs,times)
