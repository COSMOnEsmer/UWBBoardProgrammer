import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app/ble_prototype/v1'))
from uwb_ble_pipeline_v2 import CorrelatedLivePipeline
from uwb_ble_positioning import CorrelatedSolver
from test_ble_pipeline_pilot_v1 import surveyed


def test_ble_capture_identifies_pilot_and_uses_shared_master_covariance():
    rows=[]
    pipe=CorrelatedLivePipeline(surveyed(),lambda *row:rows.append(row),lambda fix:None)
    assert isinstance(pipe.engine.solver,CorrelatedSolver)
    assert rows[0][0]=='transport'
    assert rows[0][1]['name']=='BLE' and rows[0][1]['hardware_validated'] is False
    pipe.engine.record('fix',dict(engine_id='legacy',x_m=1))
    assert rows[-1][1]['engine_id']=='UWBBoardProgrammer/StandaloneBLE-pilot'
