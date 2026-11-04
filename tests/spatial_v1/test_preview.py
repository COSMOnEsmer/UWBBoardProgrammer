import numpy as np
import pytest
from types import SimpleNamespace
from uwb_board_programmer.models import Profile,TICK_S,C_M_S
from uwb_board_programmer.positioning import Solver

def test_rejected_uncertainty_retains_candidate_without_accepting_fix():
    p=Profile.for_mode('tdoa_4');p.bounds=[[-2,-2,0],[2,2,3]];p.max_z_uncertainty_m=1e-9
    for a,xyz in zip(p.anchors,[[-1,1,1],[1,1,2],[1,-1,1],[-1,-1,1]]):a.position=xyz
    point=np.array([.2,.3,1.4]);times={a.id:round(np.linalg.norm(point-a.position)/(TICK_S*C_M_S)) for a in p.anchors}
    obs={a.id:SimpleNamespace(status=0,nlos=False) for a in p.anchors};s=Solver(p)
    with pytest.raises(ValueError):s.solve(obs,times)
    assert s.previous is None
    assert all(np.isfinite(v) for v in s.last_diagnostic['candidate'].values())
